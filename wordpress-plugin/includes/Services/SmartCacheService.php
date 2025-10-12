<?php
/**
 * Smart Cache Service
 * 
 * Intelligent caching with variable TTL based on query characteristics
 * 
 * @package HybridSearch\Services
 * @since 2.7.0
 */

namespace HybridSearch\Services;

class SmartCacheService {
    
    /**
     * Cache key prefix
     */
    const CACHE_PREFIX = 'hybrid_search_';
    
    /**
     * Default cache durations (in seconds)
     */
    const TTL_SHORT = 60;           // 1 minute - trending queries
    const TTL_MEDIUM = 300;          // 5 minutes - regular queries
    const TTL_LONG = 3600;           // 1 hour - stable queries
    const TTL_PERMANENT = 86400;     // 24 hours - evergreen content
    
    /**
     * Popular queries cache (longer duration)
     */
    private $popular_queries = [];
    
    /**
     * Constructor
     */
    public function __construct() {
        $this->loadPopularQueries();
    }
    
    /**
     * Get cache duration based on query characteristics
     * 
     * @param string $query Search query
     * @param array $metadata Search metadata
     * @return int Cache duration in seconds
     */
    public function getCacheDuration($query, $metadata = []) {
        $query_lower = strtolower(trim($query));
        
        // 1. Popular queries - cache longer
        if ($this->isPopularQuery($query_lower)) {
            error_log("Hybrid Search Cache: Popular query '{$query}' - using LONG cache (1 hour)");
            return self::TTL_LONG;
        }
        
        // 2. Time-sensitive queries - cache shorter
        if ($this->isTimeSensitive($query_lower)) {
            error_log("Hybrid Search Cache: Time-sensitive query '{$query}' - using SHORT cache (1 minute)");
            return self::TTL_SHORT;
        }
        
        // 3. Navigational queries - cache longer (unlikely to change)
        if ($this->isNavigational($query_lower)) {
            error_log("Hybrid Search Cache: Navigational query '{$query}' - using PERMANENT cache (24 hours)");
            return self::TTL_PERMANENT;
        }
        
        // 4. High result count - cache longer (stable)
        $result_count = $metadata['total_results'] ?? 0;
        if ($result_count >= 10) {
            error_log("Hybrid Search Cache: High result count ({$result_count}) - using LONG cache (1 hour)");
            return self::TTL_LONG;
        }
        
        // 5. Zero results - cache shorter (might be content gap)
        if ($result_count === 0) {
            error_log("Hybrid Search Cache: Zero results - using SHORT cache (1 minute)");
            return self::TTL_SHORT;
        }
        
        // 6. Default - medium cache
        error_log("Hybrid Search Cache: Regular query '{$query}' - using MEDIUM cache (5 minutes)");
        return self::TTL_MEDIUM;
    }
    
    /**
     * Get cached result
     * 
     * @param string $query Search query
     * @param array $options Search options
     * @return array|false Cached result or false
     */
    public function get($query, $options = []) {
        $cache_key = $this->generateCacheKey($query, $options);
        $cached = get_transient($cache_key);
        
        if ($cached !== false) {
            error_log("Hybrid Search Cache: ✅ HIT for '{$query}'");
            
            // Update cache stats
            $hits = get_option('hybrid_search_cache_hits', 0);
            update_option('hybrid_search_cache_hits', $hits + 1, false);
            
            return $cached;
        }
        
        error_log("Hybrid Search Cache: ❌ MISS for '{$query}'");
        
        // Update cache stats
        $misses = get_option('hybrid_search_cache_misses', 0);
        update_option('hybrid_search_cache_misses', $misses + 1, false);
        
        return false;
    }
    
    /**
     * Set cached result with smart TTL
     * 
     * @param string $query Search query
     * @param array $options Search options
     * @param array $result Search result
     * @param array $metadata Search metadata
     * @return bool Success
     */
    public function set($query, $options, $result, $metadata = []) {
        $cache_key = $this->generateCacheKey($query, $options);
        $ttl = $this->getCacheDuration($query, $metadata);
        
        $success = set_transient($cache_key, $result, $ttl);
        
        if ($success) {
            error_log("Hybrid Search Cache: ✅ CACHED '{$query}' for {$ttl}s");
        }
        
        return $success;
    }
    
    /**
     * Generate cache key
     * 
     * @param string $query Search query
     * @param array $options Search options
     * @return string Cache key
     */
    private function generateCacheKey($query, $options = []) {
        return self::CACHE_PREFIX . md5($query . json_encode($options));
    }
    
    /**
     * Check if query is popular (frequently searched)
     * 
     * @param string $query Query (lowercase)
     * @return bool
     */
    private function isPopularQuery($query) {
        return in_array($query, $this->popular_queries);
    }
    
    /**
     * Check if query is time-sensitive
     * 
     * @param string $query Query (lowercase)
     * @return bool
     */
    private function isTimeSensitive($query) {
        $time_keywords = ['latest', 'new', 'recent', 'today', 'news', 'current', 'now', 'update'];
        
        foreach ($time_keywords as $keyword) {
            if (strpos($query, $keyword) !== false) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Check if query is navigational
     * 
     * @param string $query Query (lowercase)
     * @return bool
     */
    private function isNavigational($query) {
        $nav_keywords = ['contact', 'about', 'login', 'account', 'career', 'team', 'location', 'office'];
        
        foreach ($nav_keywords as $keyword) {
            if (strpos($query, $keyword) !== false) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Load popular queries from analytics
     */
    private function loadPopularQueries() {
        global $wpdb;
        
        // Get cache
        $cached = get_transient('hybrid_search_popular_queries');
        if ($cached !== false) {
            $this->popular_queries = $cached;
            return;
        }
        
        // Query top 20 searches from last 7 days
        $table = $wpdb->prefix . 'hybrid_search_analytics';
        $date_from = date('Y-m-d H:i:s', strtotime('-7 days'));
        
        $results = $wpdb->get_results($wpdb->prepare(
            "SELECT query, COUNT(*) as count 
             FROM {$table} 
             WHERE created_at >= %s 
             GROUP BY query 
             ORDER BY count DESC 
             LIMIT 20",
            $date_from
        ), ARRAY_A);
        
        if ($results) {
            $this->popular_queries = array_map(
                function($row) { return strtolower($row['query']); },
                $results
            );
            
            // Cache popular queries for 1 hour
            set_transient('hybrid_search_popular_queries', $this->popular_queries, 3600);
        }
    }
    
    /**
     * Pre-warm cache for popular queries
     * 
     * @param callable $search_function Function to perform search
     */
    public function prewarmCache($search_function) {
        try {
            $popular = array_slice($this->popular_queries, 0, 10);
            
            foreach ($popular as $query) {
                // Check if already cached
                if ($this->get($query, []) === false) {
                    // Not cached, search and cache
                    error_log("Hybrid Search Cache: Pre-warming cache for '{$query}'");
                    $result = call_user_func($search_function, $query, ['limit' => 10]);
                    
                    if ($result['success']) {
                        $this->set($query, ['limit' => 10], $result, $result['metadata'] ?? []);
                    }
                }
            }
            
            error_log('Hybrid Search Cache: Pre-warming complete');
            
        } catch (\Exception $e) {
            error_log('Hybrid Search Cache: Pre-warming failed: ' . $e->getMessage());
        }
    }
    
    /**
     * Clear all search caches
     */
    public function clearAll() {
        global $wpdb;
        
        $deleted = $wpdb->query("
            DELETE FROM {$wpdb->options}
            WHERE option_name LIKE '_transient_hybrid_search_%'
               OR option_name LIKE '_transient_timeout_hybrid_search_%'
        ");
        
        error_log("Hybrid Search Cache: Cleared {$deleted} cache entries");
        
        return $deleted;
    }
    
    /**
     * Get cache statistics
     * 
     * @return array Cache stats
     */
    public function getStats() {
        $hits = get_option('hybrid_search_cache_hits', 0);
        $misses = get_option('hybrid_search_cache_misses', 0);
        $total = $hits + $misses;
        $hit_rate = $total > 0 ? ($hits / $total) * 100 : 0;
        
        return [
            'hits' => $hits,
            'misses' => $misses,
            'total_requests' => $total,
            'hit_rate' => round($hit_rate, 2),
            'popular_queries_cached' => count($this->popular_queries)
        ];
    }
}

