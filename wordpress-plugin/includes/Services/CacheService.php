<?php
/**
 * Cache Service
 * 
 * Centralized caching system for the Hybrid Search plugin.
 * Provides both WordPress transients and database-based caching.
 * 
 * @package SCS\HybridSearch\Services
 * @since 2.0.0
 */

namespace HybridSearch\Services;

class CacheService {
    
    /**
     * Cache types
     */
    const CACHE_TYPE_TRANSIENT = 'transient';
    const CACHE_TYPE_DATABASE = 'database';
    
    /**
     * Default cache duration (1 hour)
     * 
     * @var int
     */
    private $default_duration = 3600;
    
    /**
     * Cache prefix
     * 
     * @var string
     */
    private $prefix = 'hybrid_search_';
    
    /**
     * Use database cache for large data
     * 
     * @var bool
     */
    private $use_database_cache = true;
    
    /**
     * WordPress database instance
     * 
     * @var \wpdb
     */
    private $wpdb;
    
    /**
     * Cache table name
     * 
     * @var string
     */
    private $cache_table;
    
    /**
     * Constructor
     * 
     * @param array $config Cache configuration
     * @since 2.0.0
     */
    public function __construct($config = []) {
        global $wpdb;
        $this->wpdb = $wpdb;
        $this->cache_table = $wpdb->prefix . 'hybrid_search_cache';
        
        // Apply configuration
        if (isset($config['default_duration'])) {
            $this->default_duration = (int) $config['default_duration'];
        }
        
        if (isset($config['prefix'])) {
            $this->prefix = sanitize_text_field($config['prefix']);
        }
        
        if (isset($config['use_database_cache'])) {
            $this->use_database_cache = (bool) $config['use_database_cache'];
        }
    }
    
    /**
     * Get cached data
     * 
     * @param string $key Cache key
     * @param mixed $default Default value if cache miss
     * @return mixed Cached data or default value
     * @since 2.0.0
     */
    public function get($key, $default = false) {
        $cache_key = $this->prefix . $key;
        
        // Try WordPress transients first (faster)
        $transient_data = get_transient($cache_key);
        if ($transient_data !== false) {
            return $transient_data;
        }
        
        // Try database cache if enabled
        if ($this->use_database_cache) {
            $db_data = $this->getFromDatabase($cache_key);
            if ($db_data !== false) {
                // Store in transient for faster access next time
                set_transient($cache_key, $db_data, $this->default_duration);
                return $db_data;
            }
        }
        
        return $default;
    }
    
    /**
     * Set cached data
     * 
     * @param string $key Cache key
     * @param mixed $data Data to cache
     * @param int $duration Cache duration in seconds
     * @return bool Success status
     * @since 2.0.0
     */
    public function set($key, $data, $duration = null) {
        if ($duration === null) {
            $duration = $this->default_duration;
        }
        
        $cache_key = $this->prefix . $key;
        $expires_at = date('Y-m-d H:i:s', time() + $duration);
        
        // Store in WordPress transients (primary cache)
        $transient_result = set_transient($cache_key, $data, $duration);
        
        // Also store in database cache for persistence
        if ($this->use_database_cache) {
            $db_result = $this->setInDatabase($cache_key, $data, $expires_at);
        } else {
            $db_result = true;
        }
        
        return $transient_result && $db_result;
    }
    
    /**
     * Delete cached data
     * 
     * @param string $key Cache key
     * @return bool Success status
     * @since 2.0.0
     */
    public function delete($key) {
        $cache_key = $this->prefix . $key;
        
        // Delete from WordPress transients
        $transient_result = delete_transient($cache_key);
        
        // Delete from database cache
        if ($this->use_database_cache) {
            $db_result = $this->deleteFromDatabase($cache_key);
        } else {
            $db_result = true;
        }
        
        return $transient_result && $db_result;
    }
    
    /**
     * Delete multiple cache keys matching pattern
     * 
     * @param string $pattern Pattern to match (supports * wildcard)
     * @return int Number of deleted items
     * @since 2.0.0
     */
    public function deletePattern($pattern) {
        $deleted_count = 0;
        
        // Convert pattern to regex
        $regex_pattern = str_replace(['*', '?'], ['.*', '.'], preg_quote($pattern, '/'));
        $regex_pattern = '/^' . $regex_pattern . '$/';
        
        // Delete from database cache
        if ($this->use_database_cache) {
            $db_keys = $this->wpdb->get_col(
                $this->wpdb->prepare(
                    "SELECT cache_key FROM {$this->cache_table} WHERE cache_key LIKE %s",
                    str_replace('*', '%', $pattern)
                )
            );
            
            foreach ($db_keys as $key) {
                if (preg_match($regex_pattern, $key)) {
                    $this->deleteFromDatabase($key);
                    $deleted_count++;
                }
            }
        }
        
        // Note: WordPress transients don't support pattern deletion
        // They will expire naturally or need to be deleted individually
        
        return $deleted_count;
    }
    
    /**
     * Clear all cache
     * 
     * @return bool Success status
     * @since 2.0.0
     */
    public function clear() {
        // Clear all transients with our prefix
        global $wpdb;
        
        $transient_keys = $wpdb->get_col(
            $wpdb->prepare(
                "SELECT option_name FROM {$wpdb->options} 
                 WHERE option_name LIKE %s OR option_name LIKE %s",
                '_transient_' . $this->prefix . '%',
                '_transient_timeout_' . $this->prefix . '%'
            )
        );
        
        foreach ($transient_keys as $key) {
            $transient_name = str_replace(['_transient_', '_transient_timeout_'], '', $key);
            delete_transient($transient_name);
        }
        
        // Clear database cache
        if ($this->use_database_cache) {
            $this->wpdb->query(
                $this->wpdb->prepare(
                    "DELETE FROM {$this->cache_table} WHERE cache_key LIKE %s",
                    $this->prefix . '%'
                )
            );
        }
        
        return true;
    }
    
    /**
     * Get cache statistics
     * 
     * @return array Cache statistics
     * @since 2.0.0
     */
    public function getStats() {
        global $wpdb;
        
        $stats = [
            'transient_count' => 0,
            'transient_size' => 0,
            'database_count' => 0,
            'database_size' => 0,
        ];
        
        // Count transients with our prefix
        $transient_count = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT COUNT(*) FROM {$wpdb->options} 
                 WHERE option_name LIKE %s",
                '_transient_' . $this->prefix . '%'
            )
        );
        $stats['transient_count'] = (int) $transient_count;
        
        // Calculate transient size
        $transient_size = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT SUM(LENGTH(option_value)) FROM {$wpdb->options} 
                 WHERE option_name LIKE %s",
                '_transient_' . $this->prefix . '%'
            )
        );
        $stats['transient_size'] = (int) $transient_size;
        
        // Database cache stats
        if ($this->use_database_cache) {
            $db_count = $wpdb->get_var(
                $wpdb->prepare(
                    "SELECT COUNT(*) FROM {$this->cache_table} 
                     WHERE cache_key LIKE %s",
                    $this->prefix . '%'
                )
            );
            $stats['database_count'] = (int) $db_count;
            
            $db_size = $wpdb->get_var(
                $wpdb->prepare(
                    "SELECT SUM(LENGTH(cache_value)) FROM {$this->cache_table} 
                     WHERE cache_key LIKE %s",
                    $this->prefix . '%'
                )
            );
            $stats['database_size'] = (int) $db_size;
        }
        
        return $stats;
    }
    
    /**
     * Clean expired cache entries
     * 
     * @return int Number of cleaned entries
     * @since 2.0.0
     */
    public function cleanExpired() {
        $cleaned_count = 0;
        
        // Clean expired database cache
        if ($this->use_database_cache) {
            $result = $this->wpdb->delete(
                $this->cache_table,
                [
                    'expires_at' => ['<', current_time('mysql')]
                ],
                ['%s']
            );
            
            if ($result !== false) {
                $cleaned_count += $result;
            }
        }
        
        // Note: WordPress transients are automatically cleaned by WordPress
        
        return $cleaned_count;
    }
    
    /**
     * Get data from database cache
     * 
     * @param string $key Cache key
     * @return mixed|false Cached data or false
     * @since 2.0.0
     */
    private function getFromDatabase($key) {
        $result = $this->wpdb->get_row(
            $this->wpdb->prepare(
                "SELECT cache_value, expires_at FROM {$this->cache_table} 
                 WHERE cache_key = %s AND expires_at > %s",
                $key,
                current_time('mysql')
            )
        );
        
        if ($result) {
            return maybe_unserialize($result->cache_value);
        }
        
        return false;
    }
    
    /**
     * Set data in database cache
     * 
     * @param string $key Cache key
     * @param mixed $data Data to cache
     * @param string $expires_at Expiration timestamp
     * @return bool Success status
     * @since 2.0.0
     */
    private function setInDatabase($key, $data, $expires_at) {
        $serialized_data = maybe_serialize($data);
        
        // Try to update existing entry first
        $updated = $this->wpdb->update(
            $this->cache_table,
            [
                'cache_value' => $serialized_data,
                'expires_at' => $expires_at,
                'created_at' => current_time('mysql'),
            ],
            ['cache_key' => $key],
            ['%s', '%s', '%s'],
            ['%s']
        );
        
        // If no rows were updated, insert new entry
        if ($updated === 0) {
            $inserted = $this->wpdb->insert(
                $this->cache_table,
                [
                    'cache_key' => $key,
                    'cache_value' => $serialized_data,
                    'expires_at' => $expires_at,
                    'created_at' => current_time('mysql'),
                ],
                ['%s', '%s', '%s', '%s']
            );
            
            return $inserted !== false;
        }
        
        return true;
    }
    
    /**
     * Delete data from database cache
     * 
     * @param string $key Cache key
     * @return bool Success status
     * @since 2.0.0
     */
    private function deleteFromDatabase($key) {
        $deleted = $this->wpdb->delete(
            $this->cache_table,
            ['cache_key' => $key],
            ['%s']
        );
        
        return $deleted !== false;
    }
    
    /**
     * Check if cache key exists
     * 
     * @param string $key Cache key
     * @return bool True if exists
     * @since 2.0.0
     */
    public function exists($key) {
        $cache_key = $this->prefix . $key;
        
        // Check transient first
        if (get_transient($cache_key) !== false) {
            return true;
        }
        
        // Check database cache
        if ($this->use_database_cache) {
            $count = $this->wpdb->get_var(
                $this->wpdb->prepare(
                    "SELECT COUNT(*) FROM {$this->cache_table} 
                     WHERE cache_key = %s AND expires_at > %s",
                    $cache_key,
                    current_time('mysql')
                )
            );
            
            return $count > 0;
        }
        
        return false;
    }
    
    /**
     * Get cache TTL (time to live)
     * 
     * @param string $key Cache key
     * @return int|false TTL in seconds or false if not found
     * @since 2.0.0
     */
    public function getTTL($key) {
        $cache_key = $this->prefix . $key;
        
        // Check database cache for TTL
        if ($this->use_database_cache) {
            $result = $this->wpdb->get_row(
                $this->wpdb->prepare(
                    "SELECT expires_at FROM {$this->cache_table} 
                     WHERE cache_key = %s",
                    $cache_key
                )
            );
            
            if ($result) {
                $expires_timestamp = strtotime($result->expires_at);
                $current_timestamp = time();
                
                if ($expires_timestamp > $current_timestamp) {
                    return $expires_timestamp - $current_timestamp;
                }
            }
        }
        
        // Note: WordPress transients don't provide TTL information
        
        return false;
    }
    
    /**
     * Increment numeric cache value
     * 
     * @param string $key Cache key
     * @param int $increment Increment amount
     * @param int $duration Cache duration
     * @return int|false New value or false on failure
     * @since 2.0.0
     */
    public function increment($key, $increment = 1, $duration = null) {
        $current_value = $this->get($key, 0);
        
        if (!is_numeric($current_value)) {
            return false;
        }
        
        $new_value = $current_value + $increment;
        
        if ($this->set($key, $new_value, $duration)) {
            return $new_value;
        }
        
        return false;
    }
    
    /**
     * Decrement numeric cache value
     * 
     * @param string $key Cache key
     * @param int $decrement Decrement amount
     * @param int $duration Cache duration
     * @return int|false New value or false on failure
     * @since 2.0.0
     */
    public function decrement($key, $decrement = 1, $duration = null) {
        return $this->increment($key, -$decrement, $duration);
    }
}
