<?php
/**
 * CTR Repository
 * 
 * Data access layer for Click-Through Rate tracking functionality.
 * Handles all CTR-related database operations with proper validation and sanitization.
 * 
 * @package HybridSearch\Database
 * @since 2.0.0
 */

namespace HybridSearch\Database;

class CTRRepository {
    
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
        $this->table_name = $db->getTableName('ctr');
    }
    
    /**
     * Insert CTR record
     * 
     * @param array $data CTR data
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
            'clicked' => 0,
            'click_timestamp' => null,
        ];
        
        $data = wp_parse_args($data, $defaults);
        
        $result = $wpdb->insert(
            $this->table_name,
            [
                'search_id' => (int) $data['search_id'],
                'result_id' => sanitize_text_field($data['result_id']),
                'result_title' => sanitize_text_field($data['result_title']),
                'result_url' => esc_url_raw($data['result_url']),
                'result_position' => (int) $data['result_position'],
                'result_score' => (float) $data['result_score'],
                'clicked' => (int) $data['clicked'],
                'click_timestamp' => $data['click_timestamp'],
                'session_id' => sanitize_text_field($data['session_id']),
                'user_id' => (int) $data['user_id'],
                'ip_address' => sanitize_text_field($data['ip_address']),
                'user_agent' => sanitize_text_field($data['user_agent']),
                'device_type' => sanitize_text_field($data['device_type']),
                'browser_name' => sanitize_text_field($data['browser_name']),
                'query' => sanitize_text_field($data['query']),
                'timestamp' => $data['timestamp'],
            ],
            [
                '%d', '%s', '%s', '%s', '%d', '%f', '%d', '%s', '%s', '%d', '%s', '%s', '%s', '%s', '%s', '%s'
            ]
        );
        
        return $result ? $wpdb->insert_id : false;
    }
    
    /**
     * Track CTR click
     * 
     * @param array $ctr_data CTR data
     * @return bool Success status
     */
    public function trackClick($ctr_data) {
        try {
            // Validate required fields
            $required_fields = ['result_id', 'result_title', 'result_url', 'result_position', 'query'];
            foreach ($required_fields as $field) {
                if (empty($ctr_data[$field])) {
                    return false;
                }
            }
            
            // Prepare data for insertion
            $data = [
                'search_id' => $ctr_data['search_id'] ?? 0,
                'result_id' => $ctr_data['result_id'],
                'result_title' => $ctr_data['result_title'],
                'result_url' => $ctr_data['result_url'],
                'result_position' => $ctr_data['result_position'],
                'result_score' => $ctr_data['result_score'] ?? 0,
                'clicked' => 1,
                'click_timestamp' => current_time('mysql'),
                'session_id' => $ctr_data['session_id'] ?? $this->generateSessionId(),
                'user_id' => $ctr_data['user_id'] ?? get_current_user_id(),
                'query' => $ctr_data['query'],
            ];
            
            $insert_id = $this->insert($data);
            
            if ($insert_id) {
                error_log('CTR click tracked successfully with ID: ' . $insert_id);
                return true;
            } else {
                error_log('Failed to track CTR click');
                return false;
            }
            
        } catch (\Exception $e) {
            error_log('Exception in CTR tracking: ' . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Get CTR statistics
     * 
     * @param int $days Number of days to analyze
     * @return array CTR statistics
     */
    public function getCTRStats($days = 30) {
        $wpdb = $this->db->getWpdb();
        $date_from = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        // Overall CTR stats
        $overall_stats = $wpdb->get_results($wpdb->prepare(
            "SELECT 
                COUNT(*) as total_impressions,
                SUM(clicked) as total_clicks,
                AVG(clicked) as ctr_rate,
                result_position,
                COUNT(*) as position_impressions,
                SUM(clicked) as position_clicks
             FROM {$this->table_name} 
             WHERE timestamp >= %s
             GROUP BY result_position
             ORDER BY result_position",
            $date_from
        ), ARRAY_A);
        
        // Top clicked results
        $top_clicked = $wpdb->get_results($wpdb->prepare(
            "SELECT 
                result_title,
                result_url,
                result_position,
                COUNT(*) as total_clicks,
                AVG(result_score) as avg_score
             FROM {$this->table_name} 
             WHERE clicked = 1 AND timestamp >= %s
             GROUP BY result_title, result_url
             ORDER BY total_clicks DESC
             LIMIT 10",
            $date_from
        ), ARRAY_A);
        
        return [
            'overall_stats' => $overall_stats,
            'top_clicked' => $top_clicked,
        ];
    }
    
    /**
     * Get debug information
     * 
     * @return array Debug information
     */
    public function getDebugInfo() {
        $wpdb = $this->db->getWpdb();
        
        // Check if table exists
        $table_exists = $this->db->tableExists('ctr');
        
        // Get record count
        $total_records = $table_exists ? $this->db->getTableRowCount('ctr') : 0;
        
        // Get recent records
        $recent_records = [];
        if ($table_exists && $total_records > 0) {
            $recent_records = $wpdb->get_results(
                "SELECT * FROM {$this->table_name} ORDER BY timestamp DESC LIMIT 5",
                ARRAY_A
            );
        }
        
        // Get CTR stats
        $ctr_stats = $table_exists ? $this->getCTRStats(7) : [];
        
        return [
            'table_exists' => $table_exists,
            'total_records' => $total_records,
            'recent_records' => $recent_records,
            'ctr_stats' => $ctr_stats,
            'table_name' => $this->table_name,
        ];
    }
    
    /**
     * Clean old CTR data
     * 
     * @param int $days Days to keep
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
}

