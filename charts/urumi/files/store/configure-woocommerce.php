<?php
// Non-secret code. Credentials are read from mounted files, never from chart data.
// Direct PHP modes check dependencies/downloads; WP-CLI eval-file modes use WP APIs.
class UrumiBootstrapFailure extends RuntimeException {}

function urumi_require($condition, $message) {
    if (!$condition) {
        throw new UrumiBootstrapFailure($message);
    }
}
function urumi_env($name) {
    $value = getenv($name);
    urumi_require(is_string($value) && $value !== '', 'Required bootstrap configuration is missing.');
    return $value;
}
function urumi_db() {
    mysqli_report(MYSQLI_REPORT_OFF);
    $host = urumi_env('WORDPRESS_DB_HOST');
    $parts = explode(':', $host, 2); // Chart-generated Service DNS and numeric port.
    $password = file_get_contents(urumi_env('WORDPRESS_DB_PASSWORD_FILE'));
    urumi_require($password !== false, 'Database credential file is unavailable.');
    $db = mysqli_init();
    $seconds = (int) urumi_env('URUMI_DB_CONNECT_SECONDS');
    urumi_require($seconds > 0, 'Invalid database connection timeout.');
    $db->options(MYSQLI_OPT_CONNECT_TIMEOUT, $seconds);
    $db->options(MYSQLI_OPT_READ_TIMEOUT, $seconds);
    urumi_require(@$db->real_connect($parts[0], urumi_env('WORDPRESS_DB_USER'),
        rtrim($password, "\r\n"), urumi_env('WORDPRESS_DB_NAME'), (int) ($parts[1] ?? 3306)),
        'Authenticated database connection failed.');
    $result = $db->query('SELECT 1');
    urumi_require($result && $result->fetch_row()[0] === '1', 'Database query failed.');
    return $db;
}
function urumi_contract() {
    $contract = [];
    foreach (['BOOTSTRAP_VERSION', 'CANONICAL_URL', 'SITE_TITLE', 'TIMEZONE',
        'COUNTRY', 'CURRENCY', 'WC_VERSION', 'WC_ARCHIVE_URL', 'WC_SHA256'] as $key) {
        $contract[$key] = urumi_env('URUMI_' . $key);
    }
    urumi_require(filter_var($contract['CANONICAL_URL'], FILTER_VALIDATE_URL) !== false,
        'Canonical URL is invalid.');
    urumi_require(in_array($contract['TIMEZONE'], timezone_identifiers_list(), true),
        'Business timezone is invalid.');
    urumi_require($contract['BOOTSTRAP_VERSION'] === '3', 'Unsupported target bootstrap version.');
    $contract['PERMALINK_STRUCTURE'] = '/%postname%/';
    $contract['COMING_SOON'] = 'no';
    $contract['STORE_PAGES_ONLY'] = 'no';
    return $contract;
}
function urumi_validate_owner($contract, $owner, $marker) {
    $legacy = $contract;
    $legacy['BOOTSTRAP_VERSION'] = '2';
    unset($legacy['COMING_SOON'], $legacy['STORE_PAGES_ONLY']);
    // Target ownership with marker 2 is the final two-write crash window.
    // Older v1 stores require the separately reviewed v1-to-v2 migration first.
    urumi_require(($owner === $legacy && $marker === '2')
        || ($owner === $contract && in_array($marker, [null, '2', '3'], true)),
        'Unclaimed store or unsupported bootstrap transition; explicit review required.');
}
function urumi_validate_permalink($marker, $current) {
    urumi_require($current === '/%postname%/'
        || ($marker === null && $current === ''),
        'Completed stores must preserve postname permalinks; only fresh bootstrap may start Plain.');
}
function urumi_validate_visibility($contract, $owner, $marker) {
    $current = [get_option('woocommerce_coming_soon', null),
        get_option('woocommerce_store_pages_only', null)];
    if ($owner === $contract && $marker !== null) {
        // Advancing ownership happens only after both values have been verified.
        urumi_require($current === ['no', 'no'], 'Established v3 Live visibility has drifted.');
    } else {
        // Pinned WooCommerce defaults, first-write interruption, or target state.
        // Missing options, wrong types and the unrelated yes/no pair are refused.
        urumi_require(in_array($current, [['yes', 'yes'], ['no', 'yes'], ['no', 'no']], true),
            'Visibility conflicts with the recognized Coming Soon-to-Live transition.');
    }
}
function urumi_verify_live() {
    urumi_require(get_option('woocommerce_coming_soon', null) === 'no'
        && get_option('woocommerce_store_pages_only', null) === 'no',
        'Persisted public Live visibility is not verified.');
}
function urumi_make_live($contract) {
    // Verify all existing configuration and routes before either visibility write.
    urumi_configure($contract);
    urumi_verify_rewrites();
    foreach (['woocommerce_coming_soon', 'woocommerce_store_pages_only'] as $key) {
        if (get_option($key, null) !== 'no') {
            urumi_save($key, 'no');
        }
    }
    urumi_verify_live();
}
function urumi_save($key, $value) {
    update_option($key, $value, false);
    urumi_require(get_option($key, null) === $value, 'Could not verify a persisted bootstrap setting.');
}
function urumi_pages($complete) {
    $missing = false;
    foreach (['shop', 'cart', 'checkout', 'myaccount'] as $page) {
        $id = wc_get_page_id($page);
        if ($id <= 0) {
            $missing = true;
        } else {
            $post = get_post($id);
            urumi_require($post && $post->post_type === 'page' && $post->post_status === 'publish',
                'An established WooCommerce page is invalid; review it manually.');
        }
    }
    urumi_require(!$complete || !$missing, 'An established WooCommerce page is missing.');
    if ($missing) {
        WC_Install::create_pages(); // Uses stored page IDs/content; no unconditional page creation.
    }
    foreach (['shop', 'cart', 'checkout', 'myaccount'] as $page) {
        $post = get_post(wc_get_page_id($page));
        urumi_require($post && $post->post_type === 'page' && $post->post_status === 'publish',
            'WooCommerce page initialization failed.');
    }
}
function urumi_verify_rewrites() {
    global $wp_rewrite;
    if (!function_exists('extract_from_markers')) {
        require_once ABSPATH . 'wp-admin/includes/misc.php';
    }
    urumi_require(get_option('permalink_structure') === '/%postname%/',
        'Expected permalink structure is missing.');
    // Compare persisted rules, not a helper that silently regenerates missing rules.
    $rules = get_option('rewrite_rules');
    urumi_require(is_array($rules) && count($rules) > 1,
        'Persisted WordPress rewrite rules are missing.');
    urumi_require(trim((string) $wp_rewrite->get_extra_permastruct('product'), '/') === 'product/%product%',
        'Unexpected WooCommerce product permalink base; no overwrite performed.');
    $product_rule = false;
    $shop_rule = false;
    foreach ($rules as $pattern => $query) {
        $regex = '#^' . str_replace('#', '\\#', $pattern) . '#';
        if (is_string($query) && preg_match($regex, 'product/urumi-route-check/')
            && str_contains($query, 'product=$matches[')) {
            $product_rule = true;
        }
        if (is_string($query) && preg_match($regex, 'shop/')
            && $query === 'index.php?post_type=product') {
            $shop_rule = true;
        }
    }
    $shop_id = wc_get_page_id('shop');
    // WooCommerce's shop is a product archive, not a singular page query.
    urumi_require($product_rule && $shop_rule && get_permalink($shop_id) === home_url('/shop/')
        && get_post_type_archive_link('product') === home_url('/shop/'),
        'Shop/product rewrite verification failed.');
    $expected = trim($wp_rewrite->mod_rewrite_rules());
    $actual = trim(implode("\n", extract_from_markers(ABSPATH . '.htaccess', 'WordPress')));
    urumi_require($expected !== '' && $actual === $expected,
        'Persisted Apache WordPress rewrite block differs; hard flush was not verified.');
}
function urumi_record_completion($contract) {
    if (get_option('urumi_bootstrap_contract', null) !== $contract) {
        urumi_save('urumi_bootstrap_contract', $contract);
    }
    // Last write. A retry also recognizes target ownership with the old marker.
    if (get_option('urumi_bootstrap_version', null) !== $contract['BOOTSTRAP_VERSION']) {
        urumi_save('urumi_bootstrap_version', $contract['BOOTSTRAP_VERSION']);
    }
}
function urumi_finalize($contract) {
    urumi_configure($contract);
    urumi_verify_rewrites();
    urumi_verify_live();
    urumi_record_completion($contract);
}
function urumi_configure($contract) {
    global $wpdb;
    $wpdb->suppress_errors(true);
    urumi_require($wpdb->get_var('SELECT 1') === '1', 'Database verification failed.');
    urumi_require(defined('WC_VERSION') && WC_VERSION === $contract['WC_VERSION']
        && class_exists('WooCommerce', false)
        && in_array('woocommerce/woocommerce.php', (array) get_option('active_plugins'), true),
        'Expected active WooCommerce version is not loaded.');
    urumi_require(defined('AUTOMATIC_UPDATER_DISABLED') && AUTOMATIC_UPDATER_DISABLED
        && defined('WP_AUTO_UPDATE_CORE') && WP_AUTO_UPDATE_CORE === false,
        'Automatic update policy is not configured.');
    urumi_require(isset(WC()->countries->get_countries()[$contract['COUNTRY']])
        && isset(get_woocommerce_currencies()[$contract['CURRENCY']]),
        'Country or currency is invalid.');
    $marker = get_option('urumi_bootstrap_version', null);
    urumi_validate_owner($contract, get_option('urumi_bootstrap_contract', null), $marker);
    urumi_validate_permalink($marker, get_option('permalink_structure'));
    urumi_validate_visibility($contract, get_option('urumi_bootstrap_contract', null), $marker);
    $complete = $marker !== null;
    urumi_require(!is_multisite() && home_url() === site_url(),
        'Only the existing single-site, root-webroot layout is supported.');
    $htaccess = ABSPATH . '.htaccess';
    urumi_require(file_exists($htaccess) ? is_writable($htaccess) : is_writable(ABSPATH),
        'The bootstrap identity cannot persist Apache rewrite rules.');

    // A completed store is verification-only. Partial runs may resume only from
    // the recorded original value or our intended value, never an unknown edit.
    $plan = get_option('urumi_bootstrap_settings', null);
    if ($plan === null) {
        urumi_require(!$complete, 'Completed bootstrap has no settings checkpoint.');
        urumi_require(count(wc_get_orders(['limit' => 1, 'return' => 'ids'])) === 0
            && count(wc_get_products(['limit' => 1, 'return' => 'ids'])) === 0,
            'An unconfigured store contains transactions/products; review before adoption.');
        $cod = get_option('woocommerce_cod_settings', []);
        urumi_require(is_array($cod), 'COD configuration is invalid.');
        $targets = [
            'home' => $contract['CANONICAL_URL'], 'siteurl' => $contract['CANONICAL_URL'],
            'blogname' => $contract['SITE_TITLE'], 'timezone_string' => $contract['TIMEZONE'],
            'woocommerce_default_country' => $contract['COUNTRY'],
            'woocommerce_currency' => $contract['CURRENCY'],
            'woocommerce_allowed_countries' => 'all', 'woocommerce_ship_to_countries' => '',
            'woocommerce_enable_guest_checkout' => 'yes', 'woocommerce_calc_taxes' => 'no',
            'woocommerce_cod_settings' => array_replace($cod, [
                'enabled' => 'yes', 'enable_for_methods' => [], 'enable_for_virtual' => 'yes',
            ]),
        ];
        $plan = [];
        foreach ($targets as $key => $value) {
            $plan[$key] = ['before' => get_option($key, null), 'target' => $value];
        }
        urumi_save('urumi_bootstrap_settings', $plan);
    }
    urumi_require(is_array($plan), 'Settings checkpoint is invalid.');
    foreach ($plan as $key => $entry) {
        $current = get_option($key, null);
        if ($current !== $entry['target']) {
            urumi_require(!$complete && $current === $entry['before'],
                'Managed store setting conflicts with its checkpoint; no reset performed.');
            urumi_save($key, $entry['target']);
        }
    }
    urumi_pages($complete);
    // Zone 0 means "locations not covered by other zones": unrestricted shipping.
    urumi_require(count(WC_Shipping_Zones::get_zones()) === 0,
        'Custom shipping zones conflict with the demo baseline.');
    $zone = new WC_Shipping_Zone(0);
    $methods = $zone->get_shipping_methods(false);
    if (count($methods) === 0 && !$complete) {
        urumi_require($zone->add_shipping_method('free_shipping') > 0,
            'Free shipping method creation failed.');
        $methods = $zone->get_shipping_methods(false);
    }
    urumi_require(count($methods) === 1, 'Expected exactly one free shipping method.');
    $method = reset($methods);
    urumi_require($method->id === 'free_shipping' && $method->enabled === 'yes'
        && $method->get_option('requires', '') === '',
        'Shipping configuration conflicts; no overwrite performed.');
    // Refresh gateway settings after option writes; verify API-visible configuration.
    $gateways = WC()->payment_gateways()->payment_gateways();
    urumi_require(isset($gateways['cod']), 'COD gateway is unavailable.');
    $gateways['cod']->init_settings();
    urumi_require($gateways['cod']->get_option('enabled') === 'yes', 'COD is not enabled.');
    foreach ($plan as $key => $entry) {
        urumi_require(get_option($key, null) === $entry['target'], 'Final settings verification failed.');
    }
    urumi_require($wpdb->get_var('SELECT 1') === '1', 'Final database verification failed.');
    if ($complete) {
        // A v2/v3 migration must not silently repair established routing drift.
        urumi_verify_rewrites();
    }
    // Completion waits for a fresh process to verify rewrites AND Live visibility.
}

try {
    $mode = defined('WP_CLI') && WP_CLI ? ($args[0] ?? '') : ($argv[1] ?? '');
    if ($mode === 'db-ready' || $mode === 'db-empty') {
        $db = urumi_db();
        if ($mode === 'db-empty') {
            $tables = $db->query('SHOW TABLES');
            urumi_require($tables && $tables->num_rows === 0,
                'Database is nonempty; refusing automatic first-install repair.');
        }
        $db->close();
    } elseif ($mode === 'download') {
        $url = urumi_env('URUMI_WC_ARCHIVE_URL');
        urumi_require(str_starts_with($url, 'https://downloads.wordpress.org/plugin/woocommerce.'),
            'Unexpected archive source.');
        $context = stream_context_create(['http' => [
            'timeout' => (int) urumi_env('URUMI_COMMAND_SECONDS'), 'max_redirects' => 3,
        ]]);
        $input = @fopen($url, 'rb', false, $context);
        $path = '/tmp/urumi-bootstrap/woocommerce.zip';
        $output = @fopen($path, 'wb');
        urumi_require($input && $output, 'Could not open the versioned archive download.');
        urumi_require(stream_copy_to_stream($input, $output) !== false, 'Archive download failed.');
        fclose($input);
        fclose($output);
        urumi_require(hash_equals(urumi_env('URUMI_WC_SHA256'), hash_file('sha256', $path)),
            'WooCommerce archive checksum mismatch.');
    } else {
        urumi_require(defined('WP_CLI') && WP_CLI && is_blog_installed(), 'WordPress must be installed.');
        $contract = urumi_contract();
        $owner = get_option('urumi_bootstrap_contract', null);
        if ($mode === 'claim') {
            urumi_require($owner === null && get_option('urumi_bootstrap_version', null) === null,
                'The installation already has bootstrap ownership or a marker.');
            urumi_save('urumi_bootstrap_contract', $contract);
        } else {
            $marker = get_option('urumi_bootstrap_version', null);
            urumi_validate_owner($contract, $owner, $marker);
            urumi_validate_permalink($marker, get_option('permalink_structure'));
            if ($marker !== null) {
                urumi_require(is_file(WP_PLUGIN_DIR . '/woocommerce/woocommerce.php')
                    && in_array('woocommerce/woocommerce.php', (array) get_option('active_plugins'), true),
                    'Completed store WooCommerce is missing/inactive; refusing automatic repair.');
            }
            if (in_array($mode, ['configure', 'make-live', 'finalize'], true)) {
                if ($mode === 'finalize') {
                    urumi_finalize($contract);
                } elseif ($mode === 'make-live') {
                    urumi_make_live($contract);
                } else {
                    urumi_configure($contract);
                }
            } else {
                urumi_require($mode === 'preflight', 'Unknown bootstrap action.');
            }
        }
        // An early WordPress exit(0) without this acknowledgement is not success.
        fwrite(STDOUT, "URUMI_BOOTSTRAP_OK\n");
    }
} catch (UrumiBootstrapFailure $failure) {
    fwrite(STDERR, $failure->getMessage() . "\n");
    exit(1);
} catch (Throwable $failure) {
    // Never log raw exception/DB/HTTP messages that might carry credentials.
    fwrite(STDERR, "Bootstrap operation failed; dependency or runtime error.\n");
    exit(1);
}
