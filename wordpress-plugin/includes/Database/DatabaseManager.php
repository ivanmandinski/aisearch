<?php
/**
 * Database Manager
 * 
 * @package SCS\HybridSearch\Database
 * @since 2.0.0
 */

namespace HybridSearch\Database;

class DatabaseManager {
    
    /**
     * WordPress database instance
     * 
     * @var \wpdb
     */
    private $wpdb;
    
    /**
     * Table names
     * 
     * @var array
     */
    private $tables = [];
    
    /**
     * Constructor
     */
    public function __construct() {
        global $wpdb;
        $this->wpdb = $wpdb;
        $this->initTableNames();
    }
    
    /**
     * Initialize table names
     */
    private function initTableNames() {
        $prefix = $this->wpdb->prefix;
        $this->tables = [
            'analytics' => $prefix . 'hybrid_search_analytics',
            'ctr' => $prefix . 'hybrid_search_ctr',
            'security_logs' => $prefix . 'hybrid_search_security_logs',
            'cache' => $prefix . 'hybrid_search_cache',
        ];
    }
    
    /**
     * Get table name
     * 
     * @param string $table
     * @return string
     */
    public function getTableName($table) {
        return isset($this->tables[$table]) ? $this->tables[$table] : '';
    }
    
    /**
     * Get WordPress database instance
     * 
     * @return \wpdb
     */
    public function getWpdb() {
        return $this->wpdb;
    }
    
    /**
     * Create all plugin tables
     * 
     * @since 2.0.0
     */
    public function createTables() {
        $this->createAnalyticsTable();
        $this->createCTRTable();
        $this->createSecurityLogsTable();
        $this->createCacheTable();
    }
    
    /**
     * Create analytics table
     */
    private function createAnalyticsTable() {
        $table_name = $this->getTableName('analytics');
        $charset_collate = $this->wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            query varchar(255) NOT NULL,
            result_count int(11) NOT NULL DEFAULT 0,
            time_taken decimal(10,3) DEFAULT NULL,
            has_results tinyint(1) NOT NULL DEFAULT 0,
            user_agent text,
            language varchar(10),
            screen_resolution varchar(20),
            viewport_size varchar(20),
            referrer text,
            session_id varchar(100),
            user_id varchar(100),
            device_type varchar(20),
            browser_name varchar(50),
            browser_version varchar(20),
            search_method varchar(50),
            filters text,
            sort_method varchar(50),
            timestamp datetime NOT NULL,
            ip_address varchar(45),
            PRIMARY KEY (id),
            KEY query_index (query),
            KEY timestamp_index (timestamp),
            KEY session_index (session_id),
            KEY user_index (user_id),
            KEY device_index (device_type),
            KEY browser_index (browser_name),
            KEY ip_index (ip_address)
        ) $charset_collate;";
        
        $this->executeTableCreation($sql);
    }
    
    /**
     * Create CTR table
     */
    private function createCTRTable() {
        $table_name = $this->getTableName('ctr');
        $charset_collate = $this->wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            search_id mediumint(9) NOT NULL,
            result_id varchar(255) NOT NULL,
            result_title text NOT NULL,
            result_url text NOT NULL,
            result_position int(11) NOT NULL,
            result_score decimal(10,3),
            clicked tinyint(1) NOT NULL DEFAULT 0,
            click_timestamp datetime,
            session_id varchar(100),
            user_id varchar(100),
            ip_address varchar(45),
            user_agent text,
            device_type varchar(20),
            browser_name varchar(50),
            query varchar(255) NOT NULL,
            timestamp datetime NOT NULL,
            PRIMARY KEY (id),
            KEY search_id_index (search_id),
            KEY result_id_index (result_id),
            KEY clicked_index (clicked),
            KEY query_index (query),
            KEY timestamp_index (timestamp),
            KEY session_index (session_id),
            KEY user_index (user_id),
            KEY position_index (result_position)
        ) $charset_collate;";
        
        $this->executeTableCreation($sql);
    }
    
    /**
     * Create security logs table
     */
    private function createSecurityLogsTable() {
        $table_name = $this->getTableName('security_logs');
        $charset_collate = $this->wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            event varchar(100) NOT NULL,
            ip_address varchar(45) NOT NULL,
            user_agent text,
            user_id int(11),
            data text,
            timestamp datetime NOT NULL,
            PRIMARY KEY (id),
            KEY event_index (event),
            KEY ip_index (ip_address),
            KEY timestamp_index (timestamp),
            KEY user_index (user_id)
        ) $charset_collate;";
        
        $this->executeTableCreation($sql);
    }
    
    /**
     * Create cache table
     */
    private function createCacheTable() {
        $table_name = $this->getTableName('cache');
        $charset_collate = $this->wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            cache_key varchar(255) NOT NULL,
            cache_value longtext NOT NULL,
            expires_at datetime NOT NULL,
            created_at datetime NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY cache_key_unique (cache_key),
            KEY expires_index (expires_at)
        ) $charset_collate;";
        
        $this->executeTableCreation($sql);
    }
    
    /**
     * Execute table creation
     * 
     * @param string $sql
     */
    private function executeTableCreation($sql) {
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql);
    }
    
    /**
     * Check if table exists
     * 
     * @param string $table
     * @return bool
     */
    public function tableExists($table) {
        $table_name = $this->getTableName($table);
        if (empty($table_name)) {
            return false;
        }
        
        return $this->wpdb->get_var("SHOW TABLES LIKE '$table_name'") === $table_name;
    }
    
    /**
     * Get table row count
     * 
     * @param string $table
     * @return int
     */
    public function getTableRowCount($table) {
        $table_name = $this->getTableName($table);
        if (empty($table_name) || !$this->tableExists($table)) {
            return 0;
        }
        
        return (int) $this->wpdb->get_var("SELECT COUNT(*) FROM $table_name");
    }
    
    /**
     * Clean old records
     * 
     * @param string $table
     * @param int $days
     */
    public function cleanOldRecords($table, $days = 30) {
        $table_name = $this->getTableName($table);
        if (empty($table_name) || !$this->tableExists($table)) {
            return;
        }
        
        $cutoff_date = date('Y-m-d H:i:s', strtotime("-{$days} days"));
        
        switch ($table) {
            case 'analytics':
                $this->wpdb->delete($table_name, ['timestamp' => $cutoff_date], ['%s']);
                break;
            case 'ctr':
                $this->wpdb->delete($table_name, ['timestamp' => $cutoff_date], ['%s']);
                break;
            case 'security_logs':
                $this->wpdb->delete($table_name, ['timestamp' => $cutoff_date], ['%s']);
                break;
            case 'cache':
                $this->wpdb->delete($table_name, ['expires_at' => $cutoff_date], ['%s']);
                break;
        }
    }
    
    /**
     * Optimize tables
     */
    public function optimizeTables() {
        foreach ($this->tables as $table => $table_name) {
            if ($this->tableExists($table)) {
                $this->wpdb->query("OPTIMIZE TABLE $table_name");
            }
        }
    }
    
    /**
     * Get database statistics
     * 
     * @return array
     */
    public function getDatabaseStats() {
        $stats = [];
        
        foreach ($this->tables as $table => $table_name) {
            if ($this->tableExists($table)) {
                $stats[$table] = [
                    'exists' => true,
                    'row_count' => $this->getTableRowCount($table),
                    'table_size' => $this->getTableSize($table_name),
                ];
            } else {
                $stats[$table] = [
                    'exists' => false,
                    'row_count' => 0,
                    'table_size' => 0,
                ];
            }
        }
        
        return $stats;
    }
    
    /**
     * Get table size
     * 
     * @param string $table_name
     * @return string
     */
    private function getTableSize($table_name) {
        $result = $this->wpdb->get_row(
            $this->wpdb->prepare(
                "SELECT ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb 
                 FROM information_schema.tables 
                 WHERE table_schema = %s AND table_name = %s",
                DB_NAME,
                $table_name
            )
        );
        
        return $result ? $result->size_mb . ' MB' : '0 MB';
    }
    
    /**
     * Create database indexes for performance
     */
    public function createIndexes() {
        // Analytics table indexes
        $analytics_table = $this->getTableName('analytics');
        if ($this->tableExists('analytics')) {
            $this->wpdb->query("CREATE INDEX IF NOT EXISTS idx_analytics_query_timestamp ON $analytics_table (query, timestamp)");
            $this->wpdb->query("CREATE INDEX IF NOT EXISTS idx_analytics_session_timestamp ON $analytics_table (session_id, timestamp)");
        }
        
        // CTR table indexes
        $ctr_table = $this->getTableName('ctr');
        if ($this->tableExists('ctr')) {
            $this->wpdb->query("CREATE INDEX IF NOT EXISTS idx_ctr_search_clicked ON $ctr_table (search_id, clicked)");
            $this->wpdb->query("CREATE INDEX IF NOT EXISTS idx_ctr_query_position ON $ctr_table (query, result_position)");
        }
    }
}
