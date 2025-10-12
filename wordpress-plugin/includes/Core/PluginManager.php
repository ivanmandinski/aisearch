<?php
/**
 * Plugin Manager
 * 
 * @package SCS\HybridSearch\Core
 * @since 2.0.0
 */

namespace HybridSearch\Core;

class PluginManager {
    
    /**
     * Plugin options
     * 
     * @var array
     */
    private $options = [];
    
    /**
     * Constructor
     */
    public function __construct() {
        $this->loadOptions();
    }
    
    /**
     * Load plugin options
     * 
     * @since 2.0.0
     */
    private function loadOptions() {
        $this->options = [
            'api_url' => get_option('hybrid_search_api_url', ''),
            'api_key' => get_option('hybrid_search_api_key', ''),
            'enabled' => get_option('hybrid_search_enabled', false),
            'max_results' => get_option('hybrid_search_max_results', 10),
            'include_answer' => get_option('hybrid_search_include_answer', false),
            'ai_instructions' => get_option('hybrid_search_ai_instructions', ''),
            'cache_duration' => get_option('hybrid_search_cache_duration', 3600),
            'enable_analytics' => get_option('hybrid_search_enable_analytics', true),
            'enable_ctr_tracking' => get_option('hybrid_search_enable_ctr_tracking', true),
            'auto_refresh_analytics' => get_option('hybrid_search_auto_refresh_analytics', true),
            'analytics_refresh_interval' => get_option('hybrid_search_analytics_refresh_interval', 30000),
        ];
    }
    
    /**
     * Get option value
     * 
     * @param string $key
     * @param mixed $default
     * @return mixed
     */
    public function getOption($key, $default = null) {
        return isset($this->options[$key]) ? $this->options[$key] : $default;
    }
    
    /**
     * Set option value
     * 
     * @param string $key
     * @param mixed $value
     * @return bool
     */
    public function setOption($key, $value) {
        $this->options[$key] = $value;
        return update_option('hybrid_search_' . $key, $value);
    }
    
    /**
     * Get all options
     * 
     * @return array
     */
    public function getOptions() {
        return $this->options;
    }
    
    /**
     * Check if plugin is enabled
     * 
     * @return bool
     */
    public function isEnabled() {
        return (bool) $this->getOption('enabled', false);
    }
    
    /**
     * Get API configuration
     * 
     * @return array
     */
    public function getAPIConfig() {
        return [
            'url' => $this->getOption('api_url'),
            'key' => $this->getOption('api_key'),
            'timeout' => 30,
            'verify_ssl' => true,
        ];
    }
    
    /**
     * Get search configuration
     * 
     * @return array
     */
    public function getSearchConfig() {
        return [
            'max_results' => (int) $this->getOption('max_results', 10),
            'include_answer' => (bool) $this->getOption('include_answer', false),
            'ai_instructions' => $this->getOption('ai_instructions', ''),
        ];
    }
    
    /**
     * Get analytics configuration
     * 
     * @return array
     */
    public function getAnalyticsConfig() {
        return [
            'enabled' => (bool) $this->getOption('enable_analytics', true),
            'ctr_tracking' => (bool) $this->getOption('enable_ctr_tracking', true),
            'auto_refresh' => (bool) $this->getOption('auto_refresh_analytics', true),
            'refresh_interval' => (int) $this->getOption('analytics_refresh_interval', 30000),
        ];
    }
    
    /**
     * Get cache configuration
     * 
     * @return array
     */
    public function getCacheConfig() {
        return [
            'duration' => (int) $this->getOption('cache_duration', 3600),
            'enabled' => true,
        ];
    }
    
    /**
     * Validate configuration
     * 
     * @return array Validation results
     */
    public function validateConfig() {
        $errors = [];
        $warnings = [];
        
        // Required fields
        if (empty($this->getOption('api_url'))) {
            $errors[] = __('API URL is required', 'scs-hybrid-search');
        }
        
        // Optional but recommended
        if (empty($this->getOption('api_key'))) {
            $warnings[] = __('API Key is recommended for security', 'scs-hybrid-search');
        }
        
        // Validate URL format
        if (!empty($this->getOption('api_url')) && !filter_var($this->getOption('api_url'), FILTER_VALIDATE_URL)) {
            $errors[] = __('API URL must be a valid URL', 'scs-hybrid-search');
        }
        
        // Validate numeric options
        $numeric_options = ['max_results', 'cache_duration', 'analytics_refresh_interval'];
        foreach ($numeric_options as $option) {
            $value = $this->getOption($option);
            if (!is_numeric($value) || $value < 0) {
                $errors[] = sprintf(__('%s must be a positive number', 'scs-hybrid-search'), $option);
            }
        }
        
        return [
            'valid' => empty($errors),
            'errors' => $errors,
            'warnings' => $warnings,
        ];
    }
}
