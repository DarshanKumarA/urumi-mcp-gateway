#!/bin/sh
# Run only in the finite bootstrap Job. Never enable shell tracing.
set -eu
umask 077

fail() { printf '%s\n' "Bootstrap failed: $1" >&2; exit 1; }
log() { printf '%s\n' "$1"; }
for number in "$URUMI_WAIT_SECONDS" "$URUMI_RETRY_SECONDS" "$URUMI_COMMAND_SECONDS"; do
    case "$number" in ''|*[!0-9]*) fail "invalid timeout configuration" ;; esac
    [ "$number" -gt 0 ] || fail "timeouts must be positive"
done

assets=/opt/urumi-store
export HOME=/tmp
export WP_CLI_CACHE_DIR=/tmp/wp-cli-cache
mkdir -p "$WP_CLI_CACHE_DIR" /tmp/urumi-bootstrap
[ "$URUMI_BOOTSTRAP_VERSION" = 2 ] || fail "this script supports bootstrap version 2 only"
# The CLI image has no Apache; describe the verified target Apache environment.
export WP_CLI_CONFIG_PATH=/tmp/urumi-bootstrap/wp-cli.yml
printf 'apache_modules:\n  - mod_rewrite\n' > "$WP_CLI_CONFIG_PATH"

php_step() {
    timeout -s KILL "$URUMI_COMMAND_SECONDS" php -d display_errors=0 -d log_errors=0 \
        "$assets/configure-woocommerce.php" "$@"
}
wp_step() {
    timeout -s KILL "$URUMI_COMMAND_SECONDS" php -d memory_limit=256M \
        -d display_errors=0 -d log_errors=0 /usr/local/bin/wp \
        --path=/var/www/html --no-color "$@"
}
wp_action() {
    action=$1
    shift
    acknowledgement=$(wp_step eval-file "$assets/configure-woocommerce.php" "$action" "$@") \
        || return 1
    [ "$acknowledgement" = URUMI_BOOTSTRAP_OK ]
}
files_ready() {
    [ -s /var/www/html/wp-load.php ] && [ -s /var/www/html/wp-config.php ] \
        && [ -s /var/www/html/wp-includes/version.php ]
}
# Each dependency has its own deadline, including time spent in each attempt.
wait_for() {
    label=$1
    command=$2
    deadline=$(($(date +%s) + URUMI_WAIT_SECONDS))
    while :; do
        remaining=$((deadline - $(date +%s)))
        [ "$remaining" -gt 0 ] || fail "$label did not become available before its deadline"
        if [ "$command" = files_ready ]; then
            if files_ready; then return; fi
        elif timeout -s KILL "$remaining" php -d display_errors=0 -d log_errors=0 \
            "$assets/configure-woocommerce.php" db-ready >/dev/null 2>&1; then
            return
        fi
        remaining=$((deadline - $(date +%s)))
        [ "$remaining" -gt 0 ] || fail "$label did not become available before its deadline"
        pause=$URUMI_RETRY_SECONDS
        [ "$pause" -le "$remaining" ] || pause=$remaining
        sleep "$pause"
    done
}

log "Waiting for initialized WordPress files."
wait_for "WordPress files" files_ready
log "Waiting for authenticated database access."
wait_for "database" db_ready

if wp_step core is-installed --skip-plugins >/dev/null 2>&1; then
    log "WordPress is installed; preserving users and passwords."
else
    # Exit code 1 from is-installed alone is NOT evidence of a fresh database.
    # This opens a new authenticated connection and positively checks zero tables.
    php_step db-empty || fail "database is unavailable or nonempty; review installation state"
    log "Confirmed an empty database; installing WordPress."
    [ -s "$URUMI_ADMIN_PASSWORD_FILE" ] || fail "initial admin Secret is missing"
    if ! wp_step core install --skip-plugins --url="$URUMI_CANONICAL_URL" \
        --title="$URUMI_SITE_TITLE" --admin_user="$URUMI_ADMIN_USERNAME" \
        --admin_email="$URUMI_ADMIN_EMAIL" --skip-email --prompt=admin_password \
        < "$URUMI_ADMIN_PASSWORD_FILE" >/dev/null 2>&1; then
        fail "initial WordPress installation failed; no reset or automatic repair attempted"
    fi
    wp_step core is-installed --skip-plugins >/dev/null 2>&1 \
        || fail "WordPress installation could not be verified"
    wp_action claim --skip-plugins \
        || fail "could not claim the new installation"
fi

# Refuse to silently take over an unrelated existing store or change its contract.
wp_action preflight --skip-plugins \
    || fail "bootstrap contract preflight failed"

if [ -e /var/www/html/wp-content/plugins/woocommerce ]; then
    installed=$(wp_step plugin get woocommerce --field=version --skip-plugins 2>/dev/null) \
        || fail "existing WooCommerce files cannot be identified; manual review required"
    [ "$installed" = "$URUMI_WC_VERSION" ] \
        || fail "installed WooCommerce version differs; explicit upgrade/downgrade review required"
else
    log "Downloading and verifying the exact WooCommerce archive."
    php_step download || fail "WooCommerce download/checksum verification failed"
    wp_step plugin install /tmp/urumi-bootstrap/woocommerce.zip --skip-plugins >/dev/null 2>&1 \
        || fail "WooCommerce installation failed; no force overwrite attempted"
fi
installed=$(wp_step plugin get woocommerce --field=version --skip-plugins 2>/dev/null) \
    || fail "WooCommerce version inspection failed"
[ "$installed" = "$URUMI_WC_VERSION" ] || fail "installed WooCommerce version is unexpected"
if ! wp_step plugin is-active woocommerce --skip-plugins >/dev/null 2>&1; then
    wp_step plugin activate woocommerce --skip-plugins >/dev/null 2>&1 \
        || fail "WooCommerce activation failed"
fi

log "Verifying loaded WooCommerce and applying resumable demo configuration."
wp_action configure \
    || fail "demo configuration or acknowledgement failed; review persisted bootstrap state"
log "Applying deterministic permalinks and flushing Apache rewrite rules."
# Load plugins AND themes. structure launches a fresh process for the hard flush,
# so WooCommerce registers routes using the new structure, not stale in-memory state.
wp_step rewrite structure '/%postname%/' --hard >/dev/null 2>&1 \
    || fail "permalink update or hard flush failed; completion marker was not advanced"
wp_action finalize \
    || fail "rewrite verification or final acknowledgement failed; review bootstrap state"
log "Bootstrap verified successfully."
