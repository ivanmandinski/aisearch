<?php
/**
 * Analytics Repository
 * 
 * @package SCS\HybridSearch\Database
 * @since 2.0.0
 */

namespace HybridSearch\Database;

class AnalyticsRepository {
    
    /**
     * Database manager
     * 
     * @var DatabaseManager
     */
    private $db;
    
    /**
     * Table name
     * 
     * @var string
     */
    private $table_name;
    
    /**
     * Constructor
     * 
     * @param DatabaseManager $db
     */
    public function __construct(DatabaseManager $db) {
        $this->db = $db;
        $this->table_name = $db->getTableName('analytics');
    }
    
    /**
     * Insert analytics record
     * 
     * @param array $data
     * @return int|false Insert ID or false on failure
     */
    public function insert($data) {
        $wpdb = $this->db->getWpdb();
        
        $defaults = [
            'timestamp' => current_time('mysql'),
            'ip_address' => $this->getClientIP(),
            'user_agent' => isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '',
            'session_id' => $this->generateSessionId(),
            'user_id' => get_current_user_id(),
            'device_type' => $this->detectDeviceType(),
            'browser_name' => $this->detectBrowser(),
            'browser_version' => '',
            'language' => $this->detectLanguage(),
            'screen_resolution' => $this->detectScreenResolution(),
            'viewport_size' => $this->detectViewportSize(),
            'referrer' => isset($_SERVER['HTTP_REFERER']) ? $_SERVER['HTTP_REFERER'] : '',
            'search_method' => 'ajax',
            'filters' => '',
            'sort_method' => 'relevance',
        ];
        
        $data = wp_parse_args($data, $defaults);
        
        $result = $wpdb->insert(
            $this->table_name,
            [
                'query' => $data['query'],
                'result_count' => (int) $data['result_count'],
                'time_taken' => (float) $data['time_taken'],
                'has_results' => (bool) $data['has_results'],
                'user_agent' => $data['user_agent'],
                'language' => $data['language'],
                'screen_resolution' => $data['screen_resolution'],
                'viewport_size' => $data['viewport_size'],
                'referrer' => $data['referrer'],
                'session_id' => $data['session_id'],
                'user_id' => $data['user_id'],
                'device_type' => $data['device_type'],
                'browser_name' => $data['browser_name'],
                'browser_version' => $data['browser_version'],
                'search_method' => $data['search_method'],
                'filters' => $data['filters'],
                'sort_method' => $data['sort_method'],
                'timestamp' => $data['timestamp'],
                'ip_address' => $data['ip_address'],
            ],
            [
                '%s', '%d', '%f', '%d', '%s', '%s', '%s', '%s', '%s', '%s', '%d', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'
            ]
        );
        
        return $result ? $wpdb->insert_id : false;
    }
    
    /**
     * Get analytics data with pagination
     * 
     * @param array $args
     * @return array
     */
    public function getAnalyticsData($args = []) {
        $wpdb = $this->db->getWpdb();
        
        $defaults = [
            'page' => 1,
            'per_page' => 50,
            'order_by' => 'timestamp',
            'order' => 'DESC',
            'search' => '',
            'date_from' => '',
            'date_to' => '',
            'device_type' => '',
            'browser_name' => '',
        ];
        
        $args = wp_parse_args($args, $defaults);
        
        // Build WHERE clause
        $where_conditions = ['1=1'];
        $where_values = [];
        
        if (!empty($args['search'])) {
            $where_conditions[] = 'query LIKE %s';
            $where_values[] = '%' . $wpdb->esc_like($args['search']) . '%';
        }
        
        if (!empty($args['date_from'])) {
            $where_conditions[] = 'timestamp >= %s';
            $where_values[] = $args['date_from'];
        }
        
        if (!empty($args['date_to'])) {
            $where_conditions[] = 'timestamp <= %s';
            $where_values[] = $args['date_to'];
        }
        
        if (!empty($args['device_type'])) {
            $where_conditions[] = 'device_type = %s';
            $where_values[] = $args['device_type'];
        }
        
        if (!empty($args['browser_name'])) {
            $where_conditions[] = 'browser_name = %s';
            $where_values[] = $args['browser_name'];
        }
        
        $where_clause = implode(' AND ', $where_conditions);
        
        // Get total count
        $count_sql = "SELECT COUNT(*) FROM {$this->table_name} WHERE $where_clause";
        if (!empty($where_values)) {
            $count_sql = $wpdb->prepare($count_sql, $where_values);
        }
        $total_count = (int) $wpdb->get_var($count_sql);
        
        // Calculate pagination
        $offset = ($args['page'] - 1) * $args['per_page'];
        $total_pages = ceil($total_count / $args['per_page']);
        
        // Get data
        $sql = "SELECT * FROM {$this->table_name} 
                WHERE $where_clause 
                ORDER BY {$args['order_by']} {$args['order']} 
                LIMIT %d OFFSET %d";
        
        $sql_values = array_merge($where_values, [$args['per_page'], $offset]);
        $sql = $wpdb->prepare($sql, $sql_values);
        
        $results = $wpdb->get_results($sql, ARRAY_A);
        
        return [
            'data' => $results,
            'pagination' => [
                'current_page' => $args['page'],
                'per_page' => $args['per_page'],
                'total_count' => $total_count,
                'total_pages' => $total_pages,
                'has_next' => $args['page'] < $total_pages,
                'has_prev' => $args['page'] > 1,
            ]
        ];
    }
    
    /**
     * Get search statistics
     * 
     * @param int $days
     * @return array
     */
    public function getSearchStats($days = 30) {
        $wpdb = $this->db->getWpdb();
        $date_from = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        // Total searches
        $total_searches = $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$this->table_name} WHERE timestamp >= %s",
            $date_from
        ));
        
        // Searches with results
        $searches_with_results = $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$this->table_name} WHERE timestamp >= %s AND has_results = 1",
            $date_from
        ));
        
        // Zero result searches
        $zero_result_searches = $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$this->table_name} WHERE timestamp >= %s AND has_results = 0",
            $date_from
        ));
        
        // Average time taken
        $avg_time = $wpdb->get_var($wpdb->prepare(
            "SELECT AVG(time_taken) FROM {$this->table_name} WHERE timestamp >= %s AND time_taken > 0",
            $date_from
        ));
        
        // Popular queries
        $popular_queries = $wpdb->get_results($wpdb->prepare(
            "SELECT query, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY query 
             ORDER BY count DESC 
             LIMIT 10",
            $date_from
        ), ARRAY_A);
        
        // Zero result queries
        $zero_result_queries = $wpdb->get_results($wpdb->prepare(
            "SELECT query, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s AND has_results = 0 
             GROUP BY query 
             ORDER BY count DESC 
             LIMIT 10",
            $date_from
        ), ARRAY_A);
        
        // Device statistics
        $device_stats = $wpdb->get_results($wpdb->prepare(
            "SELECT device_type, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY device_type 
             ORDER BY count DESC",
            $date_from
        ), ARRAY_A);
        
        // Browser statistics
        $browser_stats = $wpdb->get_results($wpdb->prepare(
            "SELECT browser_name, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY browser_name 
             ORDER BY count DESC",
            $date_from
        ), ARRAY_A);
        
        // Daily statistics
        $daily_stats = $wpdb->get_results($wpdb->prepare(
            "SELECT DATE(timestamp) as date, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY DATE(timestamp) 
             ORDER BY date DESC",
            $date_from
        ), ARRAY_A);
        
        return [
            'total_searches' => (int) $total_searches,
            'searches_with_results' => (int) $searches_with_results,
            'zero_result_searches' => (int) $zero_result_searches,
            'avg_time_taken' => (float) $avg_time,
            'popular_queries' => $popular_queries,
            'zero_result_queries' => $zero_result_queries,
            'device_stats' => $device_stats,
            'browser_stats' => $browser_stats,
            'daily_stats' => $daily_stats,
        ];
    }
    
    /**
     * Get recent searches
     * 
     * @param int $limit
     * @return array
     */
    public function getRecentSearches($limit = 10) {
        $wpdb = $this->db->getWpdb();
        
        return $wpdb->get_results($wpdb->prepare(
            "SELECT * FROM {$this->table_name} 
             ORDER BY timestamp DESC 
             LIMIT %d",
            $limit
        ), ARRAY_A);
    }
    
    /**
     * Check if search should be stored (deduplication)
     * 
     * @param string $query
     * @param string $session_id
     * @return bool
     */
    public function shouldStoreSearch($query, $session_id) {
        $wpdb = $this->db->getWpdb();
        
        // Check for exact duplicates within 30 seconds
        $recent_exact = $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$this->table_name} 
             WHERE query = %s AND session_id = %s AND timestamp > DATE_SUB(NOW(), INTERVAL 30 SECOND)",
            $query,
            $session_id
        ));
        
        if ($recent_exact > 0) {
            return false;
        }
        
        // Check for similar partial queries within 60 seconds
        $recent_partial = $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$this->table_name} 
             WHERE session_id = %s AND timestamp > DATE_SUB(NOW(), INTERVAL 60 SECOND)
             AND (query LIKE %s OR query LIKE %s)",
            $session_id,
            '%' . $wpdb->esc_like($query) . '%',
            '%' . $wpdb->esc_like(substr($query, 0, -1)) . '%'
        ));
        
        return $recent_partial === 0;
    }
    
    /**
     * Clean old analytics data
     * 
     * @param int $days
     * @return int Number of records deleted
     */
    public function cleanOldData($days = 90) {
        $wpdb = $this->db->getWpdb();
        $cutoff_date = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        return $wpdb->delete(
            $this->table_name,
            ['timestamp' => $cutoff_date],
            ['%s']
        );
    }
    
    /**
     * Generate session ID
     * 
     * @return string
     */
    private function generateSessionId() {
        return 'session_' . time() . '_' . wp_generate_password(8, false);
    }
    
    /**
     * Get client IP address
     * 
     * @return string
     */
    private function getClientIP() {
        $ip_keys = ['HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED', 'HTTP_X_CLUSTER_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED', 'REMOTE_ADDR'];
        
        foreach ($ip_keys as $key) {
            if (array_key_exists($key, $_SERVER) === true) {
                foreach (explode(',', $_SERVER[$key]) as $ip) {
                    $ip = trim($ip);
                    if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) !== false) {
                        return $ip;
                    }
                }
            }
        }
        
        return isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '0.0.0.0';
    }
    
    /**
     * Detect device type
     * 
     * @return string
     */
    private function detectDeviceType() {
        $user_agent = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '';
        
        if (preg_match('/Mobile|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i', $user_agent)) {
            return 'mobile';
        } elseif (preg_match('/Tablet|iPad/i', $user_agent)) {
            return 'tablet';
        } else {
            return 'desktop';
        }
    }
    
    /**
     * Detect browser
     * 
     * @return string
     */
    private function detectBrowser() {
        $user_agent = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '';
        
        if (strpos($user_agent, 'Chrome') !== false) {
            return 'Chrome';
        } elseif (strpos($user_agent, 'Firefox') !== false) {
            return 'Firefox';
        } elseif (strpos($user_agent, 'Safari') !== false) {
            return 'Safari';
        } elseif (strpos($user_agent, 'Edge') !== false) {
            return 'Edge';
        } elseif (strpos($user_agent, 'Opera') !== false) {
            return 'Opera';
        } else {
            return 'Unknown';
        }
    }
    
    /**
     * Detect language
     * 
     * @return string
     */
    private function detectLanguage() {
        return isset($_SERVER['HTTP_ACCEPT_LANGUAGE']) ? substr($_SERVER['HTTP_ACCEPT_LANGUAGE'], 0, 2) : 'en';
    }
    
    /**
     * Detect screen resolution (from JavaScript)
     * 
     * @return string
     */
    private function detectScreenResolution() {
        return isset($_POST['screen_resolution']) ? sanitize_text_field($_POST['screen_resolution']) : '';
    }
    
    /**
     * Detect viewport size (from JavaScript)
     * 
     * @return string
     */
    private function detectViewportSize() {
        return isset($_POST['viewport_size']) ? sanitize_text_field($_POST['viewport_size']) : '';
    }
}
