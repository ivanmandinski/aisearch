<?php
/**
 * CTR Service
 * 
 * Business logic layer for Click-Through Rate functionality.
 * Handles CTR tracking, data processing, and reporting.
 * 
 * @package HybridSearch\Services
 * @since 2.0.0
 */

namespace HybridSearch\Services;

use HybridSearch\Database\CTRRepository;
use HybridSearch\Core\Logger;

class CTRService {
    
    /**
     * CTR repository
     * 
     * @var CTRRepository
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
    const CACHE_KEY_CTR_STATS = 'ctr_stats_';
    const CACHE_KEY_TOP_CLICKED = 'top_clicked_';
    const CACHE_DURATION = 3600; // 1 hour
    
    /**
     * Constructor
     * 
     * @param CTRRepository $repository
     * @param CacheService $cache
     * @param Logger $logger
     */
    public function __construct(CTRRepository $repository, CacheService $cache, Logger $logger = null) {
        $this->repository = $repository;
        $this->cache = $cache;
        $this->logger = $logger ?: new Logger();
    }
    
    /**
     * Track CTR click
     * 
     * @param array $ctr_data CTR data
     * @return bool Success status
     */
    public function trackClick($ctr_data) {
        try {
            // Validate input data
            if (!$this->validateCTRData($ctr_data)) {
                $this->logger->warning('Invalid CTR data provided', $ctr_data, Logger::CONTEXT_CTR);
                return false;
            }
            
            // Track the click
            $result = $this->repository->trackClick($ctr_data);
            
            if ($result) {
                $this->logger->info('CTR click tracked successfully', [
                    'result_id' => $ctr_data['result_id'],
                    'position' => $ctr_data['result_position'],
                    'query' => $ctr_data['query']
                ], Logger::CONTEXT_CTR);
                
                // Clear related caches
                $this->clearCTRCaches();
                
                return true;
            } else {
                $this->logger->error('Failed to track CTR click', $ctr_data, Logger::CONTEXT_CTR);
                return false;
            }
            
        } catch (\Exception $e) {
            $this->logger->error('Exception in CTR tracking', [
                'error' => $e->getMessage(),
                'ctr_data' => $ctr_data
            ], Logger::CONTEXT_CTR);
            return false;
        }
    }
    
    /**
     * Get CTR statistics with caching
     * 
     * @param int $days Number of days to analyze
     * @return array CTR statistics
     */
    public function getCTRStats($days = 30) {
        $cache_key = self::CACHE_KEY_CTR_STATS . $days;
        
        // Try to get from cache first
        $cached_stats = $this->cache->get($cache_key);
        if ($cached_stats !== false) {
            return $cached_stats;
        }
        
        // Get from database
        $stats = $this->repository->getCTRStats($days);
        
        // Process and enhance stats
        $processed_stats = $this->processCTRStats($stats);
        
        // Cache the result
        $this->cache->set($cache_key, $processed_stats, self::CACHE_DURATION);
        
        return $processed_stats;
    }
    
    /**
     * Get top clicked results with caching
     * 
     * @param int $days Number of days to analyze
     * @param int $limit Number of results to return
     * @return array Top clicked results
     */
    public function getTopClickedResults($days = 30, $limit = 10) {
        $cache_key = self::CACHE_KEY_TOP_CLICKED . $days . '_' . $limit;
        
        // Try to get from cache first
        $cached_results = $this->cache->get($cache_key);
        if ($cached_results !== false) {
            return $cached_results;
        }
        
        // Get CTR stats (includes top clicked)
        $stats = $this->getCTRStats($days);
        $top_clicked = array_slice($stats['top_clicked'] ?? [], 0, $limit);
        
        // Cache the result
        $this->cache->set($cache_key, $top_clicked, self::CACHE_DURATION);
        
        return $top_clicked;
    }
    
    /**
     * Get CTR dashboard data
     * 
     * @return array Dashboard data
     */
    public function getDashboardData() {
        $cache_key = 'ctr_dashboard_data';
        
        // Try to get from cache first
        $cached_data = $this->cache->get($cache_key);
        if ($cached_data !== false) {
            return $cached_data;
        }
        
        // Get various CTR data
        $stats_30_days = $this->getCTRStats(30);
        $stats_7_days = $this->getCTRStats(7);
        $top_clicked = $this->getTopClickedResults(30, 10);
        
        $dashboard_data = [
            'ctr_overview' => [
                'total_impressions_30_days' => $this->calculateTotalImpressions($stats_30_days),
                'total_clicks_30_days' => $this->calculateTotalClicks($stats_30_days),
                'overall_ctr_30_days' => $this->calculateOverallCTR($stats_30_days),
                'total_impressions_7_days' => $this->calculateTotalImpressions($stats_7_days),
                'total_clicks_7_days' => $this->calculateTotalClicks($stats_7_days),
                'overall_ctr_7_days' => $this->calculateOverallCTR($stats_7_days),
            ],
            'position_analysis' => $stats_30_days['overall_stats'] ?? [],
            'top_clicked_results' => $top_clicked,
        ];
        
        // Cache the result
        $this->cache->set($cache_key, $dashboard_data, 600); // 10 minutes cache
        
        return $dashboard_data;
    }
    
    /**
     * Get debug information
     * 
     * @return array Debug information
     */
    public function getDebugInfo() {
        return $this->repository->getDebugInfo();
    }
    
    /**
     * Generate sample CTR data
     * 
     * @param int $count Number of sample records to generate
     * @return bool Success status
     */
    public function generateSampleData($count = 50) {
        try {
            $sample_titles = [
                'Introduction to Machine Learning',
                'Advanced Python Programming',
                'Data Analysis Techniques',
                'Web Development Best Practices',
                'Database Design Principles',
                'Cloud Computing Fundamentals',
                'Cybersecurity Essentials',
                'Mobile App Development',
                'User Experience Design',
                'Project Management Guide'
            ];
            
            $sample_urls = [
                '/machine-learning-intro',
                '/python-programming-guide',
                '/data-analysis-tutorial',
                '/web-development-tips',
                '/database-design-guide',
                '/cloud-computing-basics',
                '/cybersecurity-essentials',
                '/mobile-development-guide',
                '/ux-design-principles',
                '/project-management-tips'
            ];
            
            $generated_count = 0;
            
            for ($i = 0; $i < $count; $i++) {
                $title = $sample_titles[array_rand($sample_titles)];
                $url = $sample_urls[array_rand($sample_urls)];
                $position = rand(1, 10);
                $score = rand(50, 100) / 100;
                $clicked = rand(0, 1);
                
                $sample_data = [
                    'search_id' => rand(1, 100),
                    'result_id' => 'sample_result_' . $i,
                    'result_title' => $title,
                    'result_url' => $url,
                    'result_position' => $position,
                    'result_score' => $score,
                    'clicked' => $clicked,
                    'click_timestamp' => $clicked ? current_time('mysql') : null,
                    'session_id' => 'sample_session_' . time() . '_' . $i,
                    'user_id' => rand(1, 10),
                    'device_type' => rand(0, 1) ? 'desktop' : 'mobile',
                    'browser_name' => rand(0, 1) ? 'Chrome' : 'Firefox',
                    'query' => 'sample search query ' . rand(1, 10),
                    'timestamp' => date('Y-m-d H:i:s', strtotime('-' . rand(0, 30) . ' days -' . rand(0, 23) . ' hours -' . rand(0, 59) . ' minutes')),
                ];
                
                $insert_id = $this->repository->insert($sample_data);
                if ($insert_id) {
                    $generated_count++;
                }
            }
            
            $this->logger->info('Sample CTR data generated', [
                'requested_count' => $count,
                'generated_count' => $generated_count
            ], Logger::CONTEXT_CTR);
            
            // Clear caches
            $this->clearCTRCaches();
            
            return $generated_count > 0;
            
        } catch (\Exception $e) {
            $this->logger->error('Failed to generate sample CTR data', [
                'count' => $count,
                'error' => $e->getMessage()
            ], Logger::CONTEXT_CTR);
            return false;
        }
    }
    
    /**
     * Clean old CTR data
     * 
     * @param int $days Days to keep
     * @return int Number of records deleted
     */
    public function cleanOldData($days = 90) {
        $deleted_count = $this->repository->cleanOldData($days);
        
        if ($deleted_count > 0) {
            $this->logger->info('Old CTR data cleaned', [
                'deleted_count' => $deleted_count,
                'days_kept' => $days
            ], Logger::CONTEXT_CTR);
            
            // Clear caches
            $this->clearCTRCaches();
        }
        
        return $deleted_count;
    }
    
    /**
     * Validate CTR data
     * 
     * @param array $ctr_data CTR data to validate
     * @return bool True if valid
     */
    private function validateCTRData($ctr_data) {
        $required_fields = ['result_id', 'result_title', 'result_url', 'result_position', 'query'];
        
        foreach ($required_fields as $field) {
            if (!isset($ctr_data[$field]) || empty($ctr_data[$field])) {
                return false;
            }
        }
        
        // Validate URL
        if (!filter_var($ctr_data['result_url'], FILTER_VALIDATE_URL)) {
            return false;
        }
        
        // Validate position
        if (!is_numeric($ctr_data['result_position']) || $ctr_data['result_position'] < 1) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Process CTR statistics
     * 
     * @param array $stats Raw CTR statistics
     * @return array Processed statistics
     */
    private function processCTRStats($stats) {
        $processed = $stats;
        
        // Calculate CTR percentages for each position
        if (isset($processed['overall_stats'])) {
            foreach ($processed['overall_stats'] as &$stat) {
                if ($stat['position_impressions'] > 0) {
                    $stat['ctr_percentage'] = round(($stat['position_clicks'] / $stat['position_impressions']) * 100, 2);
                } else {
                    $stat['ctr_percentage'] = 0;
                }
            }
        }
        
        return $processed;
    }
    
    /**
     * Calculate total impressions
     * 
     * @param array $stats CTR statistics
     * @return int Total impressions
     */
    private function calculateTotalImpressions($stats) {
        $total = 0;
        if (isset($stats['overall_stats'])) {
            foreach ($stats['overall_stats'] as $stat) {
                $total += (int) $stat['position_impressions'];
            }
        }
        return $total;
    }
    
    /**
     * Calculate total clicks
     * 
     * @param array $stats CTR statistics
     * @return int Total clicks
     */
    private function calculateTotalClicks($stats) {
        $total = 0;
        if (isset($stats['overall_stats'])) {
            foreach ($stats['overall_stats'] as $stat) {
                $total += (int) $stat['position_clicks'];
            }
        }
        return $total;
    }
    
    /**
     * Calculate overall CTR
     * 
     * @param array $stats CTR statistics
     * @return float Overall CTR percentage
     */
    private function calculateOverallCTR($stats) {
        $impressions = $this->calculateTotalImpressions($stats);
        $clicks = $this->calculateTotalClicks($stats);
        
        if ($impressions > 0) {
            return round(($clicks / $impressions) * 100, 2);
        }
        
        return 0;
    }
    
    /**
     * Clear CTR-related caches
     */
    private function clearCTRCaches() {
        $this->cache->deletePattern(self::CACHE_KEY_CTR_STATS . '*');
        $this->cache->deletePattern(self::CACHE_KEY_TOP_CLICKED . '*');
        $this->cache->delete('ctr_dashboard_data');
    }
}

