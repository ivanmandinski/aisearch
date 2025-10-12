<?php
/**
 * Search API
 * 
 * Handles all search-related API interactions with the hybrid search backend.
 * Provides a clean interface for performing searches and managing search results.
 * 
 * @package SCS\HybridSearch\API
 * @since 2.0.0
 */

namespace HybridSearch\API;

class SearchAPI {
    
    /**
     * API client instance
     * 
     * @var APIClient
     */
    private $client;
    
    /**
     * Search configuration
     * 
     * @var array
     */
    private $config;
    
    /**
     * Smart cache service
     * 
     * @var \HybridSearch\Services\SmartCacheService
     */
    private $cache_service;
    
    /**
     * Constructor
     * 
     * @param APIClient $client
     * @param array $config
     * @since 2.0.0
     */
    public function __construct(APIClient $client, $config = []) {
        $this->client = $client;
        $this->config = wp_parse_args($config, [
            'max_results' => 10,
            'include_answer' => false,
            'ai_instructions' => '',
            'timeout' => 30,
        ]);
        
        // Initialize smart cache
        $this->cache_service = new \HybridSearch\Services\SmartCacheService();
    }
    
    /**
     * Perform search
     * 
     * @param string $query The search query
     * @param array $options Additional search options
     * @return array Search results and metadata
     * @since 2.0.0
     */
    public function search($query, $options = []) {
        // Validate input
        if (empty($query) || !is_string($query)) {
            return [
                'success' => false,
                'error' => 'Invalid search query',
                'results' => [],
                'metadata' => [],
            ];
        }
        
        // Sanitize and validate query
        $query = sanitize_text_field($query);
        if (strlen($query) > 255) {
            return [
                'success' => false,
                'error' => 'Search query too long (max 255 characters)',
                'results' => [],
                'metadata' => [],
            ];
        }
        
        // Merge options with defaults
        $search_options = wp_parse_args($options, [
            'limit' => $this->config['max_results'],
            'include_answer' => $this->config['include_answer'],
            'ai_instructions' => $this->config['ai_instructions'],
        ]);
        
        // Check smart cache first
        $cached_result = $this->cache_service->get($query, $search_options);
        if ($cached_result !== false) {
            return $cached_result;
        }
        
        // Prepare request data
        $request_data = [
            'query' => $query,
            'limit' => (int) $search_options['limit'],
            'include_answer' => (bool) $search_options['include_answer'],
            'ai_instructions' => sanitize_textarea_field($search_options['ai_instructions']),
            // AI Reranking parameters
            'enable_ai_reranking' => isset($search_options['enable_ai_reranking']) ? (bool) $search_options['enable_ai_reranking'] : true,
            'ai_weight' => isset($search_options['ai_weight']) ? (float) $search_options['ai_weight'] : 0.7,
            'ai_reranking_instructions' => isset($search_options['ai_reranking_instructions']) ? sanitize_textarea_field($search_options['ai_reranking_instructions']) : '',
        ];
        
        // Log request data for debugging
        error_log('Hybrid Search: Request data being sent to Railway API: ' . json_encode($request_data));
        
        // Record start time for performance tracking
        $start_time = microtime(true);
        
        try {
            // Make API request
            $response = $this->client->post('search', $request_data);
            
            // Calculate response time
            $end_time = microtime(true);
            $response_time = round(($end_time - $start_time) * 1000, 2);
            
            if ($response['success']) {
                // Process successful response
                $result = $this->processSearchResponse($response['data'], $query, $response_time);
                
                // Cache the result using smart cache (variable TTL)
                $this->cache_service->set($query, $search_options, $result, $result['metadata'] ?? []);
                
                return $result;
            } else {
                // Handle API error
                return [
                    'success' => false,
                    'error' => $response['error'] ?: 'Search request failed',
                    'results' => [],
                    'metadata' => [
                        'query' => $query,
                        'response_time' => $response_time,
                        'status_code' => $response['status_code'],
                    ],
                ];
            }
        } catch (\Exception $e) {
            // Handle unexpected errors
            $end_time = microtime(true);
            $response_time = round(($end_time - $start_time) * 1000, 2);
            
            return [
                'success' => false,
                'error' => 'Search request failed: ' . $e->getMessage(),
                'results' => [],
                'metadata' => [
                    'query' => $query,
                    'response_time' => $response_time,
                    'exception' => $e->getMessage(),
                ],
            ];
        }
    }
    
    /**
     * Process search response
     * 
     * @param array $data API response data
     * @param string $query Original search query
     * @param float $response_time Response time in milliseconds
     * @return array Processed search results
     * @since 2.0.0
     */
    private function processSearchResponse($data, $query, $response_time) {
        // Extract results from response
        $results = isset($data['results']) ? $data['results'] : [];
        $metadata = isset($data['metadata']) ? $data['metadata'] : [];
        
        // Extract answer from metadata (new format) or root level (old format)
        $answer = '';
        if (isset($metadata['answer']) && !empty($metadata['answer'])) {
            $answer = $metadata['answer'];
        } elseif (isset($data['answer']) && !empty($data['answer'])) {
            $answer = $data['answer'];
        }
        
        // Validate and sanitize results
        $processed_results = $this->processResults($results);
        
        // Prepare metadata (flatten the structure for easier access)
        $search_metadata = [
            'query' => $query,
            'total_results' => count($processed_results),
            'response_time' => $response_time,
            'has_answer' => !empty($answer),
            'answer' => $answer,  // Now contains the actual answer from Railway API
            'raw_metadata' => $metadata,  // Keep original metadata for reference
            'timestamp' => current_time('mysql'),
        ];
        
        return [
            'success' => true,
            'results' => $processed_results,
            'metadata' => $search_metadata,
        ];
    }
    
    /**
     * Process and validate search results
     * 
     * @param array $results Raw results from API
     * @return array Processed and validated results
     * @since 2.0.0
     */
    private function processResults($results) {
        if (!is_array($results)) {
            return [];
        }
        
        $processed = [];
        
        foreach ($results as $index => $result) {
            // Validate required fields
            if (!isset($result['title']) || !isset($result['url'])) {
                continue;
            }
            
            // Sanitize and process result
            $processed_result = [
                'id' => $this->generateResultId($result, $index),
                'title' => sanitize_text_field($result['title']),
                'url' => esc_url_raw($result['url']),
                'excerpt' => isset($result['excerpt']) ? sanitize_textarea_field($result['excerpt']) : '',
                'score' => isset($result['score']) ? (float) $result['score'] : 0.0,
                'position' => $index + 1,
                'type' => isset($result['type']) ? sanitize_text_field($result['type']) : 'post',
                'date' => isset($result['date']) ? sanitize_text_field($result['date']) : '',
                'author' => isset($result['author']) ? sanitize_text_field($result['author']) : '',
                'categories' => isset($result['categories']) ? array_map('sanitize_text_field', (array) $result['categories']) : [],
                'tags' => isset($result['tags']) ? array_map('sanitize_text_field', (array) $result['tags']) : [],
                'featured_image' => isset($result['featured_image']) ? esc_url_raw($result['featured_image']) : '',
                'meta' => isset($result['meta']) ? $result['meta'] : [],
            ];
            
            $processed[] = $processed_result;
        }
        
        return $processed;
    }
    
    /**
     * Generate unique result ID
     * 
     * @param array $result
     * @param int $index
     * @return string
     * @since 2.0.0
     */
    private function generateResultId($result, $index) {
        // Try to use existing ID
        if (isset($result['id']) && !empty($result['id'])) {
            return sanitize_text_field($result['id']);
        }
        
        // Generate ID from URL and index
        $url_hash = md5($result['url']);
        return 'result_' . $url_hash . '_' . $index;
    }
    
    /**
     * Test API connection
     * 
     * @return array Test results
     * @since 2.0.0
     */
    public function testConnection() {
        return $this->client->testConnection();
    }
    
    /**
     * Get API health status
     * 
     * @return array Health status
     * @since 2.0.0
     */
    public function getHealthStatus() {
        $response = $this->client->get('health');
        
        if ($response['success']) {
            return [
                'status' => 'healthy',
                'data' => $response['data'],
                'response_time' => $response['response_time'] ?? 0,
            ];
        } else {
            return [
                'status' => 'unhealthy',
                'error' => $response['error'],
                'status_code' => $response['status_code'],
            ];
        }
    }
    
    /**
     * Get search suggestions
     * 
     * @param string $query Partial search query
     * @param int $limit Number of suggestions
     * @return array Search suggestions
     * @since 2.0.0
     */
    public function getSuggestions($query, $limit = 5) {
        if (empty($query) || strlen($query) < 2) {
            return [
                'success' => false,
                'error' => 'Query too short for suggestions',
                'suggestions' => [],
            ];
        }
        
        $response = $this->client->get('suggestions', [
            'q' => sanitize_text_field($query),
            'limit' => (int) $limit,
        ]);
        
        if ($response['success']) {
            $suggestions = isset($response['data']['suggestions']) ? $response['data']['suggestions'] : [];
            
            // Sanitize suggestions
            $suggestions = array_map('sanitize_text_field', $suggestions);
            
            return [
                'success' => true,
                'suggestions' => $suggestions,
            ];
        } else {
            return [
                'success' => false,
                'error' => $response['error'],
                'suggestions' => [],
            ];
        }
    }
    
    /**
     * Update search configuration
     * 
     * @param array $config New configuration
     * @since 2.0.0
     */
    public function updateConfig($config) {
        $this->config = wp_parse_args($config, $this->config);
    }
    
    /**
     * Get current configuration
     * 
     * @return array Current configuration
     * @since 2.0.0
     */
    public function getConfig() {
        return $this->config;
    }
    
    /**
     * Batch search multiple queries
     * 
     * @param array $queries Array of search queries
     * @param array $options Search options
     * @return array Batch search results
     * @since 2.0.0
     */
    public function batchSearch($queries, $options = []) {
        if (!is_array($queries) || empty($queries)) {
            return [
                'success' => false,
                'error' => 'Invalid queries array',
                'results' => [],
            ];
        }
        
        $batch_results = [];
        $errors = [];
        
        foreach ($queries as $query) {
            $result = $this->search($query, $options);
            $batch_results[$query] = $result;
            
            if (!$result['success']) {
                $errors[] = $query . ': ' . $result['error'];
            }
        }
        
        return [
            'success' => empty($errors),
            'results' => $batch_results,
            'errors' => $errors,
            'total_queries' => count($queries),
            'successful_queries' => count($queries) - count($errors),
            'failed_queries' => count($errors),
        ];
    }
    
    /**
     * Get search statistics
     * 
     * @return array Search statistics
     * @since 2.0.0
     */
    public function getSearchStats() {
        $response = $this->client->get('stats');
        
        if ($response['success']) {
            return [
                'success' => true,
                'stats' => $response['data'],
            ];
        } else {
            return [
                'success' => false,
                'error' => $response['error'],
                'stats' => [],
            ];
        }
    }
}
