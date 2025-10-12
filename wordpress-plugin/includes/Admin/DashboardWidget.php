<?php
/**
 * Performance Dashboard Widget
 * 
 * Displays search metrics, performance stats, and insights
 * 
 * @package HybridSearch\Admin
 * @since 2.7.0
 */

namespace HybridSearch\Admin;

class DashboardWidget {
    
    /**
     * Constructor
     */
    public function __construct() {
        // Register dashboard widget
        add_action('wp_dashboard_setup', [$this, 'registerWidget']);
        
        // AJAX handlers for dashboard
        add_action('wp_ajax_hybrid_search_dashboard_stats', [$this, 'ajaxGetStats']);
        add_action('wp_ajax_hybrid_search_dashboard_refresh', [$this, 'ajaxRefreshCache']);
    }
    
    /**
     * Register dashboard widget
     */
    public function registerWidget() {
        wp_add_dashboard_widget(
            'hybrid_search_performance',
            'Hybrid Search Performance',
            [$this, 'renderWidget'],
            null,
            null,
            'normal',
            'high'
        );
    }
    
    /**
     * Render dashboard widget
     */
    public function renderWidget() {
        $stats = $this->getPerformanceStats(30); // Last 30 days
        
        ?>
        <div class="hybrid-search-dashboard">
            <style>
                .hybrid-search-dashboard {
                    padding: 10px 0;
                }
                .hs-stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }
                .hs-stat-card {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 4px;
                    border-left: 4px solid #0073aa;
                }
                .hs-stat-card.warning {
                    border-left-color: #f0ad4e;
                }
                .hs-stat-card.danger {
                    border-left-color: #d9534f;
                }
                .hs-stat-card.success {
                    border-left-color: #5cb85c;
                }
                .hs-stat-value {
                    font-size: 24px;
                    font-weight: bold;
                    margin: 5px 0;
                }
                .hs-stat-label {
                    font-size: 12px;
                    color: #666;
                    text-transform: uppercase;
                }
                .hs-stat-subtitle {
                    font-size: 11px;
                    color: #999;
                    margin-top: 5px;
                }
                .hs-chart-container {
                    margin: 20px 0;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }
                .hs-list {
                    list-style: none;
                    margin: 0;
                    padding: 0;
                }
                .hs-list-item {
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                }
                .hs-list-item:last-child {
                    border-bottom: none;
                }
                .hs-refresh-btn {
                    margin-top: 15px;
                }
            </style>
            
            <!-- Stats Grid -->
            <div class="hs-stats-grid">
                <div class="hs-stat-card success">
                    <div class="hs-stat-label">Total Searches</div>
                    <div class="hs-stat-value"><?php echo number_format($stats['total_searches']); ?></div>
                    <div class="hs-stat-subtitle">Last 30 days</div>
                </div>
                
                <div class="hs-stat-card">
                    <div class="hs-stat-label">Avg Response Time</div>
                    <div class="hs-stat-value"><?php echo round($stats['avg_response_time'], 2); ?>s</div>
                    <div class="hs-stat-subtitle">
                        <?php echo $stats['avg_response_time'] < 2 ? '✅ Good' : '⚠️ Slow'; ?>
                    </div>
                </div>
                
                <div class="hs-stat-card success">
                    <div class="hs-stat-label">Cache Hit Rate</div>
                    <div class="hs-stat-value"><?php echo round($stats['cache_hit_rate'], 1); ?>%</div>
                    <div class="hs-stat-subtitle">
                        Saves <?php echo number_format($stats['cache_hits']); ?> API calls
                    </div>
                </div>
                
                <div class="hs-stat-card">
                    <div class="hs-stat-label">AI Reranking Cost</div>
                    <div class="hs-stat-value">$<?php echo number_format($stats['ai_cost'], 4); ?></div>
                    <div class="hs-stat-subtitle">
                        <?php echo number_format($stats['ai_searches']); ?> AI searches
                    </div>
                </div>
                
                <?php if ($stats['zero_result_rate'] > 10): ?>
                <div class="hs-stat-card warning">
                    <div class="hs-stat-label">Zero Results</div>
                    <div class="hs-stat-value"><?php echo round($stats['zero_result_rate'], 1); ?>%</div>
                    <div class="hs-stat-subtitle">⚠️ Needs attention</div>
                </div>
                <?php endif; ?>
            </div>
            
            <!-- Top Queries -->
            <div class="hs-chart-container">
                <h4 style="margin-top: 0;">🔥 Top Search Queries</h4>
                <?php if (!empty($stats['top_queries'])): ?>
                    <ul class="hs-list">
                        <?php foreach (array_slice($stats['top_queries'], 0, 5) as $query): ?>
                            <li class="hs-list-item">
                                <span><?php echo esc_html($query['query']); ?></span>
                                <span><strong><?php echo number_format($query['count']); ?></strong> searches</span>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                <?php else: ?>
                    <p style="color: #999;">No search data yet</p>
                <?php endif; ?>
            </div>
            
            <!-- Zero Result Queries -->
            <?php if (!empty($stats['zero_result_queries'])): ?>
            <div class="hs-chart-container">
                <h4 style="margin-top: 0;">⚠️ Queries with Zero Results</h4>
                <p style="font-size: 12px; color: #666;">These queries returned no results - consider adding content for these topics</p>
                <ul class="hs-list">
                    <?php foreach (array_slice($stats['zero_result_queries'], 0, 5) as $query): ?>
                        <li class="hs-list-item">
                            <span><?php echo esc_html($query['query']); ?></span>
                            <span><?php echo number_format($query['count']); ?> times</span>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </div>
            <?php endif; ?>
            
            <button class="button button-secondary hs-refresh-btn" onclick="hybridSearchRefreshDashboard(this)">
                🔄 Refresh Stats
            </button>
            
            <script>
            function hybridSearchRefreshDashboard(btn) {
                btn.disabled = true;
                btn.textContent = '⏳ Refreshing...';
                
                jQuery.post(ajaxurl, {
                    action: 'hybrid_search_dashboard_refresh',
                    nonce: '<?php echo wp_create_nonce('hybrid_search_dashboard'); ?>'
                }, function(response) {
                    if (response.success) {
                        location.reload();
                    } else {
                        alert('Failed to refresh: ' + (response.data || 'Unknown error'));
                        btn.disabled = false;
                        btn.textContent = '🔄 Refresh Stats';
                    }
                });
            }
            </script>
        </div>
        <?php
    }
    
    /**
     * Get performance statistics
     *
     * @param int $days Number of days to look back
     * @return array Statistics
     */
    private function getPerformanceStats($days = 30) {
        global $wpdb;
        
        $cache_key = 'hybrid_search_dashboard_stats_' . $days;
        $stats = get_transient($cache_key);
        
        if ($stats !== false) {
            return $stats;
        }
        
        $table_analytics = $wpdb->prefix . 'hybrid_search_analytics';
        $date_from = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        // Total searches
        $total_searches = (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$table_analytics} WHERE created_at >= %s",
            $date_from
        ));
        
        // Average response time
        $avg_response_time = (float) $wpdb->get_var($wpdb->prepare(
            "SELECT AVG(response_time) FROM {$table_analytics} WHERE created_at >= %s",
            $date_from
        ));
        
        // Cache stats
        $cache_hits = (int) get_option('hybrid_search_cache_hits', 0);
        $cache_misses = (int) get_option('hybrid_search_cache_misses', 0);
        $cache_total = $cache_hits + $cache_misses;
        $cache_hit_rate = $cache_total > 0 ? ($cache_hits / $cache_total) * 100 : 0;
        
        // AI reranking stats
        $ai_stats = get_option('hybrid_search_ai_reranking_stats', [
            'total_searches' => 0,
            'total_cost' => 0
        ]);
        
        // Zero results
        $zero_result_count = (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$table_analytics} WHERE result_count = 0 AND created_at >= %s",
            $date_from
        ));
        $zero_result_rate = $total_searches > 0 ? ($zero_result_count / $total_searches) * 100 : 0;
        
        // Top queries
        $top_queries = $wpdb->get_results($wpdb->prepare(
            "SELECT query, COUNT(*) as count 
             FROM {$table_analytics} 
             WHERE created_at >= %s 
             GROUP BY query 
             ORDER BY count DESC 
             LIMIT 10",
            $date_from
        ), ARRAY_A);
        
        // Zero result queries
        $zero_result_queries = $wpdb->get_results($wpdb->prepare(
            "SELECT query, COUNT(*) as count 
             FROM {$table_analytics} 
             WHERE result_count = 0 AND created_at >= %s 
             GROUP BY query 
             ORDER BY count DESC 
             LIMIT 10",
            $date_from
        ), ARRAY_A);
        
        $stats = [
            'total_searches' => $total_searches,
            'avg_response_time' => $avg_response_time ?: 0,
            'cache_hits' => $cache_hits,
            'cache_misses' => $cache_misses,
            'cache_hit_rate' => $cache_hit_rate,
            'ai_searches' => $ai_stats['total_searches'] ?? 0,
            'ai_cost' => $ai_stats['total_cost'] ?? 0,
            'zero_result_count' => $zero_result_count,
            'zero_result_rate' => $zero_result_rate,
            'top_queries' => $top_queries ?: [],
            'zero_result_queries' => $zero_result_queries ?: []
        ];
        
        // Cache for 5 minutes
        set_transient($cache_key, $stats, 300);
        
        return $stats;
    }
    
    /**
     * AJAX: Get stats
     */
    public function ajaxGetStats() {
        check_ajax_referer('hybrid_search_dashboard', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Unauthorized');
            return;
        }
        
        $days = isset($_POST['days']) ? (int) $_POST['days'] : 30;
        $stats = $this->getPerformanceStats($days);
        
        wp_send_json_success($stats);
    }
    
    /**
     * AJAX: Refresh cache
     */
    public function ajaxRefreshCache() {
        check_ajax_referer('hybrid_search_dashboard', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Unauthorized');
            return;
        }
        
        // Clear cache
        delete_transient('hybrid_search_dashboard_stats_30');
        delete_transient('hybrid_search_dashboard_stats_7');
        
        wp_send_json_success('Cache cleared');
    }
}

