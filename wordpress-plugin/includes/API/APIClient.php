<?php
/**
 * API Client
 * 
 * @package SCS\HybridSearch\API
 * @since 2.0.0
 */

namespace HybridSearch\API;

class APIClient {
    
    /**
     * API configuration
     * 
     * @var array
     */
    private $config;
    
    /**
     * Default headers
     * 
     * @var array
     */
    private $default_headers;
    
    /**
     * Constructor
     * 
     * @param array $config
     */
    public function __construct($config = []) {
        $this->config = wp_parse_args($config, [
            'url' => '',
            'key' => '',
            'timeout' => 30,
            'verify_ssl' => true,
            'user_agent' => 'WordPress Hybrid Search Plugin/' . HYBRID_SEARCH_VERSION,
        ]);
        
        $this->default_headers = [
            'Content-Type' => 'application/json',
            'User-Agent' => $this->config['user_agent'],
            'Accept' => 'application/json',
        ];
        
        if (!empty($this->config['key'])) {
            $this->default_headers['Authorization'] = 'Bearer ' . $this->config['key'];
        }
    }
    
    /**
     * Make GET request
     * 
     * @param string $endpoint
     * @param array $params
     * @param array $headers
     * @return array
     */
    public function get($endpoint, $params = [], $headers = []) {
        $url = $this->buildUrl($endpoint, $params);
        $request_headers = array_merge($this->default_headers, $headers);
        
        return $this->makeRequest('GET', $url, null, $request_headers);
    }
    
    /**
     * Make POST request
     * 
     * @param string $endpoint
     * @param array $data
     * @param array $headers
     * @return array
     */
    public function post($endpoint, $data = [], $headers = []) {
        $url = $this->buildUrl($endpoint);
        $request_headers = array_merge($this->default_headers, $headers);
        
        return $this->makeRequest('POST', $url, $data, $request_headers);
    }
    
    /**
     * Make PUT request
     * 
     * @param string $endpoint
     * @param array $data
     * @param array $headers
     * @return array
     */
    public function put($endpoint, $data = [], $headers = []) {
        $url = $this->buildUrl($endpoint);
        $request_headers = array_merge($this->default_headers, $headers);
        
        return $this->makeRequest('PUT', $url, $data, $request_headers);
    }
    
    /**
     * Make DELETE request
     * 
     * @param string $endpoint
     * @param array $headers
     * @return array
     */
    public function delete($endpoint, $headers = []) {
        $url = $this->buildUrl($endpoint);
        $request_headers = array_merge($this->default_headers, $headers);
        
        return $this->makeRequest('DELETE', $url, null, $request_headers);
    }
    
    /**
     * Make HTTP request
     * 
     * @param string $method
     * @param string $url
     * @param array|null $data
     * @param array $headers
     * @return array
     */
    private function makeRequest($method, $url, $data = null, $headers = []) {
        $args = [
            'method' => $method,
            'timeout' => $this->config['timeout'],
            'headers' => $headers,
            'sslverify' => $this->config['verify_ssl'],
            'redirection' => 5,
            'httpversion' => '1.1',
            'blocking' => true,
            'cookies' => [],
        ];
        
        if ($data !== null && in_array($method, ['POST', 'PUT', 'PATCH'])) {
            $args['body'] = json_encode($data);
        }
        
        // Add request logging
        $this->logRequest($method, $url, $data, $headers);
        
        $response = wp_remote_request($url, $args);
        
        return $this->handleResponse($response, $method, $url);
    }
    
    /**
     * Handle HTTP response
     * 
     * @param array|\WP_Error $response
     * @param string $method
     * @param string $url
     * @return array
     */
    private function handleResponse($response, $method, $url) {
        if (is_wp_error($response)) {
            $error_message = $response->get_error_message();
            $this->logError($method, $url, $error_message);
            
            return [
                'success' => false,
                'error' => $error_message,
                'data' => null,
                'status_code' => 0,
            ];
        }
        
        $status_code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        $headers = wp_remote_retrieve_headers($response);
        
        // Parse JSON response
        $data = json_decode($body, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            $this->logError($method, $url, 'Invalid JSON response: ' . json_last_error_msg());
            
            return [
                'success' => false,
                'error' => 'Invalid JSON response',
                'data' => null,
                'status_code' => $status_code,
                'raw_body' => $body,
            ];
        }
        
        $success = $status_code >= 200 && $status_code < 300;
        
        // Log response
        $this->logResponse($method, $url, $status_code, $data, $success);
        
        return [
            'success' => $success,
            'error' => $success ? null : $this->getErrorMessage($status_code, $data),
            'data' => $data,
            'status_code' => $status_code,
            'headers' => $headers,
        ];
    }
    
    /**
     * Build URL with endpoint and parameters
     * 
     * @param string $endpoint
     * @param array $params
     * @return string
     */
    private function buildUrl($endpoint, $params = []) {
        $url = rtrim($this->config['url'], '/') . '/' . ltrim($endpoint, '/');
        
        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }
        
        return $url;
    }
    
    /**
     * Get error message from response
     * 
     * @param int $status_code
     * @param array $data
     * @return string
     */
    private function getErrorMessage($status_code, $data) {
        if (isset($data['error'])) {
            return $data['error'];
        }
        
        if (isset($data['message'])) {
            return $data['message'];
        }
        
        switch ($status_code) {
            case 400:
                return 'Bad Request';
            case 401:
                return 'Unauthorized';
            case 403:
                return 'Forbidden';
            case 404:
                return 'Not Found';
            case 429:
                return 'Too Many Requests';
            case 500:
                return 'Internal Server Error';
            case 502:
                return 'Bad Gateway';
            case 503:
                return 'Service Unavailable';
            default:
                return 'HTTP Error ' . $status_code;
        }
    }
    
    /**
     * Test API connection
     * 
     * @return array
     */
    public function testConnection() {
        $start_time = microtime(true);
        
        try {
            $response = $this->get('health');
            $end_time = microtime(true);
            $response_time = round(($end_time - $start_time) * 1000, 2);
            
            if ($response['success']) {
                return [
                    'success' => true,
                    'message' => 'API connection successful',
                    'response_time' => $response_time,
                    'status_code' => $response['status_code'],
                    'data' => $response['data'],
                ];
            } else {
                return [
                    'success' => false,
                    'message' => 'API connection failed: ' . $response['error'],
                    'response_time' => $response_time,
                    'status_code' => $response['status_code'],
                ];
            }
        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => 'API connection failed: ' . $e->getMessage(),
                'response_time' => 0,
                'status_code' => 0,
            ];
        }
    }
    
    /**
     * Update configuration
     * 
     * @param array $config
     */
    public function updateConfig($config) {
        $this->config = wp_parse_args($config, $this->config);
        
        // Update authorization header if key changed
        if (isset($config['key'])) {
            if (!empty($config['key'])) {
                $this->default_headers['Authorization'] = 'Bearer ' . $config['key'];
            } else {
                unset($this->default_headers['Authorization']);
            }
        }
    }
    
    /**
     * Get current configuration
     * 
     * @return array
     */
    public function getConfig() {
        return $this->config;
    }
    
    /**
     * Log request
     * 
     * @param string $method
     * @param string $url
     * @param array|null $data
     * @param array $headers
     */
    private function logRequest($method, $url, $data, $headers) {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log(sprintf(
                'Hybrid Search API Request: %s %s - Data: %s - Headers: %s',
                $method,
                $url,
                $data ? json_encode($data) : 'null',
                json_encode($headers)
            ));
        }
    }
    
    /**
     * Log response
     * 
     * @param string $method
     * @param string $url
     * @param int $status_code
     * @param array $data
     * @param bool $success
     */
    private function logResponse($method, $url, $status_code, $data, $success) {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log(sprintf(
                'Hybrid Search API Response: %s %s - Status: %d - Success: %s - Data: %s',
                $method,
                $url,
                $status_code,
                $success ? 'true' : 'false',
                json_encode($data)
            ));
        }
    }
    
    /**
     * Log error
     * 
     * @param string $method
     * @param string $url
     * @param string $error
     */
    private function logError($method, $url, $error) {
        error_log(sprintf(
            'Hybrid Search API Error: %s %s - Error: %s',
            $method,
            $url,
            $error
        ));
    }
}
