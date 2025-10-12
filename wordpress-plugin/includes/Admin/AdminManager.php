<?php
/**
 * Admin Manager
 * 
 * Handles all admin interface functionality including menus, pages, and admin-specific features.
 * 
 * @package HybridSearch\Admin
 * @since 2.0.0
 */

namespace HybridSearch\Admin;

use HybridSearch\Services\AnalyticsService;
use HybridSearch\Services\CTRService;

class AdminManager {
    
    /**
     * Analytics service
     * 
     * @var AnalyticsService
     */
    private $analytics_service;
    
    /**
     * CTR service
     * 
     * @var CTRService
     */
    private $ctr_service;
    
    /**
     * Constructor
     * 
     * @param AnalyticsService $analytics_service
     * @param CTRService $ctr_service
     */
    public function __construct(AnalyticsService $analytics_service, CTRService $ctr_service) {
        $this->analytics_service = $analytics_service;
        $this->ctr_service = $ctr_service;
    }
    
    /**
     * Register WordPress hooks
     * 
     * @since 2.0.0
     */
    public function registerHooks() {
        add_action('admin_menu', [$this, 'addAdminMenu']);
        add_action('admin_enqueue_scripts', [$this, 'enqueueAssets']);
        add_action('admin_init', [$this, 'registerSettings']);
    }
    
    /**
     * Add admin menu
     * 
     * @since 2.0.0
     */
    public function addAdminMenu() {
        // Main menu page
        add_menu_page(
            'Hybrid Search',
            'Hybrid Search',
            'manage_options',
            'hybrid-search',
            [$this, 'dashboardPage'],
            'dashicons-search',
            30
        );
        
        // Submenu pages
        add_submenu_page(
            'hybrid-search',
            'Dashboard',
            'Dashboard',
            'manage_options',
            'hybrid-search',
            [$this, 'dashboardPage']
        );
        
        add_submenu_page(
            'hybrid-search',
            'Settings',
            'Settings',
            'manage_options',
            'hybrid-search-settings',
            [$this, 'settingsPage']
        );
        
        add_submenu_page(
            'hybrid-search',
            'Analytics',
            'Analytics',
            'manage_options',
            'hybrid-search-analytics',
            [$this, 'analyticsPage']
        );
    }
    
    /**
     * Register plugin settings
     * 
     * @since 2.0.0
     */
    public function registerSettings() {
        // Register settings group
        register_setting('hybrid_search_settings', 'hybrid_search_api_url');
        register_setting('hybrid_search_settings', 'hybrid_search_api_key');
        register_setting('hybrid_search_settings', 'hybrid_search_enabled');
        register_setting('hybrid_search_settings', 'hybrid_search_max_results');
        register_setting('hybrid_search_settings', 'hybrid_search_show_ai_answer');
        register_setting('hybrid_search_settings', 'hybrid_search_ai_instructions');
        register_setting('hybrid_search_settings', 'hybrid_search_index_post_types');
        register_setting('hybrid_search_settings', 'hybrid_search_post_type_priority');
        register_setting('hybrid_search_settings', 'hybrid_search_auto_index_enabled');
        
        // AI Reranking settings
        register_setting('hybrid_search_settings', 'hybrid_search_ai_reranking_enabled', [
            'type' => 'boolean',
            'default' => true,
            'sanitize_callback' => 'rest_sanitize_boolean'
        ]);
        
        register_setting('hybrid_search_settings', 'hybrid_search_ai_weight', [
            'type' => 'integer',
            'default' => 70,
            'sanitize_callback' => function($value) {
                return max(0, min(100, intval($value)));
            }
        ]);
        
        register_setting('hybrid_search_settings', 'hybrid_search_ai_reranking_instructions', [
            'type' => 'string',
            'default' => '',
            'sanitize_callback' => 'sanitize_textarea_field'
        ]);
    }
    
    /**
     * Dashboard page
     * 
     * @since 2.0.0
     */
    public function dashboardPage() {
        // Debug: Check if tables exist
        global $wpdb;
        $analytics_table = $wpdb->prefix . 'hybrid_search_analytics';
        $table_exists = $wpdb->get_var("SHOW TABLES LIKE '$analytics_table'") === $analytics_table;
        error_log('Hybrid Search Dashboard: Analytics table exists? ' . ($table_exists ? 'YES' : 'NO'));
        
        if (!$table_exists) {
            error_log('Hybrid Search Dashboard: Analytics table DOES NOT EXIST! Plugin may not be activated properly.');
        } else {
            $row_count = $wpdb->get_var("SELECT COUNT(*) FROM $analytics_table");
            error_log('Hybrid Search Dashboard: Analytics table has ' . $row_count . ' rows');
        }
        
        $dashboard_data = $this->analytics_service->getDashboardData();
        $ctr_data = $this->ctr_service->getDashboardData();
        
        error_log('Hybrid Search Dashboard: Quick stats - Total searches (30 days): ' . ($dashboard_data['quick_stats']['total_searches_30_days'] ?? '0'));
        
        ?>
        <div class="wrap">
            <h1>Hybrid Search Dashboard</h1>
            
            <div class="dashboard-container">
                <!-- Quick Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">🔍</div>
                        <div class="stat-number"><?php echo esc_html($dashboard_data['quick_stats']['total_searches_30_days']); ?></div>
                        <div class="stat-label">Total Searches (30 days)</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-number"><?php echo esc_html($dashboard_data['quick_stats']['searches_with_results_30_days']); ?></div>
                        <div class="stat-label">Successful Searches</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">⚡</div>
                        <div class="stat-number"><?php echo esc_html(round($dashboard_data['quick_stats']['avg_time_taken'], 2)); ?>s</div>
                        <div class="stat-label">Avg Response Time</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-number"><?php echo esc_html($ctr_data['ctr_overview']['overall_ctr_30_days']); ?>%</div>
                        <div class="stat-label">Overall CTR (30 days)</div>
                    </div>
                </div>
                
                <!-- Recent Activity -->
                <div class="dashboard-section">
                    <h2>Recent Search Activity</h2>
                    <div class="activity-list">
                        <?php if (!empty($dashboard_data['recent_searches'])): ?>
                            <?php foreach ($dashboard_data['recent_searches'] as $search): ?>
                                <div class="activity-item">
                                    <div class="activity-query"><?php echo esc_html($search['query']); ?></div>
                                    <div class="activity-meta">
                                        <?php echo esc_html($search['result_count']); ?> results • 
                                        <?php echo esc_html(human_time_diff(strtotime($search['timestamp']))); ?> ago
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php else: ?>
                            <div class="activity-item">No recent searches found.</div>
                        <?php endif; ?>
                    </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="dashboard-section">
                    <h2>Quick Actions</h2>
                    <div class="quick-actions">
                        <a href="<?php echo admin_url('admin.php?page=hybrid-search-settings'); ?>" class="action-button">
                            <span class="dashicons dashicons-admin-settings"></span>
                            Configure Settings
                        </a>
                        
                        <a href="<?php echo admin_url('admin.php?page=hybrid-search-analytics'); ?>" class="action-button">
                            <span class="dashicons dashicons-chart-bar"></span>
                            View Analytics
                        </a>
                        
                        <button type="button" onclick="testAPIConnection()" class="action-button">
                            <span class="dashicons dashicons-admin-tools"></span>
                            Test API Connection
                        </button>
                        
                        <button type="button" onclick="generateSampleData()" class="action-button">
                            <span class="dashicons dashicons-database-add"></span>
                            Generate Sample Data
                        </button>
                        
                        <button type="button" onclick="reindexContent()" class="action-button">
                            <span class="dashicons dashicons-update"></span>
                            Reindex Content
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        .dashboard-container {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }
        
        .stat-icon {
            font-size: 2rem;
            width: 60px;
            text-align: center;
            margin: 0 auto 15px;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #0073aa;
            line-height: 1;
            margin-bottom: 10px;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.9rem;
        }
        
        .dashboard-section {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .dashboard-section h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #0073aa;
            padding-bottom: 10px;
        }
        
        .activity-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .activity-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .activity-item:last-child {
            border-bottom: none;
        }
        
        .activity-query {
            font-weight: 500;
            color: #0073aa;
        }
        
        .activity-meta {
            color: #666;
            font-size: 0.9rem;
        }
        
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .action-button {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 6px;
            text-decoration: none;
            color: #333;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        
        .action-button:hover {
            background: #e9ecef;
            border-color: #0073aa;
            color: #0073aa;
        }
        </style>
        
        <script>
        function testAPIConnection() {
            // Implementation for API testing
            alert('API connection test functionality would be implemented here');
        }
        
        function generateSampleData() {
            // Implementation for sample data generation
            alert('Sample data generation functionality would be implemented here');
        }
        
        function reindexContent() {
            if (!confirm('This will reindex all your content. This may take some time. Continue?')) {
                return;
            }
            
            // Show loading state
            const button = event.target;
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="dashicons dashicons-update-alt"></span> Reindexing...';
            button.disabled = true;
            
            // Make AJAX request
            jQuery.post(ajaxurl, {
                action: 'reindex_content'
            }, function(response) {
                console.log('Reindex response:', response);
                
                if (response.success) {
                    alert('Content reindexed successfully!');
                } else {
                    // Handle different types of error responses
                    let errorMessage = 'Failed to reindex content';
                    if (response.data) {
                        if (typeof response.data === 'string') {
                            errorMessage = response.data;
                        } else if (response.data.message) {
                            errorMessage = response.data.message;
                        } else if (response.data.error) {
                            errorMessage = response.data.error;
                        } else {
                            // If data is an object, stringify it for debugging
                            errorMessage = JSON.stringify(response.data);
                        }
                    }
                    alert('Error: ' + errorMessage);
                }
            }).fail(function(xhr, status, error) {
                console.error('Reindex AJAX failed:', xhr, status, error);
                alert('Failed to reindex content: ' + error);
            }).always(function() {
                // Restore button state
                button.innerHTML = originalText;
                button.disabled = false;
            });
        }
        </script>
        <?php
    }
    
    /**
     * Settings page
     * 
     * @since 2.0.0
     */
    public function settingsPage() {
        ?>
        <div class="wrap">
            <h1>Hybrid Search Settings</h1>
            
            <form method="post" action="options.php">
                <?php
                settings_fields('hybrid_search_settings');
                do_settings_sections('hybrid_search_settings');
                ?>
                
                <table class="form-table">
                    <tr>
                        <th scope="row">API URL</th>
                        <td>
                            <input type="url" name="hybrid_search_api_url" value="<?php echo esc_attr(get_option('hybrid_search_api_url')); ?>" class="regular-text" />
                            <p class="description">Enter your hybrid search API endpoint URL.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">API Key</th>
                        <td>
                            <input type="password" name="hybrid_search_api_key" value="<?php echo esc_attr(get_option('hybrid_search_api_key')); ?>" class="regular-text" />
                            <p class="description">Enter your API authentication key.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Enable Hybrid Search</th>
                        <td>
                            <input type="checkbox" name="hybrid_search_enabled" value="1" <?php checked(get_option('hybrid_search_enabled'), 1); ?> />
                            <p class="description">Enable the hybrid search functionality.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Max Results</th>
                        <td>
                            <input type="number" name="hybrid_search_max_results" value="<?php echo esc_attr(get_option('hybrid_search_max_results', 10)); ?>" min="1" max="100" />
                            <p class="description">Maximum number of results to return per search.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Auto-Index Content</th>
                        <td>
                            <input type="checkbox" name="hybrid_search_auto_index_enabled" value="1" <?php checked(get_option('hybrid_search_auto_index_enabled', true), 1); ?> />
                            <p class="description">
                                <strong>Automatically index content when posts are created, updated, or deleted.</strong><br>
                                When enabled, new content is immediately searchable without manual reindexing.<br>
                                <em>Recommended: Keep this enabled for always up-to-date search results.</em>
                            </p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Post Types to Index</th>
                        <td>
                            <?php
                            // Get all public post types
                            $post_types = get_post_types(['public' => true], 'objects');
                            $selected_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
                            if (!is_array($selected_types)) {
                                $selected_types = ['post', 'page'];
                            }
                            ?>
                            <fieldset>
                                <legend class="screen-reader-text">Select post types to index</legend>
                                <?php foreach ($post_types as $post_type): ?>
                                    <label style="display: block; margin-bottom: 8px;">
                                        <input type="checkbox" 
                                               name="hybrid_search_index_post_types[]" 
                                               value="<?php echo esc_attr($post_type->name); ?>"
                                               <?php checked(in_array($post_type->name, $selected_types)); ?> />
                                        <strong><?php echo esc_html($post_type->labels->name); ?></strong>
                                        <span style="color: #666; font-size: 12px;">(<?php echo esc_html($post_type->name); ?>)</span>
                                    </label>
                                <?php endforeach; ?>
                            </fieldset>
                            <p class="description">
                                <strong>Select which post types to include in the search index.</strong><br>
                                Only selected post types will be indexed and searchable.<br>
                                <em>Note: You must reindex content after changing this setting.</em>
                            </p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Post Type Priority</th>
                        <td>
                            <?php
                            // Get all public post types
                            $all_post_types = get_post_types(['public' => true], 'objects');
                            $priority_order = get_option('hybrid_search_post_type_priority', ['post', 'page']);
                            if (!is_array($priority_order)) {
                                $priority_order = ['post', 'page'];
                            }
                            
                            // Add any post types that aren't in the priority list yet
                            foreach ($all_post_types as $pt) {
                                if (!in_array($pt->name, $priority_order)) {
                                    $priority_order[] = $pt->name;
                                }
                            }
                            ?>
                            <div id="post-type-priority-list" style="max-width: 500px;">
                                <?php foreach ($priority_order as $index => $post_type_name): ?>
                                    <?php 
                                    $post_type_obj = get_post_type_object($post_type_name);
                                    if (!$post_type_obj) continue;
                                    ?>
                                    <div class="post-type-priority-item" data-type="<?php echo esc_attr($post_type_name); ?>" style="
                                        background: #fff;
                                        border: 1px solid #ddd;
                                        border-radius: 6px;
                                        padding: 12px 15px;
                                        margin-bottom: 8px;
                                        cursor: move;
                                        display: flex;
                                        align-items: center;
                                        gap: 12px;
                                        transition: all 0.2s ease;
                                    ">
                                        <span style="
                                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                            color: white;
                                            width: 28px;
                                            height: 28px;
                                            border-radius: 50%;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            font-weight: 600;
                                            font-size: 13px;
                                        "><?php echo $index + 1; ?></span>
                                        <span style="
                                            font-size: 16px;
                                            cursor: move;
                                        ">⋮⋮</span>
                                        <div style="flex: 1;">
                                            <strong><?php echo esc_html($post_type_obj->labels->name); ?></strong>
                                            <span style="color: #666; font-size: 12px; margin-left: 8px;">(<?php echo esc_html($post_type_name); ?>)</span>
                                        </div>
                                        <input type="hidden" name="hybrid_search_post_type_priority[]" value="<?php echo esc_attr($post_type_name); ?>">
                                    </div>
                                <?php endforeach; ?>
                            </div>
                <p class="description">
                    <strong>Drag and drop to set search result priority order.</strong><br>
                    Search results will be grouped by post type in this order. All results from priority #1 will show first, then #2, etc.<br>
                    Within each group, results are sorted by relevance score (highest first).<br>
                    <em>Example: If "Services" is #1, all Service results appear before any Posts or Pages, regardless of relevance.</em><br>
                    <em>Tip: Put your most important content types at the top (e.g., Services, Products, Team Members).</em>
                </p>
                            
                            <script>
                            jQuery(document).ready(function($) {
                                // Make the list sortable (remove 'handle' to make entire item draggable)
                                $('#post-type-priority-list').sortable({
                                    cursor: 'move',
                                    placeholder: 'post-type-priority-placeholder',
                                    tolerance: 'pointer',
                                    update: function(event, ui) {
                                        // Update the numbers when order changes
                                        $('#post-type-priority-list .post-type-priority-item').each(function(index) {
                                            $(this).find('span:first').text(index + 1);
                                        });
                                    },
                                    start: function(event, ui) {
                                        $(ui.item).css('opacity', '0.6');
                                    },
                                    stop: function(event, ui) {
                                        $(ui.item).css('opacity', '1');
                                    }
                                });
                                
                                // Add hover effect
                                $('.post-type-priority-item').hover(
                                    function() {
                                        $(this).css({
                                            'background': '#f8f9fa',
                                            'border-color': '#667eea',
                                            'box-shadow': '0 2px 8px rgba(0,0,0,0.1)'
                                        });
                                    },
                                    function() {
                                        $(this).css({
                                            'background': '#fff',
                                            'border-color': '#ddd',
                                            'box-shadow': 'none'
                                        });
                                    }
                                );
                            });
                            </script>
                            
                            <style>
                            .post-type-priority-placeholder {
                                background: #e9ecef;
                                border: 2px dashed #667eea;
                                border-radius: 6px;
                                height: 52px;
                                margin-bottom: 8px;
                            }
                            </style>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Enable AI Answers</th>
                        <td>
                            <input type="checkbox" name="hybrid_search_show_ai_answer" value="1" <?php checked(get_option('hybrid_search_show_ai_answer'), 1); ?> />
                            <p class="description">
                                <strong>Enable AI-generated answers for search queries.</strong><br>
                                When enabled, the system will request AI answers from the search API and display them at the top of search results.<br>
                                <em>Note: This may increase search response time as AI answers require additional processing.</em>
                            </p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">AI Answer Instructions</th>
                        <td>
                            <textarea name="hybrid_search_ai_instructions" rows="6" cols="60" class="large-text" placeholder="Enter custom instructions for AI answer generation...

Examples:
- 'Provide concise, helpful answers based on the search results'
- 'Focus on technical details and practical applications'
- 'Answer in a friendly, conversational tone'
- 'Include relevant examples and use cases'

Leave empty for default behavior."><?php echo esc_textarea(get_option('hybrid_search_ai_instructions')); ?></textarea>
                            <p class="description">
                                <strong>Custom instructions for AI answer generation.</strong><br>
                                These instructions will guide how the AI generates answers for search queries.<br>
                                <em>Leave empty to use default AI behavior.</em>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- AI RERANKING SECTION -->
                    <tr>
                        <td colspan="2">
                            <h2 style="margin-top: 30px; padding-top: 30px; border-top: 2px solid #e0e0e0;">
                                🤖 AI-Powered Search Reranking
                            </h2>
                            <p style="font-size: 14px; color: #666; margin-bottom: 20px;">
                                Use AI to intelligently reorder search results based on semantic relevance and user intent, going beyond simple keyword matching.
                            </p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Enable AI Reranking</th>
                        <td>
                            <label>
                                <input type="checkbox" 
                                       name="hybrid_search_ai_reranking_enabled" 
                                       id="ai-reranking-enabled"
                                       value="1" 
                                       <?php checked(get_option('hybrid_search_ai_reranking_enabled', true), 1); ?> />
                                <strong>Use AI to intelligently rerank search results</strong>
                            </label>
                            <div style="margin-top: 15px; padding: 15px; background: #f0f6fc; border-left: 4px solid #667eea; border-radius: 4px;">
                                <p style="margin: 5px 0; font-size: 13px; color: #0066cc;">
                                    <strong>✨ How It Works:</strong><br>
                                    1. TF-IDF finds initial candidates (fast keyword matching)<br>
                                    2. AI analyzes top results for semantic relevance<br>
                                    3. Results are reordered by understanding, not just keywords<br>
                                    4. You get smarter, more relevant search results!
                                </p>
                            </div>
                            <p class="description" style="margin-top: 10px;">
                                When enabled, search results are reordered based on semantic understanding and user intent.<br>
                                <strong>Performance:</strong> Adds ~1-2 seconds to search time<br>
                                <strong>Cost:</strong> ~$0.15 per 1,000 searches (very affordable with Cerebras)<br>
                                <em>Recommended: Keep enabled for best search quality.</em>
                            </p>
                        </td>
                    </tr>
                    
                    <tr class="ai-reranking-setting">
                        <th scope="row">AI Reranking Weight</th>
                        <td>
                            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                                <label style="min-width: 120px; text-align: center;">
                                    <strong>Keyword Matching</strong><br>
                                    <small style="color: #666;">TF-IDF</small>
                                </label>
                                
                                <input type="range" 
                                       name="hybrid_search_ai_weight" 
                                       id="ai-weight-slider"
                                       min="0" 
                                       max="100" 
                                       value="<?php echo esc_attr(get_option('hybrid_search_ai_weight', 70)); ?>" 
                                       style="flex: 1; min-width: 300px;"
                                       oninput="updateAIWeightDisplay(this.value)" />
                                
                                <label style="min-width: 120px; text-align: center;">
                                    <strong>AI Understanding</strong><br>
                                    <small style="color: #666;">Semantic</small>
                                </label>
                            </div>
                            
                            <div style="margin-top: 15px; padding: 15px; background: #f0f6fc; border-left: 4px solid #667eea; border-radius: 4px;">
                                <div style="font-size: 18px; font-weight: 600; color: #667eea; margin-bottom: 8px;">
                                    Current Balance: 
                                    <span id="tfidf-percent"><?php echo 100 - get_option('hybrid_search_ai_weight', 70); ?>%</span> 
                                    TF-IDF + 
                                    <span id="ai-percent"><?php echo get_option('hybrid_search_ai_weight', 70); ?>%</span> 
                                    AI
                                </div>
                                
                                <div id="weight-description" style="font-size: 14px; color: #555;"></div>
                            </div>
                            
                            <p class="description" style="margin-top: 15px;">
                                <strong>How to choose:</strong><br>
                                • <strong>0-30%:</strong> Mostly keyword matching (fast, traditional search)<br>
                                • <strong>40-60%:</strong> Balanced approach (keywords + AI)<br>
                                • <strong>70-80%:</strong> Mostly AI (<span style="color: #667eea; font-weight: 600;">✓ Recommended</span> - best results)<br>
                                • <strong>90-100%:</strong> Pure AI semantic ranking (slowest but smartest)<br>
                            </p>
                            
                            <style>
                            #ai-weight-slider {
                                -webkit-appearance: none;
                                appearance: none;
                                height: 8px;
                                background: linear-gradient(to right, #3b82f6 0%, #667eea 100%);
                                border-radius: 4px;
                                outline: none;
                            }
                            
                            #ai-weight-slider::-webkit-slider-thumb {
                                -webkit-appearance: none;
                                appearance: none;
                                width: 24px;
                                height: 24px;
                                background: white;
                                border: 3px solid #667eea;
                                border-radius: 50%;
                                cursor: pointer;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                            }
                            
                            #ai-weight-slider::-moz-range-thumb {
                                width: 24px;
                                height: 24px;
                                background: white;
                                border: 3px solid #667eea;
                                border-radius: 50%;
                                cursor: pointer;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                            }
                            </style>
                            
                            <script>
                            function updateAIWeightDisplay(value) {
                                const aiWeight = parseInt(value);
                                const tfidfWeight = 100 - aiWeight;
                                
                                document.getElementById('ai-percent').textContent = aiWeight + '%';
                                document.getElementById('tfidf-percent').textContent = tfidfWeight + '%';
                                
                                const description = document.getElementById('weight-description');
                                
                                if (aiWeight <= 30) {
                                    description.innerHTML = '⚡ <strong>Fast & Traditional:</strong> Relies mostly on keyword matching. Good for exact phrase searches.';
                                } else if (aiWeight <= 60) {
                                    description.innerHTML = '⚖️ <strong>Balanced:</strong> Combines keyword precision with AI understanding. Good all-around choice.';
                                } else if (aiWeight <= 80) {
                                    description.innerHTML = '🎯 <strong>AI-Focused (Recommended):</strong> Prioritizes semantic relevance. Best for natural language queries.';
                                } else {
                                    description.innerHTML = '🤖 <strong>Pure AI:</strong> Maximum semantic understanding. Best for complex queries and user intent.';
                                }
                            }
                            
                            document.addEventListener('DOMContentLoaded', function() {
                                updateAIWeightDisplay(<?php echo get_option('hybrid_search_ai_weight', 70); ?>);
                                
                                const enableCheckbox = document.getElementById('ai-reranking-enabled');
                                const aiSettings = document.querySelectorAll('.ai-reranking-setting');
                                
                                function toggleAISettings() {
                                    aiSettings.forEach(setting => {
                                        setting.style.display = enableCheckbox.checked ? 'table-row' : 'none';
                                    });
                                }
                                
                                if (enableCheckbox) {
                                    enableCheckbox.addEventListener('change', toggleAISettings);
                                    toggleAISettings();
                                }
                            });
                            </script>
                        </td>
                    </tr>
                    
                    <tr class="ai-reranking-setting">
                        <th scope="row">
                            AI Reranking Instructions
                            <br>
                            <small style="font-weight: normal; color: #666;">Custom guidance for AI</small>
                        </th>
                        <td>
                            <textarea name="hybrid_search_ai_reranking_instructions" 
                                      rows="8" 
                                      cols="60" 
                                      class="large-text code" 
                                      placeholder="Enter custom instructions to guide how AI reranks results...

Examples:
• Prioritize service pages over blog posts when users search for solutions
• For 'how to' queries, rank actionable step-by-step content highest
• Boost technical documentation for developer-focused queries
• Consider content freshness for time-sensitive topics

Leave empty to use default AI behavior."
                                      style="font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6;"><?php echo esc_textarea(get_option('hybrid_search_ai_reranking_instructions', '')); ?></textarea>
                            
                            <div style="margin-top: 15px; padding: 15px; background: #fff9e6; border-left: 4px solid #f59e0b; border-radius: 4px;">
                                <div style="font-weight: 600; color: #92400e; margin-bottom: 8px;">
                                    💡 How Custom Instructions Work
                                </div>
                                <p style="margin: 5px 0; font-size: 13px; color: #78350f;">
                                    These instructions are sent to the AI with every search to guide result ranking.<br>
                                    <strong>Be specific!</strong> Tell the AI what types of content are most valuable for your users.
                                </p>
                            </div>
                            
                            <p class="description" style="margin-top: 15px;">
                                <strong>💡 Pro Tips:</strong><br>
                                • Be specific about your business priorities (services vs content)<br>
                                • Specify how to handle different query types (how-to, what-is, comparison)<br>
                                • Update based on user behavior from analytics<br>
                                • Test different instructions and monitor click-through rates<br>
                            </p>
                        </td>
                    </tr>
                    
                    <tr class="ai-reranking-setting">
                        <th scope="row">AI Reranking Performance</th>
                        <td>
                            <?php
                            // Get stats safely with default values
                            $ai_stats_option = get_option('hybrid_search_ai_reranking_stats');
                            $ai_stats = [
                                'total_searches' => 0,
                                'avg_response_time' => 0,
                                'total_cost' => 0,
                                'last_updated' => ''
                            ];
                            
                            if (is_array($ai_stats_option)) {
                                $ai_stats = array_merge($ai_stats, $ai_stats_option);
                            }
                            ?>
                            
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                    <div style="font-size: 12px; color: #6b7280; margin-bottom: 5px;">Total AI Searches</div>
                                    <div style="font-size: 24px; font-weight: 600; color: #667eea;">
                                        <?php echo number_format((int) $ai_stats['total_searches']); ?>
                                    </div>
                                </div>
                                
                                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                    <div style="font-size: 12px; color: #6b7280; margin-bottom: 5px;">Avg Response Time</div>
                                    <div style="font-size: 24px; font-weight: 600; color: #10b981;">
                                        <?php echo $ai_stats['avg_response_time'] > 0 ? number_format((float) $ai_stats['avg_response_time'], 2) . 's' : '--'; ?>
                                    </div>
                                </div>
                                
                                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                    <div style="font-size: 12px; color: #6b7280; margin-bottom: 5px;">Estimated Cost</div>
                                    <div style="font-size: 24px; font-weight: 600; color: #f59e0b;">
                                        $<?php echo $ai_stats['total_cost'] > 0 ? number_format((float) $ai_stats['total_cost'], 4) : '0.0000'; ?>
                                    </div>
                                </div>
                            </div>
                            
                            <p class="description" style="margin-top: 15px;">
                                Statistics update automatically. Cost based on Cerebras pricing (~$0.10 per 1M tokens).<br>
                                <em>Last updated: <?php echo !empty($ai_stats['last_updated']) ? esc_html($ai_stats['last_updated']) : 'Never'; ?></em>
                            </p>
                        </td>
                    </tr>
                </table>
                
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }
    
    /**
     * Analytics page
     * 
     * @since 2.0.0
     */
    public function analyticsPage() {
        $analytics_data = $this->analytics_service->getAnalyticsData();
        $ctr_data = $this->ctr_service->getCTRStats();
        
        ?>
        <div class="wrap">
            <h1>Search Analytics</h1>
            
            <div class="analytics-dashboard">
                <!-- Analytics Overview -->
                <div class="analytics-card">
                    <h3>Search Analytics Overview</h3>
                    
                    <div class="analytics-stats">
                        <div class="stat-item">
                            <span class="stat-label">Total Searches:</span>
                            <span class="stat-value"><?php echo esc_html($analytics_data['pagination']['total_count'] ?? 0); ?></span>
                        </div>
                        
                        <div class="stat-item">
                            <span class="stat-label">Recent Searches:</span>
                            <span class="stat-value"><?php echo count($analytics_data['data'] ?? []); ?></span>
                        </div>
                    </div>
                    
                    <!-- Search Results Table -->
                    <div class="analytics-table-container">
                        <table class="analytics-table">
                            <thead>
                                <tr>
                                    <th>Query</th>
                                    <th>Results</th>
                                    <th>Time</th>
                                    <th>Device</th>
                                    <th>Browser</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php if (!empty($analytics_data['data'])): ?>
                                    <?php foreach ($analytics_data['data'] as $search): ?>
                                        <tr>
                                            <td><?php echo esc_html($search['query']); ?></td>
                                            <td><?php echo esc_html($search['result_count']); ?></td>
                                            <td><?php echo esc_html(round($search['time_taken'], 3)); ?>s</td>
                                            <td><?php echo esc_html($search['device_type']); ?></td>
                                            <td><?php echo esc_html($search['browser_name']); ?></td>
                                            <td><?php echo esc_html(date('M j, Y', strtotime($search['timestamp']))); ?></td>
                                        </tr>
                                    <?php endforeach; ?>
                                <?php else: ?>
                                    <tr>
                                        <td colspan="6">No search data available. Perform some searches to see analytics.</td>
                                    </tr>
                                <?php endif; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- CTR Analytics -->
                <div class="analytics-card">
                    <h3>Click-Through Rate Analytics</h3>
                    
                    <?php if (!empty($ctr_data['overall_stats'])): ?>
                        <div class="ctr-overview">
                            <div class="ctr-metric">
                                <span class="ctr-label">Total Impressions:</span>
                                <span class="ctr-value"><?php echo esc_html(array_sum(array_column($ctr_data['overall_stats'], 'position_impressions'))); ?></span>
                            </div>
                            
                            <div class="ctr-metric">
                                <span class="ctr-label">Total Clicks:</span>
                                <span class="ctr-value"><?php echo esc_html(array_sum(array_column($ctr_data['overall_stats'], 'position_clicks'))); ?></span>
                            </div>
                        </div>
                        
                        <table class="analytics-table">
                            <thead>
                                <tr>
                                    <th>Position</th>
                                    <th>Impressions</th>
                                    <th>Clicks</th>
                                    <th>CTR</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($ctr_data['overall_stats'] as $stat): ?>
                                    <tr>
                                        <td><?php echo esc_html($stat['result_position']); ?></td>
                                        <td><?php echo esc_html($stat['position_impressions']); ?></td>
                                        <td><?php echo esc_html($stat['position_clicks']); ?></td>
                                        <td><?php echo esc_html(round($stat['ctr_rate'] * 100, 2)); ?>%</td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    <?php else: ?>
                        <div class="no-data">
                            <p>No CTR data available yet. Perform some searches and click on results to see CTR analytics.</p>
                        </div>
                    <?php endif; ?>
                </div>
                
                <!-- Top Clicked Results -->
                <div class="analytics-card">
                    <h3>Top Clicked Results</h3>
                    
                    <?php if (!empty($ctr_data['top_clicked'])): ?>
                        <table class="analytics-table">
                            <thead>
                                <tr>
                                    <th>Title</th>
                                    <th>Position</th>
                                    <th>Clicks</th>
                                    <th>Avg Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($ctr_data['top_clicked'] as $result): ?>
                                    <tr>
                                        <td><?php echo esc_html($result['result_title']); ?></td>
                                        <td><?php echo esc_html($result['result_position']); ?></td>
                                        <td><?php echo esc_html($result['total_clicks']); ?></td>
                                        <td><?php echo esc_html(round($result['avg_score'], 3)); ?></td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    <?php else: ?>
                        <div class="no-data">
                            <p>No clicked results data available yet.</p>
                        </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>
        
        <style>
        .analytics-dashboard {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .analytics-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            position: relative;
            overflow: hidden;
        }
        
        .analytics-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #10b981, #059669);
        }
        
        .analytics-card h3 {
            position: sticky;
            top: 0;
            z-index: 15;
            background: white;
            margin: -25px -25px 20px -25px;
            padding: 25px 25px 15px 25px;
            border-bottom: 1px solid #e2e8f0;
            color: #1f2937;
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .analytics-card h3::before {
            content: '';
            width: 4px;
            height: 20px;
            background: linear-gradient(90deg, #10b981, #059669);
            border-radius: 2px;
        }
        
        .analytics-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .analytics-table th {
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            border: none;
        }
        
        .analytics-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .analytics-table tbody tr:hover {
            background: #f8fafc;
        }
        
        .analytics-stats {
            display: flex;
            gap: 30px;
            margin-bottom: 20px;
        }
        
        .stat-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .stat-label {
            font-size: 0.875rem;
            color: #6b7280;
            font-weight: 500;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1f2937;
        }
        
        .ctr-overview {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
        }
        
        .ctr-metric {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .ctr-label {
            font-size: 0.875rem;
            color: #166534;
            font-weight: 500;
        }
        
        .ctr-value {
            font-size: 1.25rem;
            font-weight: 700;
            color: #15803d;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #6b7280;
            border: 2px dashed #d1d5db;
            border-radius: 10px;
            background: #f9fafb;
        }
        
        .analytics-table-container {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        
        .analytics-table thead {
            position: sticky;
            top: 60px;
            z-index: 10;
        }
        </style>
        <?php
    }
    
    /**
     * Enqueue admin assets
     * 
     * @since 2.0.0
     */
    public function enqueueAssets($hook) {
        // Only load on our admin pages
        if (strpos($hook, 'hybrid-search') === false) {
            return;
        }
        
        // Enqueue jQuery and jQuery UI for sortable functionality
        wp_enqueue_script('jquery');
        wp_enqueue_script('jquery-ui-core');
        wp_enqueue_script('jquery-ui-sortable');
        
        // Assets are handled inline in the admin pages
        // No external CSS/JS files needed
    }
}
