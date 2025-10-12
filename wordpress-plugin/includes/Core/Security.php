<?php
/**
 * Security Manager
 * 
 * @package SCS\HybridSearch\Core
 * @since 2.0.0
 */

namespace HybridSearch\Core;

class Security {
    
    /**
     * Nonce action prefix
     * 
     * @var string
     */
    const NONCE_PREFIX = 'hybrid_search_';
    
    /**
     * Rate limiting configuration
     * 
     * @var array
     */
    private $rate_limit_config = [
        'max_requests' => 60,
        'time_window' => 60, // seconds
        'ban_duration' => 300, // seconds
    ];
    
    /**
     * Validate nonce
     * 
     * @param string $action
     * @param string $nonce
     * @return bool
     */
    public function validateNonce($action, $nonce) {
        if (empty($nonce) || empty($action)) {
            return false;
        }
        
        return wp_verify_nonce($nonce, self::NONCE_PREFIX . $action);
    }
    
    /**
     * Create nonce
     * 
     * @param string $action
     * @return string
     */
    public function createNonce($action) {
        return wp_create_nonce(self::NONCE_PREFIX . $action);
    }
    
    /**
     * Sanitize input data
     * 
     * @param mixed $data
     * @param string $type
     * @return mixed
     */
    public function sanitizeInput($data, $type = 'text') {
        if (is_array($data)) {
            return array_map(function($item) use ($type) {
                return $this->sanitizeInput($item, $type);
            }, $data);
        }
        
        switch ($type) {
            case 'text':
                return sanitize_text_field($data);
            case 'textarea':
                return sanitize_textarea_field($data);
            case 'url':
                return esc_url_raw($data);
            case 'email':
                return sanitize_email($data);
            case 'int':
                return intval($data);
            case 'float':
                return floatval($data);
            case 'bool':
                return (bool) $data;
            case 'html':
                return wp_kses_post($data);
            case 'sql':
                return esc_sql($data);
            default:
                return sanitize_text_field($data);
        }
    }
    
    /**
     * Validate and sanitize search query
     * 
     * @param string $query
     * @return string|false
     */
    public function validateSearchQuery($query) {
        if (empty($query)) {
            return false;
        }
        
        // Sanitize the query
        $query = $this->sanitizeInput($query, 'text');
        
        // Check length
        if (strlen($query) > 255) {
            return false;
        }
        
        // Check for suspicious patterns
        if ($this->isSuspiciousQuery($query)) {
            return false;
        }
        
        return $query;
    }
    
    /**
     * Check if query contains suspicious patterns
     * 
     * @param string $query
     * @return bool
     */
    private function isSuspiciousQuery($query) {
        $suspicious_patterns = [
            '/<script/i',
            '/javascript:/i',
            '/vbscript:/i',
            '/onload=/i',
            '/onerror=/i',
            '/union\s+select/i',
            '/drop\s+table/i',
            '/insert\s+into/i',
            '/delete\s+from/i',
            '/update\s+set/i',
            '/exec\s*\(/i',
            '/eval\s*\(/i',
        ];
        
        foreach ($suspicious_patterns as $pattern) {
            if (preg_match($pattern, $query)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Validate API key
     * 
     * @param string $api_key
     * @return bool
     */
    public function validateAPIKey($api_key) {
        if (empty($api_key)) {
            return false;
        }
        
        // Check length (typical API keys are 32-128 characters)
        if (strlen($api_key) < 16 || strlen($api_key) > 256) {
            return false;
        }
        
        // Check format (alphanumeric and some special chars)
        if (!preg_match('/^[a-zA-Z0-9\-_\.]+$/', $api_key)) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Validate URL
     * 
     * @param string $url
     * @return bool
     */
    public function validateURL($url) {
        if (empty($url)) {
            return false;
        }
        
        // Check if it's a valid URL
        if (!filter_var($url, FILTER_VALIDATE_URL)) {
            return false;
        }
        
        // Only allow HTTP/HTTPS
        $parsed = parse_url($url);
        if (!isset($parsed['scheme']) || !in_array($parsed['scheme'], ['http', 'https'])) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Check rate limit for IP
     * 
     * @param string $ip
     * @return bool
     */
    public function checkRateLimit($ip = null) {
        if (empty($ip)) {
            $ip = $this->getClientIP();
        }
        
        $transient_key = 'hybrid_search_rate_limit_' . md5($ip);
        $requests = get_transient($transient_key);
        
        if ($requests === false) {
            $requests = 0;
        }
        
        if ($requests >= $this->rate_limit_config['max_requests']) {
            return false;
        }
        
        set_transient($transient_key, $requests + 1, $this->rate_limit_config['time_window']);
        return true;
    }
    
    /**
     * Get client IP address
     * 
     * @return string
     */
    public function getClientIP() {
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
     * Log security event
     * 
     * @param string $event
     * @param array $data
     */
    public function logSecurityEvent($event, $data = []) {
        $log_data = [
            'event' => $event,
            'ip' => $this->getClientIP(),
            'user_agent' => isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '',
            'timestamp' => current_time('mysql'),
            'user_id' => get_current_user_id(),
            'data' => $data,
        ];
        
        // Log to WordPress error log
        error_log('Hybrid Search Security: ' . json_encode($log_data));
        
        // Store in database for admin review
        $this->storeSecurityLog($log_data);
    }
    
    /**
     * Store security log in database
     * 
     * @param array $log_data
     */
    private function storeSecurityLog($log_data) {
        global $wpdb;
        
        $table_name = $wpdb->prefix . 'hybrid_search_security_logs';
        
        $wpdb->insert(
            $table_name,
            [
                'event' => $log_data['event'],
                'ip_address' => $log_data['ip'],
                'user_agent' => $log_data['user_agent'],
                'user_id' => $log_data['user_id'],
                'data' => json_encode($log_data['data']),
                'timestamp' => $log_data['timestamp'],
            ],
            ['%s', '%s', '%s', '%d', '%s', '%s']
        );
    }
    
    /**
     * Check if user has permission
     * 
     * @param string $capability
     * @return bool
     */
    public function userCan($capability = 'manage_options') {
        return current_user_can($capability);
    }
    
    /**
     * Escape output for display
     * 
     * @param string $output
     * @param string $type
     * @return string
     */
    public function escapeOutput($output, $type = 'html') {
        switch ($type) {
            case 'html':
                return esc_html($output);
            case 'attr':
                return esc_attr($output);
            case 'url':
                return esc_url($output);
            case 'js':
                return esc_js($output);
            default:
                return esc_html($output);
        }
    }
}
