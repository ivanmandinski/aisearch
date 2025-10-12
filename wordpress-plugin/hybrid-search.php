<?php
/**
 * Plugin Name: Hybrid Search
 * Plugin URI: https://wordpress.org/plugins/hybrid-search
 * Description: Professional hybrid search plugin powered by Qdrant, LlamaIndex, and Cerebras LLM.
 * Version: 2.6.7
 * Author: Hybrid Search Team
 * License: GPL v2 or later
 * Text Domain: hybrid-search
 * Requires at least: 5.0
 * Tested up to: 6.4
 * Requires PHP: 7.4
 * Network: false
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('HYBRID_SEARCH_VERSION', '2.6.7');
define('HYBRID_SEARCH_PLUGIN_URL', plugin_dir_url(__FILE__));
define('HYBRID_SEARCH_PLUGIN_PATH', plugin_dir_path(__FILE__));
define('HYBRID_SEARCH_PLUGIN_FILE', __FILE__);
define('HYBRID_SEARCH_PLUGIN_BASENAME', plugin_basename(__FILE__));

// Autoloader for classes
spl_autoload_register(function ($class) {
    $prefix = 'HybridSearch\\';
    $base_dir = HYBRID_SEARCH_PLUGIN_PATH . 'includes/';
    
    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }
    
    $relative_class = substr($class, $len);
    $file = $base_dir . str_replace('\\', '/', $relative_class) . '.php';
    
    if (file_exists($file)) {
        require $file;
    }
});

/**
 * Main Plugin Class
 * 
 * @package HybridSearch
 * @since 2.0.0
 */
final class HybridSearchPlugin {
    
    /**
     * Plugin instance
     * 
     * @var HybridSearchPlugin
     */
    private static $instance = null;
    
    /**
     * Plugin components
     * 
     * @var array
     */
    private $components = [];
    
    /**
     * Get plugin instance
     * 
     * @return HybridSearchPlugin
     */
    public static function getInstance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * Constructor
     */
    private function __construct() {
        $this->init();
    }
    
    /**
     * Initialize plugin
     * 
     * @since 2.0.0
     */
    private function init() {
        // Load dependencies
        $this->loadDependencies();
        
        // Initialize components
        $this->initComponents();
        
        // Register hooks
        $this->registerHooks();
        
        // Activation/Deactivation hooks
        register_activation_hook(HYBRID_SEARCH_PLUGIN_FILE, [$this, 'activate']);
        register_deactivation_hook(HYBRID_SEARCH_PLUGIN_FILE, [$this, 'deactivate']);
    }
    
    /**
     * Load plugin dependencies
     * 
     * @since 2.0.0
     */
    private function loadDependencies() {
        // Core classes
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Core/PluginManager.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Core/Security.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Core/Logger.php';
        
        // Database layer
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Database/DatabaseManager.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Database/AnalyticsRepository.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Database/CTRRepository.php';
        
        // API layer
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/API/SearchAPI.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/API/APIClient.php';
        
        // Admin layer
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Admin/AdminManager.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Admin/DashboardWidget.php';
        
        // AJAX layer
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/AJAX/AJAXManager.php';
        
        // Frontend layer
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Frontend/FrontendManager.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Frontend/ShortcodeManager.php';
        
        // Services
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Services/AnalyticsService.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Services/CTRService.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Services/CacheService.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Services/SmartCacheService.php';
        require_once HYBRID_SEARCH_PLUGIN_PATH . 'includes/Services/AutoIndexService.php';
    }
    
    /**
     * Initialize plugin components
     * 
     * @since 2.0.0
     */
    private function initComponents() {
        // Core components
        $this->components['plugin_manager'] = new \HybridSearch\Core\PluginManager();
        $this->components['security'] = new \HybridSearch\Core\Security();
        $this->components['logger'] = new \HybridSearch\Core\Logger();
        
        // Database components
        $this->components['database'] = new \HybridSearch\Database\DatabaseManager();
        $this->components['analytics_repo'] = new \HybridSearch\Database\AnalyticsRepository($this->components['database']);
        $this->components['ctr_repo'] = new \HybridSearch\Database\CTRRepository($this->components['database']);
        
        // API components
        $api_url = get_option('hybrid_search_api_url', '');
        $this->components['api_client'] = new \HybridSearch\API\APIClient([
            'url' => $api_url,
            'timeout' => 30,
        ]);
        $this->components['search_api'] = new \HybridSearch\API\SearchAPI($this->components['api_client']);
        
        // Services
        $this->components['cache'] = new \HybridSearch\Services\CacheService();
        $this->components['analytics_service'] = new \HybridSearch\Services\AnalyticsService(
            $this->components['analytics_repo'],
            $this->components['cache'],
            $this->components['logger']
        );
        $this->components['ctr_service'] = new \HybridSearch\Services\CTRService(
            $this->components['ctr_repo'],
            $this->components['cache'],
            $this->components['logger']
        );
        $this->components['auto_index'] = new \HybridSearch\Services\AutoIndexService(
            $this->components['search_api'],
            $this->components['logger']
        );
        
        // Admin components
        $this->components['admin'] = new \HybridSearch\Admin\AdminManager(
            $this->components['analytics_service'],
            $this->components['ctr_service']
        );
        $this->components['dashboard_widget'] = new \HybridSearch\Admin\DashboardWidget();
        
        // AJAX components
        $this->components['ajax'] = new \HybridSearch\AJAX\AJAXManager(
            $this->components['search_api'],
            $this->components['analytics_service'],
            $this->components['ctr_service'],
            $this->components['security']
        );
        
        // Frontend components
        $this->components['frontend'] = new \HybridSearch\Frontend\FrontendManager($this->components['search_api']);
        $this->components['shortcodes'] = new \HybridSearch\Frontend\ShortcodeManager($this->components['frontend']);
    }
    
    /**
     * Register WordPress hooks
     * 
     * @since 2.0.0
     */
    private function registerHooks() {
        add_action('init', [$this, 'initHooks']);
        add_action('wp_enqueue_scripts', [$this, 'enqueueScripts']);
        add_action('admin_enqueue_scripts', [$this, 'enqueueAdminScripts']);
        
        // Component-specific hooks
        $this->components['admin']->registerHooks();
        $this->components['ajax']->registerHooks();
        $this->components['frontend']->registerHooks();
        $this->components['shortcodes']->registerHooks();
        $this->components['auto_index']->registerHooks();
        
        // Register WP-Cron handler for single post indexing
        add_action('hybrid_search_index_single_post', [$this->components['auto_index'], 'indexSinglePost']);
    }
    
    /**
     * Initialize WordPress hooks
     * 
     * @since 2.0.0
     */
    public function initHooks() {
        // Add query vars
        add_filter('query_vars', [$this, 'addQueryVars']);
    }
    
    /**
     * Add query variables
     * 
     * @param array $vars
     * @return array
     */
    public function addQueryVars($vars) {
        $vars[] = 'hybrid_search';
        return $vars;
    }
    
    /**
     * Enqueue frontend scripts and styles
     * 
     * @since 2.0.0
     */
    public function enqueueScripts() {
        $this->components['frontend']->enqueueAssets();
    }
    
    /**
     * Enqueue admin scripts and styles
     * 
     * @since 2.0.0
     */
    public function enqueueAdminScripts($hook) {
        $this->components['admin']->enqueueAssets($hook);
    }
    
    /**
     * Get component instance
     * 
     * @param string $component
     * @return mixed|null
     */
    public function getComponent($component) {
        return isset($this->components[$component]) ? $this->components[$component] : null;
    }
    
    /**
     * Plugin activation
     * 
     * @since 2.0.0
     */
    public function activate() {
        $this->components['database']->createTables();
        flush_rewrite_rules();
        
        // Log activation
        $this->components['logger']->info('Plugin activated', [
            'version' => HYBRID_SEARCH_VERSION,
            'wp_version' => get_bloginfo('version'),
            'php_version' => PHP_VERSION
        ]);
    }
    
    /**
     * Plugin deactivation
     * 
     * @since 2.0.0
     */
    public function deactivate() {
        flush_rewrite_rules();
        
        // Log deactivation
        $this->components['logger']->info('Plugin deactivated');
    }
    
    /**
     * Prevent cloning
     */
    private function __clone() {}
    
    /**
     * Prevent unserialization
     */
    public function __wakeup() {}
}

// Initialize the plugin
function hybrid_search_init() {
    return HybridSearchPlugin::getInstance();
}

// Start the plugin
add_action('plugins_loaded', 'hybrid_search_init');
