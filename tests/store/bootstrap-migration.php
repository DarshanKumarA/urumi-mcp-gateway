<?php
// Isolated fixtures: load function declarations ONLY, never the bootstrap entrypoint.
// Run with PHP 8.3: php tests/store/bootstrap-migration.php
// For stdin validation, prepend those declarations to this file's body.
if (!function_exists('urumi_finalize')) {
    $source = file_get_contents(__DIR__ . '/../../charts/urumi/files/store/configure-woocommerce.php');
    $boundary = strpos($source, "\ntry {");
    if ($boundary === false) { throw new RuntimeException('Missing entrypoint boundary'); }
    eval(substr($source, 5, $boundary - 5));
}
define('ABSPATH', sys_get_temp_dir() . '/');
define('WC_VERSION', '11.2.1');
define('AUTOMATIC_UPDATER_DISABLED', true);
define('WP_AUTO_UPDATE_CORE', false);
$options = $writes = [];
$fail_key = null;
$db_ready = true;
$product_structure = 'product/%product%';
$apache_rules = ['RewriteEngine On', 'RewriteRule . /index.php [L]'];
function get_option($key, $default = false) { global $options; return $options[$key] ?? $default; }
function update_option($key, $value, $autoload = null) {
    global $options, $writes, $fail_key;
    if ($key === $fail_key) { return false; }
    $writes[] = $key;
    $options[$key] = $value;
    return true;
}
function is_multisite() { return false; }
function home_url($path = '') { return 'http://store.example.invalid' . $path; }
function site_url() { return home_url(); }
function get_woocommerce_currencies() { return ['INR' => 'Indian rupee']; }
function wc_get_page_id($page) { return 5; }
function get_post($id) { return (object) ['post_type' => 'page', 'post_status' => 'publish']; }
function get_permalink($id) { return home_url('/shop/'); }
function get_post_type_archive_link($type) { return home_url('/shop/'); }
function extract_from_markers($path, $marker) { global $apache_rules; return $apache_rules; }
function wc_get_orders($args) { throw new RuntimeException('Existing data must not be reseeded'); }
function wc_get_products($args) { throw new RuntimeException('Existing data must not be reseeded'); }
function wp_insert_user($data) { throw new RuntimeException('Users must not be reset'); }
function wp_update_user($data) { throw new RuntimeException('Users must not be reset'); }
function wp_set_password($value, $id) { throw new RuntimeException('Passwords must not be reset'); }
function wc_create_order($args = []) { throw new RuntimeException('Orders must not be created'); }
class WC_Product_Simple { function __construct() { throw new RuntimeException('Products must not be created'); } }
class WooCommerce {}
class FixtureGateway {
    function init_settings() {}
    function get_option($key) { return 'yes'; }
}
class FixtureStore {
    public $countries;
    function __construct() { $this->countries = $this; }
    function get_countries() { return ['IN' => 'India']; }
    function payment_gateways() { return ['cod' => new FixtureGateway()]; }
}
function WC() {
    return new class extends FixtureStore {
        function payment_gateways() { return new FixtureStore(); }
    };
}
class WC_Shipping_Zones { static function get_zones() { return []; } }
class WC_Shipping_Zone {
    function __construct($id) {}
    function get_shipping_methods($enabled) {
        return [new class {
            public $id = 'free_shipping';
            public $enabled = 'yes';
            function get_option($key, $default = '') { return ''; }
        }];
    }
}
$wpdb = new class {
    function suppress_errors($value) {}
    function get_var($query) { global $db_ready; return $db_ready ? '1' : null; }
};
$wp_rewrite = new class {
    function get_extra_permastruct($type) { global $product_structure; return $product_structure; }
    function mod_rewrite_rules() { return "RewriteEngine On\nRewriteRule . /index.php [L]\n"; }
};
$target = ['BOOTSTRAP_VERSION' => '3', 'COUNTRY' => 'IN', 'CURRENCY' => 'INR', 'WC_VERSION' => '11.2.1',
    'CANONICAL_URL' => home_url(), 'PERMALINK_STRUCTURE' => '/%postname%/',
    'COMING_SOON' => 'no', 'STORE_PAGES_ONLY' => 'no'];
$legacy = $target;
$legacy['BOOTSTRAP_VERSION'] = '2';
unset($legacy['COMING_SOON'], $legacy['STORE_PAGES_ONLY']);
function reset_fixture() {
    global $options, $writes, $legacy, $fail_key, $db_ready, $apache_rules, $product_structure;
    $writes = []; $fail_key = null; $db_ready = true;
    $product_structure = 'product/%product%';
    $apache_rules = ['RewriteEngine On', 'RewriteRule . /index.php [L]'];
    $options = [
        'urumi_bootstrap_contract' => $legacy, 'urumi_bootstrap_version' => '2',
        'urumi_bootstrap_settings' => ['woocommerce_currency' => ['before' => 'USD', 'target' => 'INR']],
        'woocommerce_currency' => 'INR', 'permalink_structure' => '/%postname%/',
        'woocommerce_coming_soon' => 'yes', 'woocommerce_store_pages_only' => 'yes',
        'active_plugins' => ['woocommerce/woocommerce.php'],
        'rewrite_rules' => [
            'shop/?$' => 'index.php?post_type=product',
            'product/([^/]+)/?$' => 'index.php?product=$matches[1]',
        ],
        // Sentinels stand for unrelated data: no production API may change them.
        'fixture_user' => ['id' => 1, 'credential_state' => 'unchanged-test-sentinel'],
        'fixture_product' => ['id' => 11, 'sku' => 'URUMI-DEMO-001', 'price' => '499',
            'status' => 'publish', 'stock' => 'instock'],
        'fixture_order' => ['id' => 12, 'status' => 'processing', 'total' => '499.00',
            'currency' => 'INR', 'product' => 11, 'quantity' => 1, 'payment' => 'cod'],
    ];
}
$tests = 0;
function check($condition, $label) {
    global $tests;
    if (!$condition) { throw new RuntimeException($label); }
    $tests++;
}
function refused($operation, $label) {
    try { $operation(); } catch (UrumiBootstrapFailure $e) { check(true, $label); return; }
    throw new RuntimeException('Expected refusal: ' . $label);
}
reset_fixture();
urumi_configure($target);
check($writes === [], 'v2 configure verifies without overwriting settings or data');
refused(fn() => urumi_finalize($target), 'finalize must not repair or complete pre-launch visibility');
check($writes === [], 'failed visibility verification leaves owner/marker untouched');
$before = $options;
urumi_make_live($target);
check($writes === ['woocommerce_coming_soon', 'woocommerce_store_pages_only'], 'visibility writes in recognized order');
check($options['urumi_bootstrap_version'] === '2' && $options['urumi_bootstrap_contract'] === $legacy,
    'make-live never advances ownership or marker');
urumi_finalize($target);
check($writes === ['woocommerce_coming_soon', 'woocommerce_store_pages_only',
    'urumi_bootstrap_contract', 'urumi_bootstrap_version'], 'visibility, ownership, then marker LAST');
foreach ($before as $key => $value) {
    if (!in_array($key, ['woocommerce_coming_soon', 'woocommerce_store_pages_only',
        'urumi_bootstrap_contract', 'urumi_bootstrap_version'], true)) {
        check($options[$key] === $value, 'preserve ' . $key);
    }
}
$writes = [];
urumi_make_live($target);
urumi_finalize($target);
check($writes === [], 'completed v3 make-live/finalize is verification-only and idempotent');
$product_structure = '/product/%product%';
urumi_finalize($target);
check($writes === [], 'leading slash representation also verifies without writes');

foreach (['unknown-owner', 'wrong-country', 'unknown-marker', 'legacy-incomplete', 'legacy-v1', 'settings-drift',
    'custom-permalinks', 'completed-plain', 'missing-checkpoint', 'db-down', 'empty-rules',
    'missing-product-rule', 'missing-shop-rule', 'wrong-product-base', 'failed-hard-flush',
    'missing-visibility', 'invalid-value', 'wrong-type', 'unrecognized-pair', 'v3-drift',
    'target-owner-old-marker-drift', 'target-owner-marker-1', 'inactive-woocommerce', 'wrong-wc-contract'] as $case) {
    reset_fixture();
    switch ($case) {
        case 'unknown-owner': $options['urumi_bootstrap_contract'] = null; break;
        case 'wrong-country': $options['urumi_bootstrap_contract']['COUNTRY'] = 'US'; break;
        case 'unknown-marker': $options['urumi_bootstrap_version'] = '9'; break;
        case 'legacy-incomplete': $options['urumi_bootstrap_version'] = null; break;
        case 'legacy-v1':
            $options['urumi_bootstrap_contract']['BOOTSTRAP_VERSION'] = '1';
            unset($options['urumi_bootstrap_contract']['PERMALINK_STRUCTURE']);
            $options['urumi_bootstrap_version'] = '1'; break;
        case 'settings-drift': $options['woocommerce_currency'] = 'USD'; break;
        case 'custom-permalinks': $options['permalink_structure'] = '/archives/%post_id%/'; break;
        case 'completed-plain':
            $options['permalink_structure'] = ''; break;
        case 'missing-checkpoint': $options['urumi_bootstrap_settings'] = null; break;
        case 'db-down': $db_ready = false; break;
        case 'empty-rules': $options['rewrite_rules'] = []; break;
        case 'missing-product-rule': unset($options['rewrite_rules']['product/([^/]+)/?$']); break;
        case 'missing-shop-rule': unset($options['rewrite_rules']['shop/?$']); break;
        case 'wrong-product-base': $product_structure = 'catalog/%product%'; break;
        case 'failed-hard-flush': $apache_rules = ['stale rules']; break;
        case 'missing-visibility': unset($options['woocommerce_store_pages_only']); break;
        case 'invalid-value': $options['woocommerce_coming_soon'] = 'maybe'; break;
        case 'wrong-type': $options['woocommerce_coming_soon'] = true; break;
        case 'unrecognized-pair': $options['woocommerce_store_pages_only'] = 'no'; break;
        case 'v3-drift':
            $options['urumi_bootstrap_contract'] = $target; $options['urumi_bootstrap_version'] = '3'; break;
        case 'target-owner-old-marker-drift': $options['urumi_bootstrap_contract'] = $target; break;
        case 'target-owner-marker-1':
            $options['urumi_bootstrap_contract'] = $target; $options['urumi_bootstrap_version'] = '1'; break;
        case 'inactive-woocommerce': $options['active_plugins'] = []; break;
        case 'wrong-wc-contract': $options['urumi_bootstrap_contract']['WC_VERSION'] = 'other'; break;
    }
    refused(fn() => urumi_make_live($target), $case);
    check($writes === [], $case . ' must not write visibility or completion');
}
foreach (['woocommerce_coming_soon', 'woocommerce_store_pages_only',
    'urumi_bootstrap_contract', 'urumi_bootstrap_version'] as $key) {
    reset_fixture();
    $fail_key = $key;
    refused(function () use ($target) { urumi_make_live($target); urumi_finalize($target); }, 'interrupted ' . $key);
    check($options['urumi_bootstrap_version'] === '2', 'old marker survives interrupted completion');
    $fail_key = null;
    urumi_make_live($target);
    urumi_finalize($target);
    check($options['urumi_bootstrap_version'] === '3', 'recognized interrupted completion resumes');
    check(end($writes) === 'urumi_bootstrap_version', 'resumed marker remains last');
}
reset_fixture();
$options['urumi_bootstrap_contract'] = $target;
$options['urumi_bootstrap_version'] = null; // Fresh/partial v3 after its business-setting checkpoint.
urumi_make_live($target);
urumi_finalize($target);
check($writes === ['woocommerce_coming_soon', 'woocommerce_store_pages_only', 'urumi_bootstrap_version'],
    'fresh/partial v3 verifies before completion without reseeding existing data');

foreach ([['no', 'yes'], ['no', 'no']] as $pair) {
    reset_fixture();
    [$options['woocommerce_coming_soon'], $options['woocommerce_store_pages_only']] = $pair;
    urumi_make_live($target); urumi_finalize($target);
    check($options['urumi_bootstrap_version'] === '3', 'recognized v2 visibility pair resumes');
    reset_fixture();
    $options['urumi_bootstrap_contract'] = $target;
    $options['urumi_bootstrap_version'] = null;
    [$options['woocommerce_coming_soon'], $options['woocommerce_store_pages_only']] = $pair;
    urumi_make_live($target); urumi_finalize($target);
    check($options['urumi_bootstrap_version'] === '3', 'recognized partial v3 visibility pair resumes');
}
foreach (['2', '3'] as $marker) {
    reset_fixture();
    $options['urumi_bootstrap_contract'] = $target;
    $options['urumi_bootstrap_version'] = $marker;
    $options['woocommerce_coming_soon'] = 'no'; // The second invariant still matters.
    refused(fn() => urumi_make_live($target), 'v3 ownership cannot repair store-pages-only drift');
    check($writes === [], 'no visibility repair after v3 ownership');
}
reset_fixture();
urumi_make_live($target);
$writes = [];
$options['woocommerce_store_pages_only'] = 'yes'; // A new process sees lost/reverted persistence.
refused(fn() => urumi_finalize($target), 'fresh finalizer sees incomplete persisted Live state');
check($writes === [] && $options['urumi_bootstrap_version'] === '2', 'finalizer never repairs visibility or advances marker');
reset_fixture();
$options['urumi_bootstrap_contract'] = $target;
$options['urumi_bootstrap_version'] = null;
$options['permalink_structure'] = ''; // Fresh v3 still uses the existing CLI rewrite stage.
urumi_configure($target);
check($writes === [], 'fresh Plain state can reach the CLI rewrite stage');
refused(fn() => urumi_make_live($target), 'fresh Live writes wait for successful rewrite persistence');
check($writes === [], 'no publication before fresh rewrite verification');
$options['permalink_structure'] = '/%postname%/';
urumi_make_live($target); urumi_finalize($target);
check($options['urumi_bootstrap_version'] === '3', 'fresh v3 finishes after rewrite and Live verification');
echo "PASS: $tests migration assertions; isolated fixtures, no WordPress/database bootstrap executed.\n";
