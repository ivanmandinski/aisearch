<?php
/**
 * Analytics Service
 * 
 * Business logic layer for analytics functionality.
 * Handles search analytics tracking, data processing, and reporting.
 * 
 * @package SCS\HybridSearch\Services
 * @since 2.0.0
 */

namespace HybridSearch\Services;

use HybridSearch\Database\AnalyticsRepository;
use HybridSearch\Core\Logger;

class AnalyticsService {
    
    /**
     * Analytics repository
     * 
     * @var AnalyticsRepository
     */
    private $repository;
    
    /**
     * Cache service
     * 
     * @var CacheService
     */
    private $cache;
    
    /**
     * Logger instance
     * 
     * @var Logger
     */
    private $logger;
    
    /**
     * Cache keys
     */
    const CACHE_KEY_ANALYTICS_DATA = 'analytics_data_';
    const CACHE_KEY_SEARCH_STATS = 'search_stats_';
    const CACHE_KEY_RECENT_SEARCHES = 'recent_searches';
    const CACHE_DURATION = 3600; // 1 hour
    
    /**
     * Constructor
     * 
     * @param AnalyticsRepository $repository
     * @param CacheService $cache
     * @param Logger $logger
     * @since 2.0.0
     */
    public function __construct(AnalyticsRepository $repository, CacheService $cache, Logger $logger = null) {
        $this->repository = $repository;
        $this->cache = $cache;
        $this->logger = $logger ?: new Logger();
    }
    
    /**
     * Track search analytics
     * 
     * @param string $query Search query
     * @param array $results Search results
     * @param array $metadata Additional metadata
     * @return bool Success status
     * @since 2.0.0
     */
    public function trackSearch($query, $results = [], $metadata = []) {
        try {
            // Validate input
            if (empty($query) || !is_string($query)) {
                $this->logger->warning('Invalid query for analytics tracking', [
                    'query' => $query,
                    'type' => gettype($query)
                ], Logger::CONTEXT_ANALYTICS);
                return false;
            }
            
            // Prepare analytics data
            $analytics_data = [
                'query' => $query,
                'result_count' => count($results),
                'time_taken' => $metadata['response_time'] ?? 0,
                'has_results' => !empty($results),
                'timestamp' => $metadata['timestamp'] ?? current_time('mysql'),
                'session_id' => $metadata['session_id'] ?? $this->generateSessionId(),
                'user_id' => $metadata['user_id'] ?? get_current_user_id(),
            ];
            
            // Add additional metadata if provided
            $analytics_data = array_merge($analytics_data, $metadata);
            
            // Check if we should store this search (deduplication)
            $should_store = $this->repository->shouldStoreSearch($query, $analytics_data['session_id']);
            error_log('Hybrid Search Analytics: Should store query "' . $query . '"? ' . ($should_store ? 'YES' : 'NO (deduplicated)'));
            
            if (!$should_store) {
                $this->logger->debug('Search not stored due to deduplication', [
                    'query' => $query,
                    'session_id' => $analytics_data['session_id']
                ], Logger::CONTEXT_ANALYTICS);
                return true; // Return true as this is expected behavior
            }
            
            // Store analytics data
            error_log('Hybrid Search Analytics: Inserting analytics data: ' . json_encode($analytics_data));
            $insert_id = $this->repository->insert($analytics_data);
            error_log('Hybrid Search Analytics: Insert result ID: ' . ($insert_id ? $insert_id : 'FAILED'));
            
            if ($insert_id) {
                $this->logger->info('Search analytics tracked successfully', [
                    'query' => $query,
                    'result_count' => count($results),
                    'insert_id' => $insert_id
                ], Logger::CONTEXT_ANALYTICS);
                
                // Clear related caches
                $this->clearAnalyticsCaches();
                
                return true;
            } else {
                $this->logger->error('Failed to insert search analytics', [
                    'query' => $query,
                    'analytics_data' => $analytics_data
                ], Logger::CONTEXT_ANALYTICS);
                return false;
            }
            
        } catch (\Exception $e) {
            $this->logger->error('Exception in analytics tracking', [
                'query' => $query,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ], Logger::CONTEXT_ANALYTICS);
            return false;
        }
    }
    
    /**
     * Get analytics data with caching
     * 
     * @param array $args Query arguments
     * @return array Analytics data
     * @since 2.0.0
     */
    public function getAnalyticsData($args = []) {
        $cache_key = self::CACHE_KEY_ANALYTICS_DATA . md5(serialize($args));
        
        // Try to get from cache first
        $cached_data = $this->cache->get($cache_key);
        if ($cached_data !== false) {
            return $cached_data;
        }
        
        // Get from database
        $data = $this->repository->getAnalyticsData($args);
        
        // Cache the result
        $this->cache->set($cache_key, $data, self::CACHE_DURATION);
        
        return $data;
    }
    
    /**
     * Get search statistics with caching
     * 
     * @param int $days Number of days to analyze
     * @return array Search statistics
     * @since 2.0.0
     */
    public function getSearchStats($days = 30) {
        $cache_key = self::CACHE_KEY_SEARCH_STATS . $days;
        
        // Try to get from cache first
        $cached_stats = $this->cache->get($cache_key);
        if ($cached_stats !== false) {
            return $cached_stats;
        }
        
        // Get from database
        $stats = $this->repository->getSearchStats($days);
        
        // Cache the result
        $this->cache->set($cache_key, $stats, self::CACHE_DURATION);
        
        return $stats;
    }
    
    /**
     * Get recent searches with caching
     * 
     * @param int $limit Number of recent searches to retrieve
     * @return array Recent searches
     * @since 2.0.0
     */
    public function getRecentSearches($limit = 10) {
        $cache_key = self::CACHE_KEY_RECENT_SEARCHES . '_' . $limit;
        
        // Try to get from cache first
        $cached_searches = $this->cache->get($cache_key);
        if ($cached_searches !== false) {
            return $cached_searches;
        }
        
        // Get from database
        $searches = $this->repository->getRecentSearches($limit);
        
        // Cache the result
        $this->cache->set($cache_key, $searches, 300); // 5 minutes cache
        
        return $searches;
    }
    
    /**
     * Generate sample analytics data
     * 
     * @param int $count Number of sample records to generate
     * @return bool Success status
     * @since 2.0.0
     */
    public function generateSampleData($count = 50) {
        try {
            $sample_queries = [
                'machine learning', 'python programming', 'data analysis',
                'web development', 'database design', 'cloud computing',
                'cybersecurity', 'mobile development', 'user experience',
                'project management', 'artificial intelligence', 'blockchain',
                'devops', 'software architecture', 'testing frameworks'
            ];
            
            $device_types = ['desktop', 'mobile', 'tablet'];
            $browsers = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera'];
            
            $generated_count = 0;
            
            for ($i = 0; $i < $count; $i++) {
                $query = $sample_queries[array_rand($sample_queries)];
                $result_count = rand(0, 15);
                $time_taken = rand(50, 500) / 1000; // 0.05 to 0.5 seconds
                
                $sample_data = [
                    'query' => $query,
                    'result_count' => $result_count,
                    'time_taken' => $time_taken,
                    'has_results' => $result_count > 0,
                    'session_id' => 'sample_session_' . time() . '_' . $i,
                    'user_id' => rand(1, 10),
                    'device_type' => $device_types[array_rand($device_types)],
                    'browser_name' => $browsers[array_rand($browsers)],
                    'browser_version' => rand(90, 120) . '.0',
                    'language' => rand(0, 1) ? 'en' : 'es',
                    'screen_resolution' => rand(0, 1) ? '1920x1080' : '1366x768',
                    'viewport_size' => rand(0, 1) ? '1920x1080' : '1366x768',
                    'referrer' => rand(0, 1) ? 'https://google.com' : '',
                    'search_method' => 'ajax',
                    'filters' => '',
                    'sort_method' => 'relevance',
                ];
                
                // Add some random timestamp within the last 30 days
                $days_ago = rand(0, 30);
                $hours_ago = rand(0, 23);
                $minutes_ago = rand(0, 59);
                $sample_data['timestamp'] = date('Y-m-d H:i:s', strtotime("-{$days_ago} days -{$hours_ago} hours -{$minutes_ago} minutes"));
                
                $insert_id = $this->repository->insert($sample_data);
                if ($insert_id) {
                    $generated_count++;
                }
            }
            
            $this->logger->info('Sample analytics data generated', [
                'requested_count' => $count,
                'generated_count' => $generated_count
            ], Logger::CONTEXT_ANALYTICS);
            
            // Clear caches
            $this->clearAnalyticsCaches();
            
            return $generated_count > 0;
            
        } catch (\Exception $e) {
            $this->logger->error('Failed to generate sample analytics data', [
                'count' => $count,
                'error' => $e->getMessage()
            ], Logger::CONTEXT_ANALYTICS);
            return false;
        }
    }
    
    /**
     * Get analytics dashboard data
     * 
     * @return array Dashboard data
     * @since 2.0.0
     */
    public function getDashboardData() {
        $cache_key = 'analytics_dashboard_data';
        
        // Try to get from cache first
        $cached_data = $this->cache->get($cache_key);
        if ($cached_data !== false) {
            return $cached_data;
        }
        
        // Get various analytics data
        $stats_30_days = $this->getSearchStats(30);
        $stats_7_days = $this->getSearchStats(7);
        $recent_searches = $this->getRecentSearches(10);
        
        $dashboard_data = [
            'quick_stats' => [
                'total_searches_30_days' => $stats_30_days['total_searches'] ?? 0,
                'total_searches_7_days' => $stats_7_days['total_searches'] ?? 0,
                'searches_with_results_30_days' => $stats_30_days['searches_with_results'] ?? 0,
                'zero_result_searches_30_days' => $stats_30_days['zero_result_searches'] ?? 0,
                'avg_time_taken' => $stats_30_days['avg_time_taken'] ?? 0,
            ],
            'recent_searches' => $recent_searches,
            'popular_queries' => $stats_30_days['popular_queries'] ?? [],
            'device_stats' => $stats_30_days['device_stats'] ?? [],
            'browser_stats' => $stats_30_days['browser_stats'] ?? [],
            'daily_stats' => $stats_30_days['daily_stats'] ?? [],
        ];
        
        // Cache the result
        $this->cache->set($cache_key, $dashboard_data, 600); // 10 minutes cache
        
        return $dashboard_data;
    }
    
    /**
     * Clean old analytics data
     * 
     * @param int $days Days to keep
     * @return int Number of records deleted
     * @since 2.0.0
     */
    public function cleanOldData($days = 90) {
        $deleted_count = $this->repository->cleanOldData($days);
        
        if ($deleted_count > 0) {
            $this->logger->info('Old analytics data cleaned', [
                'deleted_count' => $deleted_count,
                'days_kept' => $days
            ], Logger::CONTEXT_ANALYTICS);
            
            // Clear caches
            $this->clearAnalyticsCaches();
        }
        
        return $deleted_count;
    }
    
    /**
     * Clear analytics-related caches
     * 
     * @since 2.0.0
     */
    private function clearAnalyticsCaches() {
        $this->cache->deletePattern(self::CACHE_KEY_ANALYTICS_DATA . '*');
        $this->cache->deletePattern(self::CACHE_KEY_SEARCH_STATS . '*');
        $this->cache->deletePattern(self::CACHE_KEY_RECENT_SEARCHES . '*');
        $this->cache->delete('analytics_dashboard_data');
    }
    
    /**
     * Generate session ID
     * 
     * @return string
     * @since 2.0.0
     */
    private function generateSessionId() {
        return 'session_' . time() . '_' . wp_generate_password(8, false);
    }
    
    /**
     * Get analytics summary for admin
     * 
     * @return array Summary data
     * @since 2.0.0
     */
    public function getAnalyticsSummary() {
        $cache_key = 'analytics_summary';
        
        // Try to get from cache first
        $cached_summary = $this->cache->get($cache_key);
        if ($cached_summary !== false) {
            return $cached_summary;
        }
        
        $stats_30_days = $this->getSearchStats(30);
        $stats_7_days = $this->getSearchStats(7);
        $stats_1_day = $this->getSearchStats(1);
        
        $summary = [
            'periods' => [
                '1_day' => $stats_1_day,
                '7_days' => $stats_7_days,
                '30_days' => $stats_30_days,
            ],
            'trends' => [
                'searches_trend' => $this->calculateTrend($stats_7_days['total_searches'] ?? 0, $stats_30_days['total_searches'] ?? 0),
                'success_rate_trend' => $this->calculateTrend(
                    $this->calculateSuccessRate($stats_7_days),
                    $this->calculateSuccessRate($stats_30_days)
                ),
                'avg_time_trend' => $this->calculateTrend($stats_7_days['avg_time_taken'] ?? 0, $stats_30_days['avg_time_taken'] ?? 0),
            ],
        ];
        
        // Cache the result
        $this->cache->set($cache_key, $summary, 1800); // 30 minutes cache
        
        return $summary;
    }
    
    /**
     * Calculate trend between two values
     * 
     * @param float $current
     * @param float $previous
     * @return array Trend data
     * @since 2.0.0
     */
    private function calculateTrend($current, $previous) {
        if ($previous == 0) {
            return [
                'direction' => $current > 0 ? 'up' : 'stable',
                'percentage' => $current > 0 ? 100 : 0,
                'value' => $current,
            ];
        }
        
        $percentage = (($current - $previous) / $previous) * 100;
        
        return [
            'direction' => $percentage > 0 ? 'up' : ($percentage < 0 ? 'down' : 'stable'),
            'percentage' => abs(round($percentage, 1)),
            'value' => $current,
        ];
    }
    
    /**
     * Calculate success rate
     * 
     * @param array $stats
     * @return float Success rate percentage
     * @since 2.0.0
     */
    private function calculateSuccessRate($stats) {
        $total = $stats['total_searches'] ?? 0;
        $with_results = $stats['searches_with_results'] ?? 0;
        
        return $total > 0 ? ($with_results / $total) * 100 : 0;
    }
}
