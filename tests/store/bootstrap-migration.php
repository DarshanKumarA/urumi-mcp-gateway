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
$target = ['BOOTSTRAP_VERSION' => '2', 'COUNTRY' => 'IN', 'CURRENCY' => 'INR', 'WC_VERSION' => '11.2.1',
    'CANONICAL_URL' => home_url(), 'PERMALINK_STRUCTURE' => '/%postname%/'];
$legacy = $target;
$legacy['BOOTSTRAP_VERSION'] = '1';
unset($legacy['PERMALINK_STRUCTURE']);
function reset_fixture() {
    global $options, $writes, $legacy, $fail_key, $db_ready, $apache_rules, $product_structure;
    $writes = []; $fail_key = null; $db_ready = true;
    $product_structure = 'product/%product%';
    $apache_rules = ['RewriteEngine On', 'RewriteRule . /index.php [L]'];
    $options = [
        'urumi_bootstrap_contract' => $legacy, 'urumi_bootstrap_version' => '1',
        'urumi_bootstrap_settings' => ['woocommerce_currency' => ['before' => 'USD', 'target' => 'INR']],
        'woocommerce_currency' => 'INR', 'permalink_structure' => '',
        'active_plugins' => ['woocommerce/woocommerce.php'],
        'rewrite_rules' => [
            'shop/?$' => 'index.php?post_type=product',
            'product/([^/]+)/?$' => 'index.php?product=$matches[1]',
        ],
        // Sentinels stand for unrelated data: no production API may change them.
        'fixture_user' => 1, 'fixture_product_id' => 11, 'fixture_sku' => 'URUMI-DEMO-001',
        'fixture_order' => 123,
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
check($writes === [], 'v1 configure verifies without overwriting settings or data');
refused(fn() => urumi_finalize($target), 'no completion before structure changes');
check($writes === [], 'failed route verification leaves owner/marker untouched');
$options['permalink_structure'] = '/%postname%/'; // Simulated successful external CLI step.
$before = $options;
urumi_finalize($target);
check($writes === ['urumi_bootstrap_contract', 'urumi_bootstrap_version'], 'owner then marker last');
foreach ($before as $key => $value) {
    if (!in_array($key, ['urumi_bootstrap_contract', 'urumi_bootstrap_version'], true)) {
        check($options[$key] === $value, 'preserve ' . $key);
    }
}
$writes = [];
urumi_finalize($target);
check($writes === [], 'completed v2 finalization is idempotent');
$product_structure = '/product/%product%';
urumi_finalize($target);
check($writes === [], 'leading slash representation also verifies without writes');

foreach (['unknown-owner', 'wrong-country', 'unknown-marker', 'legacy-incomplete', 'settings-drift',
    'custom-permalinks', 'completed-plain', 'missing-checkpoint', 'db-down', 'empty-rules',
    'missing-product-rule', 'missing-shop-rule', 'wrong-product-base', 'failed-hard-flush'] as $case) {
    reset_fixture();
    $options['permalink_structure'] = '/%postname%/';
    switch ($case) {
        case 'unknown-owner': $options['urumi_bootstrap_contract'] = null; break;
        case 'wrong-country': $options['urumi_bootstrap_contract']['COUNTRY'] = 'US'; break;
        case 'unknown-marker': $options['urumi_bootstrap_version'] = '9'; break;
        case 'legacy-incomplete': $options['urumi_bootstrap_version'] = null; break;
        case 'settings-drift': $options['woocommerce_currency'] = 'USD'; break;
        case 'custom-permalinks': $options['permalink_structure'] = '/archives/%post_id%/'; break;
        case 'completed-plain':
            $options['urumi_bootstrap_contract'] = $target; $options['urumi_bootstrap_version'] = '2';
            $options['permalink_structure'] = ''; break;
        case 'missing-checkpoint': $options['urumi_bootstrap_settings'] = null; break;
        case 'db-down': $db_ready = false; break;
        case 'empty-rules': $options['rewrite_rules'] = []; break;
        case 'missing-product-rule': unset($options['rewrite_rules']['product/([^/]+)/?$']); break;
        case 'missing-shop-rule': unset($options['rewrite_rules']['shop/?$']); break;
        case 'wrong-product-base': $product_structure = 'catalog/%product%'; break;
        case 'failed-hard-flush': $apache_rules = ['stale rules']; break;
    }
    refused(fn() => urumi_finalize($target), $case);
    check($writes === [], $case . ' must not advance completion');
}
foreach (['urumi_bootstrap_contract', 'urumi_bootstrap_version'] as $key) {
    reset_fixture();
    $options['permalink_structure'] = '/%postname%/';
    $fail_key = $key;
    refused(fn() => urumi_finalize($target), 'interrupted ' . $key);
    check($options['urumi_bootstrap_version'] === '1', 'old marker survives interrupted completion');
    $fail_key = null;
    urumi_finalize($target);
    check($options['urumi_bootstrap_version'] === '2', 'recognized interrupted completion resumes');
}
reset_fixture();
$options['urumi_bootstrap_contract'] = $target;
$options['urumi_bootstrap_version'] = null; // Fresh v2 installation after base configuration.
$options['permalink_structure'] = '/%postname%/';
urumi_finalize($target);
check($writes === ['urumi_bootstrap_version'], 'fresh v2 marks completion after verification');
echo "PASS: $tests migration assertions; isolated fixtures, no WordPress/database bootstrap executed.\n";
