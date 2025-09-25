<?php
/**
 * Plugin Name: SCS Engineers Hybrid Search
 * Plugin URI: https://www.scsengineers.com
 * Description: Replace WordPress native search with hybrid search powered by Qdrant, LlamaIndex, and Cerebras LLM for SCS Engineers.
 * Version: 1.0.0
 * Author: SCS Engineers
 * License: GPL v2 or later
 * Text Domain: scs-hybrid-search
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('HYBRID_SEARCH_VERSION', '1.0.0');
define('HYBRID_SEARCH_PLUGIN_URL', plugin_dir_url(__FILE__));
define('HYBRID_SEARCH_PLUGIN_PATH', plugin_dir_path(__FILE__));

/**
 * Main Hybrid Search Plugin Class
 */
class HybridSearchPlugin {
    
    private $api_url;
    private $api_key;
    private $enabled;
    
    public function __construct() {
        $this->init();
    }
    
    /**
     * Initialize the plugin
     */
    private function init() {
        // Load plugin options
        $this->load_options();
        
        // Register hooks
        add_action('init', array($this, 'init_hooks'));
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'register_settings'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        add_action('wp_ajax_hybrid_search', array($this, 'handle_ajax_search'));
        add_action('wp_ajax_nopriv_hybrid_search', array($this, 'handle_ajax_search'));
        
        // Replace default search
        add_filter('posts_search', array($this, 'replace_search_query'), 10, 2);
        add_filter('search_template', array($this, 'load_search_template'));
    }
    
    /**
     * Load plugin options
     */
    private function load_options() {
        $this->api_url = get_option('hybrid_search_api_url', '');
        $this->api_key = get_option('hybrid_search_api_key', '');
        $this->enabled = get_option('hybrid_search_enabled', false);
    }
    
    /**
     * Initialize hooks
     */
    public function init_hooks() {
        // Add rewrite rules for search
        add_rewrite_rule(
            '^search/([^/]+)/?$',
            'index.php?hybrid_search=1&s=$matches[1]',
            'top'
        );
        
        // Add query vars
        add_filter('query_vars', array($this, 'add_query_vars'));
    }
    
    /**
     * Add query variables
     */
    public function add_query_vars($vars) {
        $vars[] = 'hybrid_search';
        return $vars;
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'SCS Engineers Hybrid Search Settings',
            'SCS Hybrid Search',
            'manage_options',
            'hybrid-search',
            array($this, 'admin_page')
        );
    }
    
    /**
     * Register settings
     */
    public function register_settings() {
        register_setting('hybrid_search_settings', 'hybrid_search_api_url');
        register_setting('hybrid_search_settings', 'hybrid_search_api_key');
        register_setting('hybrid_search_settings', 'hybrid_search_enabled');
        register_setting('hybrid_search_settings', 'hybrid_search_max_results');
        register_setting('hybrid_search_settings', 'hybrid_search_include_answer');
    }
    
    /**
     * Admin page
     */
    public function admin_page() {
        ?>
        <div class="wrap">
            <h1>SCS Engineers Hybrid Search Settings</h1>
            <form method="post" action="options.php">
                <?php
                settings_fields('hybrid_search_settings');
                do_settings_sections('hybrid_search_settings');
                ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">Enable Hybrid Search</th>
                        <td>
                            <input type="checkbox" name="hybrid_search_enabled" value="1" <?php checked(1, get_option('hybrid_search_enabled'), true); ?> />
                            <p class="description">Replace WordPress native search with hybrid search</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">API URL</th>
                        <td>
                            <input type="url" name="hybrid_search_api_url" value="<?php echo esc_attr(get_option('hybrid_search_api_url')); ?>" class="regular-text" />
                            <p class="description">URL of your hybrid search API (e.g., https://your-api.railway.app)</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">API Key</th>
                        <td>
                            <input type="password" name="hybrid_search_api_key" value="<?php echo esc_attr(get_option('hybrid_search_api_key')); ?>" class="regular-text" />
                            <p class="description">API key for authentication (if required)</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Max Results</th>
                        <td>
                            <input type="number" name="hybrid_search_max_results" value="<?php echo esc_attr(get_option('hybrid_search_max_results', 10)); ?>" min="1" max="50" />
                            <p class="description">Maximum number of search results to display</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Include AI Answer</th>
                        <td>
                            <input type="checkbox" name="hybrid_search_include_answer" value="1" <?php checked(1, get_option('hybrid_search_include_answer'), true); ?> />
                            <p class="description">Include AI-generated answer with search results</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
            
            <div class="card">
                <h2>API Status</h2>
                <button type="button" id="test-api" class="button">Test API Connection</button>
                <div id="api-status"></div>
            </div>
        </div>
        
        <script>
        document.getElementById('test-api').addEventListener('click', function() {
            const statusDiv = document.getElementById('api-status');
            statusDiv.innerHTML = 'Testing...';
            
            fetch('<?php echo admin_url('admin-ajax.php'); ?>', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=test_hybrid_search_api'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusDiv.innerHTML = '<p style="color: green;">✓ API connection successful</p>';
                } else {
                    statusDiv.innerHTML = '<p style="color: red;">✗ API connection failed: ' + data.message + '</p>';
                }
            })
            .catch(error => {
                statusDiv.innerHTML = '<p style="color: red;">✗ Error: ' + error.message + '</p>';
            });
        });
        </script>
        <?php
    }
    
    /**
     * Enqueue scripts and styles
     */
    public function enqueue_scripts() {
        if (is_search() || get_query_var('hybrid_search')) {
            wp_enqueue_script(
                'hybrid-search',
                HYBRID_SEARCH_PLUGIN_URL . 'assets/hybrid-search.js',
                array('jquery'),
                HYBRID_SEARCH_VERSION,
                true
            );
            
            wp_enqueue_style(
                'hybrid-search',
                HYBRID_SEARCH_PLUGIN_URL . 'assets/hybrid-search.css',
                array(),
                HYBRID_SEARCH_VERSION
            );
            
            // Localize script
            wp_localize_script('hybrid-search', 'hybridSearch', array(
                'ajaxUrl' => admin_url('admin-ajax.php'),
                'apiUrl' => get_option('hybrid_search_api_url'),
                'apiKey' => get_option('hybrid_search_api_key'),
                'maxResults' => get_option('hybrid_search_max_results', 10),
                'includeAnswer' => get_option('hybrid_search_include_answer', false)
            ));
        }
    }
    
    /**
     * Handle AJAX search
     */
    public function handle_ajax_search() {
        check_ajax_referer('hybrid_search_nonce', 'nonce');
        
        $query = sanitize_text_field($_POST['query']);
        $limit = intval($_POST['limit']) ?: 10;
        $include_answer = isset($_POST['include_answer']) ? (bool)$_POST['include_answer'] : false;
        
        $results = $this->perform_search($query, $limit, $include_answer);
        
        wp_send_json_success($results);
    }
    
    /**
     * Test API connection
     */
    public function test_api_connection() {
        $api_url = get_option('hybrid_search_api_url');
        
        if (empty($api_url)) {
            return array('success' => false, 'message' => 'API URL not configured');
        }
        
        $response = wp_remote_get($api_url . '/health', array(
            'timeout' => 10,
            'headers' => array(
                'User-Agent' => 'WordPress Hybrid Search Plugin'
            )
        ));
        
        if (is_wp_error($response)) {
            return array('success' => false, 'message' => $response->get_error_message());
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        if ($data && $data['status'] === 'healthy') {
            return array('success' => true, 'message' => 'API is healthy');
        } else {
            return array('success' => false, 'message' => 'API returned unhealthy status');
        }
    }
    
    /**
     * Perform search via API
     */
    private function perform_search($query, $limit = 10, $include_answer = false) {
        $api_url = get_option('hybrid_search_api_url');
        $api_key = get_option('hybrid_search_api_key');
        
        if (empty($api_url)) {
            return array('error' => 'API URL not configured');
        }
        
        $request_data = array(
            'query' => $query,
            'limit' => $limit,
            'include_answer' => $include_answer
        );
        
        $headers = array(
            'Content-Type' => 'application/json',
            'User-Agent' => 'WordPress Hybrid Search Plugin'
        );
        
        if (!empty($api_key)) {
            $headers['Authorization'] = 'Bearer ' . $api_key;
        }
        
        $response = wp_remote_post($api_url . '/search', array(
            'headers' => $headers,
            'body' => json_encode($request_data),
            'timeout' => 30
        ));
        
        if (is_wp_error($response)) {
            return array('error' => $response->get_error_message());
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        if (!$data) {
            return array('error' => 'Invalid response from API');
        }
        
        return $data;
    }
    
    /**
     * Replace search query
     */
    public function replace_search_query($search, $wp_query) {
        if (!$this->enabled || !$wp_query->is_search()) {
            return $search;
        }
        
        // Store original search query for later use
        $wp_query->set('hybrid_search_query', $wp_query->get('s'));
        
        // Return empty search to prevent WordPress from searching
        return '';
    }
    
    /**
     * Load custom search template
     */
    public function load_search_template($template) {
        if (!$this->enabled) {
            return $template;
        }
        
        $custom_template = locate_template('hybrid-search-results.php');
        if ($custom_template) {
            return $custom_template;
        }
        
        // Load default template from plugin
        return HYBRID_SEARCH_PLUGIN_PATH . 'templates/search-results.php';
    }
}

// Initialize the plugin
new HybridSearchPlugin();

// Activation hook
register_activation_hook(__FILE__, function() {
    // Add rewrite rules
    add_rewrite_rule(
        '^search/([^/]+)/?$',
        'index.php?hybrid_search=1&s=$matches[1]',
        'top'
    );
    
    flush_rewrite_rules();
});

// Deactivation hook
register_deactivation_hook(__FILE__, function() {
    flush_rewrite_rules();
});
