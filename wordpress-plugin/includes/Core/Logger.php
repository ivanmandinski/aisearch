<?php
/**
 * Logger
 * 
 * Centralized logging system for the Hybrid Search plugin.
 * Provides structured logging with different levels and contexts.
 * 
 * @package SCS\HybridSearch\Core
 * @since 2.0.0
 */

namespace HybridSearch\Core;

class Logger {
    
    /**
     * Log levels
     */
    const LEVEL_DEBUG = 'debug';
    const LEVEL_INFO = 'info';
    const LEVEL_WARNING = 'warning';
    const LEVEL_ERROR = 'error';
    const LEVEL_CRITICAL = 'critical';
    
    /**
     * Log contexts
     */
    const CONTEXT_SEARCH = 'search';
    const CONTEXT_ANALYTICS = 'analytics';
    const CONTEXT_CTR = 'ctr';
    const CONTEXT_API = 'api';
    const CONTEXT_SECURITY = 'security';
    const CONTEXT_ADMIN = 'admin';
    const CONTEXT_CACHE = 'cache';
    const CONTEXT_DATABASE = 'database';
    
    /**
     * WordPress database instance
     * 
     * @var \wpdb
     */
    private $wpdb;
    
    /**
     * Log table name
     * 
     * @var string
     */
    private $table_name;
    
    /**
     * Minimum log level (only log messages at this level or higher)
     * 
     * @var string
     */
    private $min_level;
    
    /**
     * Log levels hierarchy
     * 
     * @var array
     */
    private $levels = [
        self::LEVEL_DEBUG => 0,
        self::LEVEL_INFO => 1,
        self::LEVEL_WARNING => 2,
        self::LEVEL_ERROR => 3,
        self::LEVEL_CRITICAL => 4,
    ];
    
    /**
     * Constructor
     * 
     * @since 2.0.0
     */
    public function __construct() {
        global $wpdb;
        $this->wpdb = $wpdb;
        $this->table_name = $wpdb->prefix . 'hybrid_search_logs';
        
        // Set minimum log level based on WordPress debug setting
        $this->min_level = defined('WP_DEBUG') && WP_DEBUG ? self::LEVEL_DEBUG : self::LEVEL_INFO;
    }
    
    /**
     * Log debug message
     * 
     * @param string $message
     * @param array $context
     * @param string $context_type
     * @since 2.0.0
     */
    public function debug($message, $context = [], $context_type = self::CONTEXT_SEARCH) {
        $this->log(self::LEVEL_DEBUG, $message, $context, $context_type);
    }
    
    /**
     * Log info message
     * 
     * @param string $message
     * @param array $context
     * @param string $context_type
     * @since 2.0.0
     */
    public function info($message, $context = [], $context_type = self::CONTEXT_SEARCH) {
        $this->log(self::LEVEL_INFO, $message, $context, $context_type);
    }
    
    /**
     * Log warning message
     * 
     * @param string $message
     * @param array $context
     * @param string $context_type
     * @since 2.0.0
     */
    public function warning($message, $context = [], $context_type = self::CONTEXT_SEARCH) {
        $this->log(self::LEVEL_WARNING, $message, $context, $context_type);
    }
    
    /**
     * Log error message
     * 
     * @param string $message
     * @param array $context
     * @param string $context_type
     * @since 2.0.0
     */
    public function error($message, $context = [], $context_type = self::CONTEXT_SEARCH) {
        $this->log(self::LEVEL_ERROR, $message, $context, $context_type);
    }
    
    /**
     * Log critical message
     * 
     * @param string $message
     * @param array $context
     * @param string $context_type
     * @since 2.0.0
     */
    public function critical($message, $context = [], $context_type = self::CONTEXT_SEARCH) {
        $this->log(self::LEVEL_CRITICAL, $message, $context, $context_type);
    }
    
    /**
     * Main logging method
     * 
     * @param string $level
     * @param string $message
     * @param array $context
     * @param string $context_type
     * @since 2.0.0
     */
    public function log($level, $message, $context = [], $context_type = self::CONTEXT_SEARCH) {
        // Check if we should log this level
        if (!$this->shouldLog($level)) {
            return;
        }
        
        // Prepare log data
        $log_data = [
            'level' => $level,
            'message' => $message,
            'context' => $context,
            'context_type' => $context_type,
            'timestamp' => current_time('mysql'),
            'user_id' => get_current_user_id(),
            'ip_address' => $this->getClientIP(),
            'user_agent' => isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '',
            'request_uri' => isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '',
            'request_method' => isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : '',
        ];
        
        // Log to database
        $this->logToDatabase($log_data);
        
        // Log to WordPress error log for critical/error levels
        if (in_array($level, [self::LEVEL_ERROR, self::LEVEL_CRITICAL])) {
            $this->logToErrorLog($log_data);
        }
        
        // Log to file if WP_DEBUG is enabled
        if (defined('WP_DEBUG') && WP_DEBUG && defined('WP_DEBUG_LOG') && WP_DEBUG_LOG) {
            $this->logToFile($log_data);
        }
    }
    
    /**
     * Check if we should log this level
     * 
     * @param string $level
     * @return bool
     * @since 2.0.0
     */
    private function shouldLog($level) {
        return isset($this->levels[$level]) && 
               $this->levels[$level] >= $this->levels[$this->min_level];
    }
    
    /**
     * Log to database
     * 
     * @param array $log_data
     * @since 2.0.0
     */
    private function logToDatabase($log_data) {
        // Check if table exists, create if not
        if (!$this->tableExists()) {
            $this->createLogTable();
        }
        
        $this->wpdb->insert(
            $this->table_name,
            [
                'level' => $log_data['level'],
                'message' => $log_data['message'],
                'context' => json_encode($log_data['context']),
                'context_type' => $log_data['context_type'],
                'timestamp' => $log_data['timestamp'],
                'user_id' => $log_data['user_id'],
                'ip_address' => $log_data['ip_address'],
                'user_agent' => $log_data['user_agent'],
                'request_uri' => $log_data['request_uri'],
                'request_method' => $log_data['request_method'],
            ],
            [
                '%s', '%s', '%s', '%s', '%s', '%d', '%s', '%s', '%s', '%s'
            ]
        );
    }
    
    /**
     * Log to WordPress error log
     * 
     * @param array $log_data
     * @since 2.0.0
     */
    private function logToErrorLog($log_data) {
        $formatted_message = sprintf(
            '[Hybrid Search %s] %s - Context: %s - IP: %s - User: %d',
            strtoupper($log_data['level']),
            $log_data['message'],
            json_encode($log_data['context']),
            $log_data['ip_address'],
            $log_data['user_id']
        );
        
        error_log($formatted_message);
    }
    
    /**
     * Log to file
     * 
     * @param array $log_data
     * @since 2.0.0
     */
    private function logToFile($log_data) {
        $log_file = WP_CONTENT_DIR . '/hybrid-search-debug.log';
        $formatted_message = sprintf(
            "[%s] %s [%s] %s - %s\n",
            $log_data['timestamp'],
            strtoupper($log_data['level']),
            $log_data['context_type'],
            $log_data['message'],
            json_encode($log_data['context'])
        );
        
        file_put_contents($log_file, $formatted_message, FILE_APPEND | LOCK_EX);
    }
    
    /**
     * Check if log table exists
     * 
     * @return bool
     * @since 2.0.0
     */
    private function tableExists() {
        return $this->wpdb->get_var("SHOW TABLES LIKE '{$this->table_name}'") === $this->table_name;
    }
    
    /**
     * Create log table
     * 
     * @since 2.0.0
     */
    private function createLogTable() {
        $charset_collate = $this->wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE {$this->table_name} (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            level varchar(20) NOT NULL,
            message text NOT NULL,
            context text,
            context_type varchar(50) NOT NULL,
            timestamp datetime NOT NULL,
            user_id int(11),
            ip_address varchar(45),
            user_agent text,
            request_uri text,
            request_method varchar(10),
            PRIMARY KEY (id),
            KEY level_index (level),
            KEY context_type_index (context_type),
            KEY timestamp_index (timestamp),
            KEY user_index (user_id),
            KEY ip_index (ip_address)
        ) $charset_collate;";
        
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql);
    }
    
    /**
     * Get logs with filtering
     * 
     * @param array $args
     * @return array
     * @since 2.0.0
     */
    public function getLogs($args = []) {
        $defaults = [
            'level' => '',
            'context_type' => '',
            'page' => 1,
            'per_page' => 50,
            'date_from' => '',
            'date_to' => '',
            'user_id' => '',
            'search' => '',
        ];
        
        $args = wp_parse_args($args, $defaults);
        
        // Build WHERE clause
        $where_conditions = ['1=1'];
        $where_values = [];
        
        if (!empty($args['level'])) {
            $where_conditions[] = 'level = %s';
            $where_values[] = $args['level'];
        }
        
        if (!empty($args['context_type'])) {
            $where_conditions[] = 'context_type = %s';
            $where_values[] = $args['context_type'];
        }
        
        if (!empty($args['date_from'])) {
            $where_conditions[] = 'timestamp >= %s';
            $where_values[] = $args['date_from'];
        }
        
        if (!empty($args['date_to'])) {
            $where_conditions[] = 'timestamp <= %s';
            $where_values[] = $args['date_to'];
        }
        
        if (!empty($args['user_id'])) {
            $where_conditions[] = 'user_id = %d';
            $where_values[] = (int) $args['user_id'];
        }
        
        if (!empty($args['search'])) {
            $where_conditions[] = 'message LIKE %s';
            $where_values[] = '%' . $this->wpdb->esc_like($args['search']) . '%';
        }
        
        $where_clause = implode(' AND ', $where_conditions);
        
        // Get total count
        $count_sql = "SELECT COUNT(*) FROM {$this->table_name} WHERE $where_clause";
        if (!empty($where_values)) {
            $count_sql = $this->wpdb->prepare($count_sql, $where_values);
        }
        $total_count = (int) $this->wpdb->get_var($count_sql);
        
        // Calculate pagination
        $offset = ($args['page'] - 1) * $args['per_page'];
        $total_pages = ceil($total_count / $args['per_page']);
        
        // Get data
        $sql = "SELECT * FROM {$this->table_name} 
                WHERE $where_clause 
                ORDER BY timestamp DESC 
                LIMIT %d OFFSET %d";
        
        $sql_values = array_merge($where_values, [$args['per_page'], $offset]);
        $sql = $this->wpdb->prepare($sql, $sql_values);
        
        $results = $this->wpdb->get_results($sql, ARRAY_A);
        
        // Decode context JSON
        foreach ($results as &$result) {
            $result['context'] = json_decode($result['context'], true);
        }
        
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
     * Clean old logs
     * 
     * @param int $days
     * @return int Number of records deleted
     * @since 2.0.0
     */
    public function cleanOldLogs($days = 30) {
        $cutoff_date = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        return $this->wpdb->delete(
            $this->table_name,
            ['timestamp' => $cutoff_date],
            ['%s']
        );
    }
    
    /**
     * Get log statistics
     * 
     * @param int $days
     * @return array
     * @since 2.0.0
     */
    public function getLogStats($days = 7) {
        $date_from = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        // Logs by level
        $levels = $this->wpdb->get_results($this->wpdb->prepare(
            "SELECT level, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY level 
             ORDER BY count DESC",
            $date_from
        ), ARRAY_A);
        
        // Logs by context type
        $contexts = $this->wpdb->get_results($this->wpdb->prepare(
            "SELECT context_type, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY context_type 
             ORDER BY count DESC",
            $date_from
        ), ARRAY_A);
        
        // Daily log counts
        $daily = $this->wpdb->get_results($this->wpdb->prepare(
            "SELECT DATE(timestamp) as date, COUNT(*) as count 
             FROM {$this->table_name} 
             WHERE timestamp >= %s 
             GROUP BY DATE(timestamp) 
             ORDER BY date DESC",
            $date_from
        ), ARRAY_A);
        
        return [
            'levels' => $levels,
            'contexts' => $contexts,
            'daily' => $daily,
            'total_logs' => array_sum(array_column($levels, 'count')),
        ];
    }
    
    /**
     * Get client IP address
     * 
     * @return string
     * @since 2.0.0
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
     * Set minimum log level
     * 
     * @param string $level
     * @since 2.0.0
     */
    public function setMinLevel($level) {
        if (isset($this->levels[$level])) {
            $this->min_level = $level;
        }
    }
    
    /**
     * Get current minimum log level
     * 
     * @return string
     * @since 2.0.0
     */
    public function getMinLevel() {
        return $this->min_level;
    }
}
