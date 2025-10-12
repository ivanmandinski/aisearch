<?php
/**
 * AJAX Manager
 * 
 * Centralized AJAX request handling for the Hybrid Search plugin.
 * Manages all AJAX endpoints, security, and request routing.
 * 
 * @package SCS\HybridSearch\AJAX
 * @since 2.0.0
 */

namespace HybridSearch\AJAX;

use HybridSearch\API\SearchAPI;
use HybridSearch\API\APIClient;
use HybridSearch\Services\AnalyticsService;
use HybridSearch\Services\CTRService;
use HybridSearch\Core\Security;

class AJAXManager {
    
    /**
     * Search API instance
     * 
     * @var SearchAPI
     */
    private $search_api;
    
    /**
     * Analytics service instance
     * 
     * @var AnalyticsService
     */
    private $analytics_service;
    
    /**
     * CTR service instance
     * 
     * @var CTRService
     */
    private $ctr_service;
    
    /**
     * Security manager instance
     * 
     * @var Security
     */
    private $security;
    
    /**
     * AJAX actions configuration
     * 
     * @var array
     */
    private $actions = [
        'hybrid_search' => [
            'handler' => 'handleSearch',
            'public' => true,
            'security' => 'none',
        ],
        'track_search_analytics' => [
            'handler' => 'handleTrackAnalytics',
            'public' => true,
            'security' => 'none',
        ],
        'track_search_ctr' => [
            'handler' => 'handleTrackCTR',
            'public' => true,
            'security' => 'none',
        ],
        'get_search_analytics' => [
            'handler' => 'handleGetAnalytics',
            'public' => false,
            'security' => 'nonce_capability',
            'capability' => 'manage_options',
        ],
        'generate_sample_analytics' => [
            'handler' => 'handleGenerateSampleAnalytics',
            'public' => false,
            'security' => 'nonce_capability',
            'capability' => 'manage_options',
        ],
        'test_analytics_tracking' => [
            'handler' => 'handleTestAnalyticsTracking',
            'public' => false,
            'security' => 'nonce_capability',
            'capability' => 'manage_options',
        ],
        'test_ctr_tracking' => [
            'handler' => 'handleTestCTRTracking',
            'public' => false,
            'security' => 'nonce_capability',
            'capability' => 'manage_options',
        ],
        'debug_ctr_data' => [
            'handler' => 'handleDebugCTRData',
            'public' => false,
            'security' => 'nonce_capability',
            'capability' => 'manage_options',
        ],
        'test_hybrid_search_api' => [
            'handler' => 'handleTestAPI',
            'public' => false,
            'security' => 'nonce_capability',
            'capability' => 'manage_options',
        ],
        'reindex_content' => [
            'handler' => 'handleReindexContent',
            'public' => false,
            'security' => 'capability_only',
            'capability' => 'manage_options',
        ],
    ];
    
    /**
     * Constructor
     * 
     * @param SearchAPI $search_api
     * @param AnalyticsService $analytics_service
     * @param CTRService $ctr_service
     * @param Security $security
     * @since 2.0.0
     */
    public function __construct(
        SearchAPI $search_api,
        AnalyticsService $analytics_service,
        CTRService $ctr_service,
        Security $security
    ) {
        $this->search_api = $search_api;
        $this->analytics_service = $analytics_service;
        $this->ctr_service = $ctr_service;
        $this->security = $security;
    }
    
    /**
     * Register WordPress hooks
     * 
     * @since 2.0.0
     */
    public function registerHooks() {
        foreach ($this->actions as $action => $config) {
            // Register for logged-in users
            add_action('wp_ajax_' . $action, [$this, 'handleAJAXRequest']);
            
            // Register for non-logged-in users if public
            if ($config['public']) {
                add_action('wp_ajax_nopriv_' . $action, [$this, 'handleAJAXRequest']);
            }
        }
    }
    
    /**
     * Handle AJAX request
     * 
     * @since 2.0.0
     */
    public function handleAJAXRequest() {
        $action = sanitize_text_field($_POST['action'] ?? '');
        
        if (empty($action) || !isset($this->actions[$action])) {
            $this->sendError('Invalid AJAX action');
            return;
        }
        
        $config = $this->actions[$action];
        
        // Security check
        if (!$this->validateSecurity($config)) {
            $this->sendError('Security validation failed');
            return;
        }
        
        // Rate limiting check
        if (!$this->security->checkRateLimit()) {
            $this->security->logSecurityEvent('rate_limit_exceeded', [
                'action' => $action,
                'ip' => $this->security->getClientIP(),
            ]);
            $this->sendError('Rate limit exceeded');
            return;
        }
        
        try {
            // Call appropriate handler
            $handler_method = $config['handler'];
            if (method_exists($this, $handler_method)) {
                $result = $this->$handler_method();
                $this->sendSuccess($result);
            } else {
                $this->sendError('Handler method not found');
            }
        } catch (\Exception $e) {
            $this->security->logSecurityEvent('ajax_error', [
                'action' => $action,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);
            $this->sendError('Request failed: ' . $e->getMessage());
        }
    }
    
    /**
     * Validate security for AJAX request
     * 
     * @param array $config Action configuration
     * @return bool
     * @since 2.0.0
     */
    private function validateSecurity($config) {
        switch ($config['security']) {
            case 'none':
                return true;
                
            case 'nonce':
                $nonce = sanitize_text_field($_POST['nonce'] ?? '');
                return $this->security->validateNonce($config['handler'], $nonce);
                
            case 'nonce_capability':
                $nonce = sanitize_text_field($_POST['nonce'] ?? '');
                $capability = $config['capability'] ?? 'manage_options';
                
                return $this->security->validateNonce($config['handler'], $nonce) &&
                       $this->security->userCan($capability);
                       
            case 'capability_only':
                $capability = $config['capability'] ?? 'manage_options';
                return $this->security->userCan($capability);
                
            default:
                return false;
        }
    }
    
    /**
     * Send success response
     * 
     * @param mixed $data Response data
     * @since 2.0.0
     */
    private function sendSuccess($data) {
        wp_send_json_success($data);
    }
    
    /**
     * Send error response
     * 
     * @param string $message Error message
     * @param int $code Error code
     * @since 2.0.0
     */
    private function sendError($message, $code = 400) {
        wp_send_json_error([
            'message' => $message,
            'code' => $code,
        ]);
    }
    
    /**
     * Handle search request
     * 
     * @return array Search results
     * @since 2.0.0
     */
    public function handleSearch() {
        $query = $this->security->validateSearchQuery($_POST['query'] ?? '');
        $limit = (int) ($_POST['limit'] ?? 10);
        $offset = (int) ($_POST['offset'] ?? 0);
        $include_answer = (bool) ($_POST['include_answer'] ?? false);
        $ai_instructions = sanitize_textarea_field($_POST['ai_instructions'] ?? '');
        
        // Get filter parameters
        $filter_type = sanitize_text_field($_POST['filter_type'] ?? '');
        $filter_date = sanitize_text_field($_POST['filter_date'] ?? '');
        $filter_sort = sanitize_text_field($_POST['filter_sort'] ?? 'relevance');
        
        if (!$query) {
            $this->sendError('Invalid search query');
            return;
        }
        
        // Validate limit and offset
        if ($limit < 1 || $limit > 50) {
            $limit = 10;
        }
        if ($offset < 0) {
            $offset = 0;
        }
        
        // Get AI instructions from settings if not provided
        if (empty($ai_instructions)) {
            $ai_instructions = get_option('hybrid_search_ai_instructions', '');
        }
        
        // Get AI reranking settings
        $enable_ai_reranking = get_option('hybrid_search_ai_reranking_enabled', true);
        $ai_weight = get_option('hybrid_search_ai_weight', 70) / 100; // Convert to 0-1
        $ai_reranking_instructions = get_option('hybrid_search_ai_reranking_instructions', '');
        
        // Log search parameters for debugging
        error_log('Hybrid Search: Query=' . $query . ', Filters=[type:' . $filter_type . ', date:' . $filter_date . ', sort:' . $filter_sort . ']');
        error_log('Hybrid Search: AI Reranking enabled=' . ($enable_ai_reranking ? 'yes' : 'no') . 
                  ', weight=' . $ai_weight . 
                  ', custom_instructions=' . (!empty($ai_reranking_instructions) ? 'yes' : 'no'));
        
        // Perform search with pagination and filters
        $search_options = [
            'limit' => $limit,
            'offset' => $offset,
            'include_answer' => $include_answer,
            'ai_instructions' => $ai_instructions,
            'enable_ai_reranking' => $enable_ai_reranking,
            'ai_weight' => $ai_weight,
            'ai_reranking_instructions' => $ai_reranking_instructions,
            'filters' => [
                'type' => $filter_type,
                'date' => $filter_date,
                'sort' => $filter_sort,
            ],
        ];
        
        $result = $this->search_api->search($query, $search_options);
        
        // Log what we received from API (AI reranking already done by Railway)
        if ($result['success'] && !empty($result['results'])) {
            $total_results = count($result['results']);
            error_log('Hybrid Search: Received ' . $total_results . ' results from API (AI reranking already applied)');
            error_log('Hybrid Search: Top 3 results from API: ' . 
                json_encode(array_map(function($r) { 
                    return [
                        'title' => substr($r['title'], 0, 50),
                        'type' => $r['type'] ?? 'unknown',
                        'score' => round($r['score'] ?? 0, 3),
                        'ai_score' => round($r['ai_score'] ?? 0, 3)
                    ];
                }, array_slice($result['results'], 0, 3))));
            
            // Detect query intent to determine ranking strategy
            $intent = $this->getQueryIntent($query);
            
            // Apply ranking strategy based on intent
            switch ($intent) {
                case 'navigational':
                    // Trust AI completely - user looking for specific page
                    error_log('Hybrid Search: Using AI ranking only (navigational query)');
                    // Don't apply any type priority, keep AI order
                    break;
                    
                case 'informational':
                    // Use smart priority - protect top results but group rest
                    error_log('Hybrid Search: Using smart priority (informational query)');
                    $result['results'] = $this->applySmartPriority($result['results']);
                    break;
                    
                case 'transactional':
                    // Use strict priority - type matters for transactions
                    error_log('Hybrid Search: Using strict priority (transactional query)');
                    $result['results'] = $this->applyPostTypePriority($result['results']);
                    break;
                    
                case 'general':
                default:
                    // Balanced approach - use smart priority
                    error_log('Hybrid Search: Using smart priority (general query)');
                    $result['results'] = $this->applySmartPriority($result['results']);
                    break;
            }
            
            // Then apply other filters (type, date) - these filter OUT results but don't re-sort
            $result['results'] = $this->applyFilters($result['results'], $filter_type, $filter_date, $filter_sort);
            
            // Apply pagination AFTER priority and filters
            $total_after_filters = count($result['results']);
            error_log('Hybrid Search: Total results after priority+filters: ' . $total_after_filters);
            
            // Slice results for pagination
            $result['results'] = array_slice($result['results'], $offset, $limit);
            
            error_log('Hybrid Search: Returning ' . count($result['results']) . ' results for current page (offset=' . $offset . ', limit=' . $limit . ')');
        }
        
        // Store analytics only for first page (offset = 0)
        if ($result['success'] && $offset === 0) {
            error_log('Hybrid Search: Attempting to track analytics for query: ' . $query);
            $tracking_result = $this->analytics_service->trackSearch($query, $result['results'], $result['metadata']);
            error_log('Hybrid Search: Analytics tracking result: ' . ($tracking_result ? 'SUCCESS' : 'FAILED'));
        } else {
            if (!$result['success']) {
                error_log('Hybrid Search: NOT tracking analytics - search failed');
            } elseif ($offset !== 0) {
                error_log('Hybrid Search: NOT tracking analytics - pagination request (offset=' . $offset . ')');
            }
        }
        
        // Update AI reranking stats (if AI was used)
        if ($result['success'] && $enable_ai_reranking) {
            if (isset($result['metadata']['ai_reranking_used']) && $result['metadata']['ai_reranking_used']) {
                error_log('Hybrid Search: AI reranking WAS used, updating stats');
                $this->updateAIRerankingStats($result['metadata']);
            } else {
                error_log('Hybrid Search: AI reranking NOT used. Metadata: ' . json_encode($result['metadata']));
                error_log('Hybrid Search: This means Railway API does not have AI reranking deployed yet');
            }
        } else {
            error_log('Hybrid Search: AI reranking disabled in settings or search failed');
        }
        
        // Add pagination info to result
        if ($result['success']) {
            $result['pagination'] = [
                'offset' => $offset,
                'limit' => $limit,
                'has_more' => count($result['results']) === $limit,
                'next_offset' => $offset + $limit,
            ];
        }
        
        return $result;
    }
    
    /**
     * Apply filters to search results
     * 
     * @param array $results Search results
     * @param string $type Type filter
     * @param string $date Date filter
     * @param string $sort Sort filter
     * @return array Filtered results
     * @since 2.3.7
     */
    private function applyFilters($results, $type, $date, $sort) {
        // Filter by type
        if (!empty($type)) {
            $results = array_filter($results, function($result) use ($type) {
                return isset($result['type']) && $result['type'] === $type;
            });
        }
        
        // Filter by date
        if (!empty($date)) {
            $date_threshold = $this->getDateThreshold($date);
            $results = array_filter($results, function($result) use ($date_threshold) {
                if (!isset($result['date'])) return true;
                $result_date = strtotime($result['date']);
                return $result_date >= $date_threshold;
            });
        }
        
        // Sort results
        if (!empty($sort) && $sort !== 'relevance') {
            $results = $this->sortResults($results, $sort);
        }
        
        // Re-index array after filtering
        return array_values($results);
    }
    
    /**
     * Get date threshold based on filter
     * 
     * @param string $date_filter Date filter (day, week, month, year)
     * @return int Unix timestamp
     * @since 2.3.7
     */
    private function getDateThreshold($date_filter) {
        $now = current_time('timestamp');
        
        switch ($date_filter) {
            case 'day':
                return $now - DAY_IN_SECONDS;
            case 'week':
                return $now - WEEK_IN_SECONDS;
            case 'month':
                return $now - MONTH_IN_SECONDS;
            case 'year':
                return $now - YEAR_IN_SECONDS;
            default:
                return 0;
        }
    }
    
    /**
     * Sort search results while maintaining post type priority grouping
     * Sorts within each priority group instead of globally
     * 
     * @param array $results Search results (already grouped by priority)
     * @param string $sort_by Sort method
     * @return array Sorted results
     * @since 2.3.7
     */
    private function sortResults($results, $sort_by) {
        // Get priority order to maintain grouping
        $priority_order = get_option('hybrid_search_post_type_priority', ['post', 'page']);
        if (!is_array($priority_order)) {
            $priority_order = ['post', 'page'];
        }
        
        // Group results by post type to maintain priority
        $grouped_results = [];
        foreach ($results as $result) {
            $type = $result['type'] ?? 'unknown';
            if (!isset($grouped_results[$type])) {
                $grouped_results[$type] = [];
            }
            $grouped_results[$type][] = $result;
        }
        
        // Sort each group individually based on sort method
        foreach ($grouped_results as $type => &$group) {
            switch ($sort_by) {
                case 'date-desc':
                    usort($group, function($a, $b) {
                        $date_a = strtotime($a['date'] ?? '1970-01-01');
                        $date_b = strtotime($b['date'] ?? '1970-01-01');
                        return $date_b - $date_a; // Newest first
                    });
                    break;
                    
                case 'date-asc':
                    usort($group, function($a, $b) {
                        $date_a = strtotime($a['date'] ?? '1970-01-01');
                        $date_b = strtotime($b['date'] ?? '1970-01-01');
                        return $date_a - $date_b; // Oldest first
                    });
                    break;
                    
                case 'title-asc':
                    usort($group, function($a, $b) {
                        return strcmp($a['title'] ?? '', $b['title'] ?? '');
                    });
                    break;
                    
                default: // 'relevance' or unknown
                    usort($group, function($a, $b) {
                        $score_a = $a['score'] ?? 0;
                        $score_b = $b['score'] ?? 0;
                        return $score_b <=> $score_a; // Higher score first
                    });
                    break;
            }
        }
        
        // Rebuild results array in priority order
        $sorted_results = [];
        
        // First, add results from types in priority order
        foreach ($priority_order as $priority_type) {
            if (isset($grouped_results[$priority_type])) {
                $sorted_results = array_merge($sorted_results, $grouped_results[$priority_type]);
                unset($grouped_results[$priority_type]);
            }
        }
        
        // Then, add any remaining types not in priority list
        ksort($grouped_results);
        foreach ($grouped_results as $type => $group) {
            $sorted_results = array_merge($sorted_results, $group);
        }
        
        return $sorted_results;
    }
    
    /**
     * Detect query intent to adjust ranking strategy
     * 
     * @param string $query Search query
     * @return string Intent type: 'navigational', 'informational', 'transactional', or 'general'
     * @since 2.7.0
     */
    private function getQueryIntent($query) {
        $query_lower = strtolower(trim($query));
        
        // Navigational queries (looking for specific page)
        $navigational_keywords = ['contact', 'about', 'login', 'account', 'career', 'jobs', 'team', 'location', 'office'];
        foreach ($navigational_keywords as $keyword) {
            if (strpos($query_lower, $keyword) !== false) {
                error_log('Hybrid Search: Detected NAVIGATIONAL intent for query: ' . $query);
                return 'navigational';
            }
        }
        
        // Question/informational queries (how-to, what is, why, etc.)
        if (preg_match('/^(how|what|why|when|where|can|should|is|are|do|does|will)\b/i', $query_lower)) {
            error_log('Hybrid Search: Detected INFORMATIONAL intent for query: ' . $query);
            return 'informational';
        }
        
        // Transactional queries (looking to do something)
        $transactional_keywords = ['buy', 'download', 'order', 'purchase', 'get', 'find', 'hire', 'request'];
        foreach ($transactional_keywords as $keyword) {
            if (strpos($query_lower, $keyword) !== false) {
                error_log('Hybrid Search: Detected TRANSACTIONAL intent for query: ' . $query);
                return 'transactional';
            }
        }
        
        error_log('Hybrid Search: Detected GENERAL intent for query: ' . $query);
        return 'general';
    }
    
    /**
     * Apply smart priority sorting - protects highly relevant results from demotion
     * This is an improved version that balances type priority with AI relevance
     * 
     * @param array $results Search results (already AI-ranked)
     * @return array Sorted results
     * @since 2.7.0
     */
    private function applySmartPriority($results) {
        // Configuration
        $protected_count = 3;  // Always protect top 3 results
        $relevance_threshold = 0.85;  // High relevance threshold
        
        error_log('Hybrid Search: Applying SMART priority (protects top ' . $protected_count . ' and score > ' . $relevance_threshold . ')');
        
        // Step 1: Separate highly relevant results from regular ones
        $protected_results = [];
        $regular_results = [];
        
        foreach ($results as $index => $result) {
            $score = $result['score'] ?? 0;
            
            // Protect if in top N OR has very high relevance score
            if ($index < $protected_count || $score >= $relevance_threshold) {
                $protected_results[] = $result;
                error_log('Hybrid Search: PROTECTED result #' . ($index + 1) . ': "' . substr($result['title'], 0, 50) . '" (score: ' . round($score, 3) . ')');
            } else {
                $regular_results[] = $result;
            }
        }
        
        // Step 2: Apply traditional type priority ONLY to non-protected results
        if (!empty($regular_results)) {
            error_log('Hybrid Search: Applying type priority to ' . count($regular_results) . ' non-protected results');
            $prioritized_regular = $this->applyPostTypePriority($regular_results);
        } else {
            $prioritized_regular = [];
        }
        
        // Step 3: Merge - protected first, then prioritized
        $final_results = array_merge($protected_results, $prioritized_regular);
        
        error_log('Hybrid Search: Smart priority complete. Protected: ' . count($protected_results) . ', Prioritized: ' . count($prioritized_regular));
        
        return $final_results;
    }
    
    /**
     * Apply post type priority sorting to results
     * Groups results by post type priority, showing all results from higher priority types first
     * 
     * @param array $results Search results
     * @return array Sorted results
     * @since 2.5.0
     */
    private function applyPostTypePriority($results) {
        // Get priority order from settings
        $priority_order = get_option('hybrid_search_post_type_priority', ['post', 'page']);
        if (!is_array($priority_order)) {
            $priority_order = ['post', 'page'];
        }
        
        error_log('Hybrid Search: Applying post type priority order: ' . json_encode($priority_order));
        
        // Group results by post type
        $grouped_results = [];
        foreach ($results as $result) {
            $type = $result['type'] ?? 'unknown';
            if (!isset($grouped_results[$type])) {
                $grouped_results[$type] = [];
            }
            $grouped_results[$type][] = $result;
        }
        
        // Sort each group by relevance score (highest first)
        foreach ($grouped_results as $type => &$group) {
            usort($group, function($a, $b) {
                $score_a = $a['score'] ?? 0;
                $score_b = $b['score'] ?? 0;
                return $score_b <=> $score_a; // Higher score first
            });
        }
        
        // Rebuild results array in priority order
        $sorted_results = [];
        
        // First, add results from types in priority order
        foreach ($priority_order as $priority_type) {
            if (isset($grouped_results[$priority_type])) {
                $sorted_results = array_merge($sorted_results, $grouped_results[$priority_type]);
                unset($grouped_results[$priority_type]); // Remove from grouped to avoid duplicates
            }
        }
        
        // Then, add any remaining types not in priority list (sorted by type name)
        ksort($grouped_results);
        foreach ($grouped_results as $type => $group) {
            $sorted_results = array_merge($sorted_results, $group);
        }
        
        error_log('Hybrid Search: Priority sorting complete. Result order: ' . 
            json_encode(array_map(function($r) { 
                return $r['type'] . ':' . ($r['score'] ?? 0); 
            }, array_slice($sorted_results, 0, 10))));
        
        return $sorted_results;
    }
    
    /**
     * Update AI reranking statistics
     * 
     * @param array $metadata Search metadata with AI stats
     * @return void
     * @since 2.6.0
     */
    private function updateAIRerankingStats($metadata) {
        $stats = get_option('hybrid_search_ai_reranking_stats', [
            'total_searches' => 0,
            'avg_response_time' => 0,
            'total_cost' => 0,
            'last_updated' => ''
        ]);
        
        // Increment search count
        $stats['total_searches']++;
        
        // Update average response time (rolling average)
        if (isset($metadata['ai_response_time'])) {
            $total_time = $stats['avg_response_time'] * ($stats['total_searches'] - 1);
            $stats['avg_response_time'] = ($total_time + $metadata['ai_response_time']) / $stats['total_searches'];
        }
        
        // Update total cost
        if (isset($metadata['ai_cost'])) {
            $stats['total_cost'] += $metadata['ai_cost'];
        }
        
        // Update timestamp
        $stats['last_updated'] = current_time('mysql');
        
        // Save stats
        update_option('hybrid_search_ai_reranking_stats', $stats, false);
        
        error_log('Hybrid Search: Updated AI stats - Total searches: ' . $stats['total_searches'] . 
                  ', Avg time: ' . round($stats['avg_response_time'], 2) . 's' .
                  ', Total cost: $' . number_format($stats['total_cost'], 6));
    }
    
    /**
     * Handle analytics tracking request
     * 
     * @return array Tracking result
     * @since 2.0.0
     */
    public function handleTrackAnalytics() {
        $analytics_data = $_POST['analytics'] ?? [];
        
        if (!is_array($analytics_data)) {
            $this->sendError('Invalid analytics data');
            return;
        }
        
        // Sanitize analytics data
        $analytics_data = $this->sanitizeAnalyticsData($analytics_data);
        
        $result = $this->analytics_service->trackSearch(
            $analytics_data['query'] ?? '',
            $analytics_data['results'] ?? [],
            $analytics_data
        );
        
        return [
            'success' => $result,
            'message' => $result ? 'Analytics tracked successfully' : 'Failed to track analytics',
        ];
    }
    
    /**
     * Handle CTR tracking request
     * 
     * @return array Tracking result
     * @since 2.0.0
     */
    public function handleTrackCTR() {
        $ctr_data = $_POST['ctr_data'] ?? [];
        
        if (!is_array($ctr_data)) {
            $this->sendError('Invalid CTR data');
            return;
        }
        
        // Sanitize CTR data
        $ctr_data = $this->sanitizeCTRData($ctr_data);
        
        $result = $this->ctr_service->trackClick($ctr_data);
        
        return [
            'success' => $result,
            'message' => $result ? 'CTR tracked successfully' : 'Failed to track CTR',
        ];
    }
    
    /**
     * Handle get analytics request
     * 
     * @return array Analytics data
     * @since 2.0.0
     */
    public function handleGetAnalytics() {
        $args = [
            'page' => (int) ($_POST['page'] ?? 1),
            'per_page' => (int) ($_POST['per_page'] ?? 50),
            'search' => sanitize_text_field($_POST['search'] ?? ''),
            'date_from' => sanitize_text_field($_POST['date_from'] ?? ''),
            'date_to' => sanitize_text_field($_POST['date_to'] ?? ''),
            'device_type' => sanitize_text_field($_POST['device_type'] ?? ''),
            'browser_name' => sanitize_text_field($_POST['browser_name'] ?? ''),
        ];
        
        return $this->analytics_service->getAnalyticsData($args);
    }
    
    /**
     * Handle generate sample analytics request
     * 
     * @return array Generation result
     * @since 2.0.0
     */
    public function handleGenerateSampleAnalytics() {
        $count = (int) ($_POST['count'] ?? 50);
        
        if ($count < 1 || $count > 1000) {
            $count = 50;
        }
        
        $result = $this->analytics_service->generateSampleData($count);
        
        return [
            'success' => $result,
            'message' => $result ? "Generated {$count} sample analytics records" : 'Failed to generate sample data',
            'count' => $count,
        ];
    }
    
    /**
     * Handle test analytics tracking request
     * 
     * @return array Test result
     * @since 2.0.0
     */
    public function handleTestAnalyticsTracking() {
        $test_data = [
            'query' => 'test analytics tracking',
            'result_count' => 5,
            'time_taken' => 0.123,
            'has_results' => true,
            'session_id' => 'test_session_' . time(),
            'user_id' => get_current_user_id(),
        ];
        
        $result = $this->analytics_service->trackSearch($test_data['query'], [], $test_data);
        
        return [
            'success' => $result,
            'message' => $result ? 'Analytics tracking test successful' : 'Analytics tracking test failed',
            'test_data' => $test_data,
        ];
    }
    
    /**
     * Handle test CTR tracking request
     * 
     * @return array Test result
     * @since 2.0.0
     */
    public function handleTestCTRTracking() {
        $test_data = [
            'search_id' => 999,
            'result_id' => 'test_result_' . time(),
            'result_title' => 'Test Result Title',
            'result_url' => 'https://example.com/test',
            'result_position' => 1,
            'result_score' => 0.95,
            'session_id' => 'test_session_' . time(),
            'user_id' => get_current_user_id(),
            'query' => 'test ctr tracking',
        ];
        
        $result = $this->ctr_service->trackClick($test_data);
        
        return [
            'success' => $result,
            'message' => $result ? 'CTR tracking test successful' : 'CTR tracking test failed',
            'test_data' => $test_data,
        ];
    }
    
    /**
     * Handle debug CTR data request
     * 
     * @return array Debug information
     * @since 2.0.0
     */
    public function handleDebugCTRData() {
        return $this->ctr_service->getDebugInfo();
    }
    
    /**
     * Handle test API request
     * 
     * @return array API test result
     * @since 2.0.0
     */
    public function handleTestAPI() {
        return $this->search_api->testConnection();
    }
    
    /**
     * Handle reindex content request
     * 
     * @return array Reindex result
     * @since 2.0.1
     */
    public function handleReindexContent() {
        try {
            error_log('Hybrid Search: Starting reindex function');
            
            // Get API configuration
            $api_url = get_option('hybrid_search_api_url', '');
            
            if (empty($api_url)) {
                return [
                    'success' => false,
                    'message' => 'API URL not configured. Please set the API URL in plugin settings.',
                    'indexed_count' => 0,
                    'total_count' => 0
                ];
            }
            
            error_log('Hybrid Search: API URL found: ' . $api_url);
            
            // Get selected post types from settings
            $selected_post_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
            if (!is_array($selected_post_types) || empty($selected_post_types)) {
                $selected_post_types = ['post', 'page']; // Default to posts and pages
            }
            
            error_log('Hybrid Search: Selected post types to index: ' . json_encode($selected_post_types));
            
            // Use WordPress HTTP API directly instead of custom APIClient
            $request_data = [
                'force_reindex' => true,
                'post_types' => $selected_post_types
            ];
            
            $response = wp_remote_post($api_url . '/index', [
                'method' => 'POST',
                'timeout' => 300,
                'headers' => [
                    'Content-Type' => 'application/json',
                ],
                'body' => json_encode($request_data)
            ]);
            
            if (is_wp_error($response)) {
                $error_message = $response->get_error_message();
                error_log('Hybrid Search: WP HTTP Error: ' . $error_message);
                
                return [
                    'success' => false,
                    'message' => 'API request failed: ' . $error_message,
                    'indexed_count' => 0,
                    'total_count' => 0
                ];
            }
            
            $status_code = wp_remote_retrieve_response_code($response);
            $body = wp_remote_retrieve_body($response);
            $data = json_decode($body, true);
            
            error_log('Hybrid Search: API Response - Status: ' . $status_code . ', Body: ' . $body);
            
            if ($status_code >= 200 && $status_code < 300) {
                $message = isset($data['message']) ? $data['message'] : 'Content reindexed successfully';
                $documents_indexed = isset($data['documents_indexed']) ? $data['documents_indexed'] : 0;
                $processing_time = isset($data['processing_time']) ? $data['processing_time'] : 0;
                
                return [
                    'success' => true,
                    'message' => $message,
                    'indexed_count' => $documents_indexed,
                    'total_count' => $documents_indexed,
                    'processing_time' => $processing_time,
                    'api_response' => $data
                ];
            } else {
                $error_message = isset($data['message']) ? $data['message'] : 'API returned error status ' . $status_code;
                
                return [
                    'success' => false,
                    'message' => 'Railway API error: ' . $error_message,
                    'indexed_count' => 0,
                    'total_count' => 0,
                    'status_code' => $status_code
                ];
            }
            
        } catch (Exception $e) {
            error_log('Hybrid Search: Reindexing exception: ' . $e->getMessage());
            return [
                'success' => false,
                'message' => 'Reindexing failed: ' . $e->getMessage(),
                'indexed_count' => 0,
                'total_count' => 0
            ];
        }
    }
    
    /**
     * Sanitize analytics data
     * 
     * @param array $data
     * @return array
     * @since 2.0.0
     */
    private function sanitizeAnalyticsData($data) {
        return [
            'query' => sanitize_text_field($data['query'] ?? ''),
            'result_count' => (int) ($data['result_count'] ?? 0),
            'time_taken' => (float) ($data['time_taken'] ?? 0),
            'has_results' => (bool) ($data['has_results'] ?? false),
            'user_agent' => sanitize_text_field($data['user_agent'] ?? ''),
            'language' => sanitize_text_field($data['language'] ?? ''),
            'screen_resolution' => sanitize_text_field($data['screen_resolution'] ?? ''),
            'viewport_size' => sanitize_text_field($data['viewport_size'] ?? ''),
            'referrer' => esc_url_raw($data['referrer'] ?? ''),
            'session_id' => sanitize_text_field($data['session_id'] ?? ''),
            'user_id' => (int) ($data['user_id'] ?? 0),
            'device_type' => sanitize_text_field($data['device_type'] ?? ''),
            'browser_name' => sanitize_text_field($data['browser_name'] ?? ''),
            'browser_version' => sanitize_text_field($data['browser_version'] ?? ''),
            'search_method' => sanitize_text_field($data['search_method'] ?? 'ajax'),
            'filters' => sanitize_text_field($data['filters'] ?? ''),
            'sort_method' => sanitize_text_field($data['sort_method'] ?? 'relevance'),
            'results' => is_array($data['results']) ? $data['results'] : [],
        ];
    }
    
    /**
     * Sanitize CTR data
     * 
     * @param array $data
     * @return array
     * @since 2.0.0
     */
    private function sanitizeCTRData($data) {
        return [
            'search_id' => (int) ($data['search_id'] ?? 0),
            'result_id' => sanitize_text_field($data['result_id'] ?? ''),
            'result_title' => sanitize_text_field($data['result_title'] ?? ''),
            'result_url' => esc_url_raw($data['result_url'] ?? ''),
            'result_position' => (int) ($data['result_position'] ?? 0),
            'result_score' => (float) ($data['result_score'] ?? 0),
            'session_id' => sanitize_text_field($data['session_id'] ?? ''),
            'user_id' => (int) ($data['user_id'] ?? 0),
            'query' => sanitize_text_field($data['query'] ?? ''),
        ];
    }
}
