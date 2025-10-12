<?php
/**
 * Frontend Manager
 * 
 * Handles frontend functionality including search form rendering and asset management.
 * 
 * @package HybridSearch\Frontend
 * @since 2.0.0
 */

namespace HybridSearch\Frontend;

use HybridSearch\API\SearchAPI;

class FrontendManager {
    
    /**
     * Search API
     * 
     * @var SearchAPI
     */
    private $search_api;
    
    /**
     * Constructor
     * 
     * @param SearchAPI $search_api
     */
    public function __construct(SearchAPI $search_api) {
        $this->search_api = $search_api;
    }
    
    /**
     * Register WordPress hooks
     * 
     * @since 2.0.0
     */
    public function registerHooks() {
        add_action('wp_enqueue_scripts', [$this, 'enqueueAssets']);
        add_action('wp_footer', [$this, 'addInlineScripts']);
        add_filter('get_search_form', [$this, 'customSearchForm']);
        add_shortcode('hybrid_search_form', [$this, 'searchFormShortcode']);
        
        // Intercept search requests when hybrid search is enabled
        add_action('template_redirect', [$this, 'interceptSearchRequest']);
        add_filter('posts_results', [$this, 'replaceSearchResults'], 10, 2);
        
        // More aggressive form replacement
        add_action('wp_head', [$this, 'injectSearchFormCSS']);
        add_action('wp_footer', [$this, 'injectSearchFormJS']);
    }
    
    /**
     * Enqueue frontend assets
     * 
     * @since 2.0.0
     */
    public function enqueueAssets() {
        // Only load on pages that might have search
        if (!$this->shouldLoadAssets()) {
            return;
        }
        
        // Enqueue CSS (Original + Enhanced)
        wp_enqueue_style(
            'hybrid-search',
            HYBRID_SEARCH_PLUGIN_URL . 'assets/css/hybrid-search.css',
            [],
            HYBRID_SEARCH_VERSION
        );
        
        wp_enqueue_style(
            'hybrid-search-enhanced',
            HYBRID_SEARCH_PLUGIN_URL . 'assets/css/hybrid-search-enhanced.css',
            ['hybrid-search'],
            HYBRID_SEARCH_VERSION
        );
        
        // SCS Engineers brand-specific theme
        wp_enqueue_style(
            'hybrid-search-scs-theme',
            HYBRID_SEARCH_PLUGIN_URL . 'assets/css/scs-brand-theme.css',
            ['hybrid-search-enhanced'],
            HYBRID_SEARCH_VERSION
        );
        
        // Enqueue JavaScript modules
        wp_enqueue_script(
            'hybrid-search-ui',
            HYBRID_SEARCH_PLUGIN_URL . 'assets/js/hybrid-search-ui.js',
            ['jquery'],
            HYBRID_SEARCH_VERSION,
            true
        );
        
        wp_enqueue_script(
            'hybrid-search-autocomplete',
            HYBRID_SEARCH_PLUGIN_URL . 'assets/js/hybrid-search-autocomplete.js',
            ['jquery', 'hybrid-search-ui'],
            HYBRID_SEARCH_VERSION,
            true
        );
        
        wp_enqueue_script(
            'hybrid-search-integration',
            HYBRID_SEARCH_PLUGIN_URL . 'assets/js/hybrid-search-integration.js',
            ['jquery', 'hybrid-search-ui', 'hybrid-search-autocomplete'],
            HYBRID_SEARCH_VERSION,
            true
        );
        
        // Pass configuration to JavaScript
        wp_localize_script('hybrid-search-ui', 'hybridSearch', [
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'apiUrl' => get_option('hybrid_search_api_url', ''),
            'maxResults' => get_option('hybrid_search_max_results', 10),
            'includeAnswer' => get_option('hybrid_search_include_answer', false),
            'nonce' => wp_create_nonce('hybrid_search_nonce'),
            'enableVoiceSearch' => true,
            'enableKeyboardShortcuts' => true
        ]);
    }
    
    /**
     * Add inline scripts
     * 
     * @since 2.0.0
     */
    public function addInlineScripts() {
        if (!$this->shouldLoadAssets()) {
            return;
        }
        
        ?>
        <script type="text/javascript">
        // Hybrid Search initialization
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize search functionality if the instance exists
            if (window.hybridSearchInstance) {
                // Additional initialization can be added here
                console.log('Hybrid Search initialized successfully');
            }
        });
        
        // Global functions for debugging (only in debug mode)
        <?php if (defined('WP_DEBUG') && WP_DEBUG): ?>
        window.testHybridSearch = function() {
            console.log('Testing Hybrid Search...');
            if (window.hybridSearchInstance) {
                window.hybridSearchInstance.performSearch('test query');
            } else {
                console.error('Hybrid Search instance not found');
            }
        };
        <?php endif; ?>
        </script>
        <?php
    }
    
    /**
     * Custom search form
     * 
     * @param string $form Original search form
     * @return string Modified search form
     * @since 2.0.0
     */
    public function customSearchForm($form) {
        // Always return custom form for now - we'll handle enabling/disabling in the search logic
        return $this->renderSearchForm();
    }
    
    /**
     * Search form shortcode
     * 
     * @param array $atts Shortcode attributes
     * @return string Search form HTML
     * @since 2.0.0
     */
    public function searchFormShortcode($atts) {
        $atts = shortcode_atts([
            'placeholder' => 'Search...',
            'button_text' => 'Search',
            'show_clear' => 'true',
            'class' => '',
        ], $atts);
        
        return $this->renderSearchForm($atts);
    }
    
    /**
     * Render search form
     * 
     * @param array $options Form options
     * @return string Search form HTML
     * @since 2.0.0
     */
    public function renderSearchForm($options = []) {
        $defaults = [
            'placeholder' => 'Search...',
            'button_text' => 'Search',
            'show_clear' => true,
            'class' => '',
        ];
        
        $options = wp_parse_args($options, $defaults);
        
        ob_start();
        ?>
        <div class="hybrid-search-container <?php echo esc_attr($options['class']); ?>">
            <form class="hybrid-search-form" method="get" action="<?php echo esc_url(home_url('/')); ?>">
                <input type="text" 
                       name="s" 
                       class="hybrid-search-input" 
                       placeholder="<?php echo esc_attr($options['placeholder']); ?>"
                       value="<?php echo esc_attr(get_search_query()); ?>"
                       autocomplete="off"
                       spellcheck="false">
                
                <?php if ($options['show_clear']): ?>
                    <button type="button" class="hybrid-search-clear" aria-label="Clear search">×</button>
                <?php endif; ?>
                
                <button type="submit" class="hybrid-search-button hybrid-search-button--search">
                    <?php echo esc_html($options['button_text']); ?>
                </button>
                
                <input type="hidden" name="hybrid_search" value="1">
            </form>
            
            <!-- Search Filters -->
            <div class="hybrid-search-filters">
                <div class="hybrid-search-filters-header">
                    <div class="hybrid-search-filters-title">
                        <span>🎛️</span>
                        <span>Filters</span>
                    </div>
                    <button type="button" class="hybrid-search-filters-toggle" onclick="toggleSearchFilters()">
                        Hide Filters
                    </button>
                </div>
                
                <div class="hybrid-search-filters-content">
                    <div class="hybrid-search-filter-group">
                        <label class="hybrid-search-filter-label">Content Type</label>
                        <select class="hybrid-search-filter-select" id="filter-type">
                            <option value="">All Types</option>
                            <option value="post">Posts</option>
                            <option value="page">Pages</option>
                        </select>
                    </div>
                    
                    <div class="hybrid-search-filter-group">
                        <label class="hybrid-search-filter-label">Date Range</label>
                        <select class="hybrid-search-filter-select" id="filter-date">
                            <option value="">Any Time</option>
                            <option value="day">Last 24 Hours</option>
                            <option value="week">Last Week</option>
                            <option value="month">Last Month</option>
                            <option value="year">Last Year</option>
                        </select>
                    </div>
                    
                    <div class="hybrid-search-filter-group">
                        <label class="hybrid-search-filter-label">Sort By</label>
                        <select class="hybrid-search-filter-select" id="filter-sort">
                            <option value="relevance">Relevance</option>
                            <option value="date-desc">Newest First</option>
                            <option value="date-asc">Oldest First</option>
                            <option value="title-asc">Title A-Z</option>
                        </select>
                    </div>
                    
                    <div class="hybrid-search-filter-group">
                        <label class="hybrid-search-filter-label">Results Per Page</label>
                        <select class="hybrid-search-filter-select" id="filter-limit">
                            <option value="10">10 Results</option>
                            <option value="25">25 Results</option>
                            <option value="50">50 Results</option>
                        </select>
                    </div>
                    
                    <div class="hybrid-search-filters-actions">
                        <button type="button" class="hybrid-search-filter-apply" onclick="applySearchFilters()">
                            Apply Filters
                        </button>
                        <button type="button" class="hybrid-search-filter-reset" onclick="resetSearchFilters()">
                            Reset All
                        </button>
                    </div>
                    
                    <div class="hybrid-search-active-filters" id="active-filters"></div>
                </div>
            </div>
            
            <div class="hybrid-search-results"></div>
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Check if assets should be loaded
     * 
     * @return bool True if assets should be loaded
     * @since 2.0.0
     */
    private function shouldLoadAssets() {
        // Don't load if hybrid search is disabled
        if (!get_option('hybrid_search_enabled', false)) {
            return false;
        }
        
        // Load on search pages
        if (is_search()) {
            return true;
        }
        
        // Load on home page
        if (is_home() || is_front_page()) {
            return true;
        }
        
        // Load on pages with any hybrid search shortcode
        global $post;
        if ($post && (
            has_shortcode($post->post_content, 'hybrid_search') ||
            has_shortcode($post->post_content, 'hybrid_search_form') ||
            has_shortcode($post->post_content, 'hybrid_search_results')
        )) {
            return true;
        }
        
        // Load on pages with search form in sidebar/widgets
        if (is_active_sidebar('sidebar-1') || is_active_sidebar('sidebar-2')) {
            return true;
        }
        
        // Load by default for maximum compatibility
        return true;
    }
    
    /**
     * Check if custom form should be used
     * 
     * @return bool True if custom form should be used
     * @since 2.0.0
     */
    private function shouldUseCustomForm() {
        // Don't replace forms in admin or other specific contexts
        if (is_admin() || is_feed() || is_trackback()) {
            return false;
        }
        
        // Replace form on all frontend pages when plugin is enabled
        return apply_filters('hybrid_search_use_custom_form', true);
    }
    
    /**
     * Get search results template
     * 
     * @param array $results Search results
     * @return string Results HTML
     * @since 2.0.0
     */
    public function renderSearchResults($results, $ai_answer = null) {
        if (empty($results)) {
            return $this->renderNoResults();
        }
        
        ob_start();
        ?>
        <div class="hybrid-search-results">
            <?php if (!empty($ai_answer) && get_option('hybrid_search_show_ai_answer', false)): ?>
                <?php echo $this->renderAIAnswer($ai_answer); ?>
            <?php endif; ?>
            
            <div class="hybrid-search-results-header">
                <div class="hybrid-search-results-count">
                    Found <?php echo count($results); ?> result<?php echo count($results) !== 1 ? 's' : ''; ?>
                </div>
            </div>
            
            <div class="hybrid-search-results-list">
                <?php foreach ($results as $index => $result): ?>
                    <?php echo $this->renderSearchResult($result, $index + 1); ?>
                <?php endforeach; ?>
            </div>
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Render AI answer
     * 
     * @param string $ai_answer AI generated answer
     * @return string AI answer HTML
     * @since 2.2.1
     */
    public function renderAIAnswer($ai_answer) {
        if (empty($ai_answer)) {
            return '';
        }
        
        // Check if answer is long enough to need truncation (more than 200 characters)
        $needs_truncation = strlen($ai_answer) > 200;
        
        ob_start();
        ?>
        <div class="hybrid-search-ai-answer">
            <div class="hybrid-search-ai-answer-header">
                <span class="hybrid-search-ai-answer-icon">🤖</span>
                <span>AI Answer</span>
            </div>
            <div class="hybrid-search-ai-answer-content<?php echo $needs_truncation ? ' collapsed' : ''; ?>">
                <p><?php echo esc_html($ai_answer); ?></p>
            </div>
            
            <?php if ($needs_truncation): ?>
            <button class="hybrid-search-ai-answer-toggle" onclick="toggleAIAnswer(this)">
                <span>Show more</span>
                <span class="hybrid-search-ai-answer-toggle-icon">▼</span>
            </button>
            <?php endif; ?>
        </div>
        <?php
        return ob_get_clean();
    }

    /**
     * Render single search result
     * 
     * @param array $result Search result data
     * @param int $position Result position
     * @return string Result HTML
     * @since 2.0.0
     */
    public function renderSearchResult($result, $position = 1) {
        ob_start();
        ?>
        <article class="hybrid-search-result" data-result-id="<?php echo esc_attr($result['id']); ?>" data-position="<?php echo esc_attr($position); ?>">
            <h3 class="hybrid-search-result-title">
                <a href="<?php echo esc_url($result['url']); ?>" 
                   data-result-id="<?php echo esc_attr($result['id']); ?>"
                   data-title="<?php echo esc_attr($result['title']); ?>"
                   data-url="<?php echo esc_url($result['url']); ?>"
                   data-position="<?php echo esc_attr($position); ?>"
                   data-score="<?php echo esc_attr($result['score'] ?? 0); ?>">
                    <?php echo esc_html($result['title']); ?>
                </a>
            </h3>
            
            <?php if (!empty($result['excerpt'])): ?>
                <div class="hybrid-search-result-excerpt">
                    <?php echo esc_html($this->cleanExcerptText($result['excerpt'])); ?>
                </div>
            <?php endif; ?>
            
            <div class="hybrid-search-result-meta">
                <?php if (get_option('hybrid_search_show_score', false) && isset($result['score'])): ?>
                    <span class="hybrid-search-result-score">
                        Score: <?php echo esc_html(round($result['score'] * 100, 1)); ?>%
                    </span>
                <?php endif; ?>
                
                <?php if (get_option('hybrid_search_show_type', true) && !empty($result['type'])): ?>
                    <span class="hybrid-search-result-type">
                        <?php echo esc_html(ucfirst($result['type'])); ?>
                    </span>
                <?php endif; ?>
                
                <?php if (get_option('hybrid_search_show_date', true) && !empty($result['date'])): ?>
                    <span class="hybrid-search-result-date">
                        <?php echo esc_html(date('M j, Y', strtotime($result['date']))); ?>
                    </span>
                <?php endif; ?>
                
                <?php if (get_option('hybrid_search_show_author', false) && !empty($result['author'])): ?>
                    <span class="hybrid-search-result-author">
                        By <?php echo esc_html($result['author']); ?>
                    </span>
                <?php endif; ?>
            </div>
        </article>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Render no results message
     * 
     * @return string No results HTML
     * @since 2.0.0
     */
    public function renderNoResults() {
        ob_start();
        ?>
        <div class="hybrid-search-empty">
            <div class="hybrid-search-empty-icon">🔍</div>
            <h3 class="hybrid-search-empty-title">No results found</h3>
            <p class="hybrid-search-empty-description">
                Try adjusting your search terms or check the spelling.
            </p>
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Inject search form CSS
     * 
     * @since 2.1.2
     */
    public function injectSearchFormCSS() {
        ?>
        <style type="text/css">
        /* Hide original WordPress search forms and show hybrid search form */
        .search-form,
        form[role="search"],
        #searchform,
        .widget_search form,
        .searchform {
            display: none !important;
        }
        
        /* Hybrid Search Form Styles */
        .hybrid-search-container {
            display: block !important;
            max-width: 100%;
            margin: 0 auto;
        }
        
        .hybrid-search-form {
            display: flex;
            align-items: center;
            gap: 10px;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 25px;
            padding: 8px 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .hybrid-search-form:focus-within {
            border-color: #007cba;
            box-shadow: 0 0 0 2px rgba(0,124,186,0.2);
        }
        
        .hybrid-search-input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 16px;
            padding: 8px 0;
            background: transparent;
        }
        
        .hybrid-search-clear {
            background: none;
            border: none;
            font-size: 18px;
            color: #999;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .hybrid-search-clear:hover {
            color: #666;
        }
        
        .hybrid-search-button {
            background: #007cba;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s ease;
        }
        
        .hybrid-search-button:hover {
            background: #005a87;
        }
        
        /* Search Results Container */
        .hybrid-search-results {
            margin-top: 40px;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
            padding: 0 20px;
        }
        
        .hybrid-search-results-header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f8f9fa;
            position: relative;
        }
        
        .hybrid-search-results-header::after {
            content: '';
            position: absolute;
            bottom: -3px;
            left: 0;
            width: 60px;
            height: 3px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 2px;
        }
        
        .hybrid-search-results-count {
            font-size: 18px;
            color: #495057;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .hybrid-search-results-count::before {
            content: '🔍';
            font-size: 20px;
        }
        
        .hybrid-search-results-list {
            display: flex;
            flex-direction: column;
            gap: 30px;
        }
        
        /* Individual Search Result */
        .hybrid-search-result {
            background: #fff;
            border: 1px solid #e9ecef;
            border-radius: 16px;
            padding: 30px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            position: relative;
            overflow: hidden;
        }
        
        .hybrid-search-result::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transform: scaleY(0);
            transition: transform 0.3s ease;
        }
        
        .hybrid-search-result:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
            border-color: #667eea;
        }
        
        .hybrid-search-result:hover::before {
            transform: scaleY(1);
        }
        
        .hybrid-search-result-title {
            margin: 0 0 15px 0;
            font-size: 22px;
            line-height: 1.3;
            font-weight: 700;
        }
        
        .hybrid-search-result-title a {
            color: #1a1a1a;
            text-decoration: none;
            transition: all 0.2s ease;
            position: relative;
        }
        
        .hybrid-search-result-title a:hover {
            color: #667eea;
            text-decoration: none;
        }
        
        .hybrid-search-result-title a::after {
            content: '↗';
            opacity: 0;
            margin-left: 8px;
            font-size: 16px;
            transition: opacity 0.2s ease;
        }
        
        .hybrid-search-result-title a:hover::after {
            opacity: 1;
        }
        
        .hybrid-search-result-excerpt {
            color: #555;
            line-height: 1.7;
            margin-bottom: 20px;
            font-size: 16px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }
        
        .hybrid-search-result-meta {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
            font-size: 14px;
        }
        
        .hybrid-search-result-score {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 5px;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }
        
        .hybrid-search-result-score::before {
            content: '⭐';
            font-size: 14px;
        }
        
        .hybrid-search-result-type {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            color: #495057;
            padding: 6px 12px;
            border-radius: 12px;
            border: 1px solid #dee2e6;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .hybrid-search-result-type::before {
            content: '📄';
            font-size: 14px;
        }
        
        .hybrid-search-result-date {
            color: #6c757d;
            background: #fff;
            padding: 6px 12px;
            border-radius: 12px;
            border: 1px solid #e9ecef;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .hybrid-search-result-date::before {
            content: '📅';
            font-size: 14px;
        }
        
        /* Empty State */
        .hybrid-search-empty {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 16px;
            border: 2px dashed #dee2e6;
        }
        
        .hybrid-search-empty-icon {
            font-size: 64px;
            margin-bottom: 20px;
            opacity: 0.7;
        }
        
        .hybrid-search-empty-title {
            font-size: 24px;
            font-weight: 600;
            color: #495057;
            margin-bottom: 10px;
        }
        
        .hybrid-search-empty-description {
            font-size: 16px;
            line-height: 1.6;
            max-width: 400px;
            margin: 0 auto;
        }
        
        /* Loading State */
        .hybrid-search-loading {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
            font-size: 18px;
            font-weight: 500;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 16px;
            border: 2px solid #dee2e6;
            position: relative;
            overflow: hidden;
        }
        
        .hybrid-search-loading::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.1), transparent);
            animation: loading-shimmer 2s infinite;
        }
        
        @keyframes loading-shimmer {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        .hybrid-search-loading::after {
            content: '⏳';
            margin-right: 10px;
            font-size: 20px;
        }
        
        /* Infinite Scroll Elements */
        .hybrid-search-infinite-trigger {
            margin-top: 30px;
            padding: 20px;
            text-align: center;
        }
        
        .hybrid-search-no-more {
            color: #6c757d;
            font-size: 16px;
            font-weight: 500;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            border: 2px dashed #dee2e6;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .hybrid-search-no-more::before {
            content: '✅';
            font-size: 18px;
        }
        
        /* Search Filters */
        .hybrid-search-filters {
            background: #fff;
            border: 1px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        
        .hybrid-search-filters-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f8f9fa;
        }
        
        .hybrid-search-filters-title {
            font-size: 16px;
            font-weight: 600;
            color: #495057;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .hybrid-search-filters-toggle {
            background: transparent;
            border: none;
            color: #667eea;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            padding: 6px 12px;
            border-radius: 6px;
            transition: all 0.2s ease;
        }
        
        .hybrid-search-filters-toggle:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .hybrid-search-filters-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .hybrid-search-filters-content.hidden {
            display: none;
        }
        
        .hybrid-search-filter-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .hybrid-search-filter-label {
            font-size: 13px;
            font-weight: 600;
            color: #495057;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .hybrid-search-filter-select {
            padding: 10px 12px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            color: #495057;
            background: #fff;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .hybrid-search-filter-select:hover {
            border-color: #667eea;
        }
        
        .hybrid-search-filter-select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .hybrid-search-filters-actions {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            padding-top: 15px;
            border-top: 1px solid #f8f9fa;
        }
        
        .hybrid-search-filter-apply {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }
        
        .hybrid-search-filter-apply:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .hybrid-search-filter-reset {
            background: #f8f9fa;
            color: #6c757d;
            border: 1px solid #dee2e6;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .hybrid-search-filter-reset:hover {
            background: #e9ecef;
            color: #495057;
        }
        
        .hybrid-search-active-filters {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        
        .hybrid-search-filter-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .hybrid-search-filter-badge-remove {
            background: rgba(255, 255, 255, 0.3);
            border: none;
            color: white;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 12px;
            line-height: 1;
            transition: all 0.2s ease;
        }
        
        .hybrid-search-filter-badge-remove:hover {
            background: rgba(255, 255, 255, 0.5);
        }
        
        /* Search Suggestions */
        .hybrid-search-suggestions {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #fff;
            border: 1px solid #e9ecef;
            border-top: none;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }
        
        .hybrid-search-suggestions.visible {
            display: block;
        }
        
        .hybrid-search-suggestion-item {
            padding: 12px 16px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid #f8f9fa;
        }
        
        .hybrid-search-suggestion-item:last-child {
            border-bottom: none;
        }
        
        .hybrid-search-suggestion-item:hover,
        .hybrid-search-suggestion-item.selected {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        }
        
        .hybrid-search-suggestion-icon {
            font-size: 16px;
            opacity: 0.6;
        }
        
        .hybrid-search-suggestion-text {
            flex: 1;
            color: #495057;
            font-size: 14px;
        }
        
        .hybrid-search-suggestion-text strong {
            color: #667eea;
            font-weight: 600;
        }
        
        .hybrid-search-suggestion-count {
            font-size: 12px;
            color: #6c757d;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 12px;
        }
        
        /* AI Answer Display */
        .hybrid-search-ai-answer {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 16px;
            margin-bottom: 30px;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .hybrid-search-ai-answer::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, rgba(255,255,255,0.3), rgba(255,255,255,0.8), rgba(255,255,255,0.3));
            animation: ai-shimmer 3s infinite;
        }
        
        @keyframes ai-shimmer {
            0%, 100% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
        }
        
        .hybrid-search-ai-answer-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
            font-weight: 600;
            font-size: 18px;
        }
        
        .hybrid-search-ai-answer-icon {
            font-size: 24px;
            animation: ai-pulse 2s infinite;
        }
        
        @keyframes ai-pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .hybrid-search-ai-answer-content {
            font-size: 16px;
            line-height: 1.6;
            opacity: 0.95;
        }
        
        .hybrid-search-ai-answer-content p {
            margin: 0 0 15px 0;
        }
        
        .hybrid-search-ai-answer-content p:last-child {
            margin-bottom: 0;
        }
        
        .hybrid-search-ai-answer-toggle {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 15px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .hybrid-search-ai-answer-toggle:hover {
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-1px);
        }
        
        .hybrid-search-ai-answer-toggle-icon {
            transition: transform 0.3s ease;
        }
        
        .hybrid-search-ai-answer-toggle.expanded .hybrid-search-ai-answer-toggle-icon {
            transform: rotate(180deg);
        }
        
        .hybrid-search-ai-answer-content.collapsed {
            max-height: 4.5em;
            overflow: hidden;
            position: relative;
        }
        
        .hybrid-search-ai-answer-content.collapsed::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 1.5em;
            background: linear-gradient(transparent, rgba(102, 126, 234, 1));
        }
        </style>
        <?php
    }
    
    /**
     * Inject search form JavaScript
     * 
     * @since 2.1.2
     */
    public function injectSearchFormJS() {
        ?>
        <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {
            // Replace existing search forms with hybrid search form
            function replaceSearchForms() {
                const searchForms = document.querySelectorAll('.search-form, form[role="search"], #searchform, .widget_search form, .searchform');
                
                searchForms.forEach(function(form) {
                    // Skip if already replaced
                    if (form.classList.contains('hybrid-search-replaced')) {
                        return;
                    }
                    
                    // Create hybrid search form
                    const hybridForm = document.createElement('div');
                    hybridForm.className = 'hybrid-search-container';
                    hybridForm.innerHTML = `
                        <form class="hybrid-search-form" method="get" action="<?php echo esc_url(home_url('/')); ?>">
                            <input type="text" 
                                   name="s" 
                                   class="hybrid-search-input" 
                                   placeholder="Search..."
                                   value="<?php echo esc_attr(get_search_query()); ?>"
                                   autocomplete="off"
                                   spellcheck="false">
                            
                            <button type="button" class="hybrid-search-clear" aria-label="Clear search">×</button>
                            
                            <button type="submit" class="hybrid-search-button hybrid-search-button--search">
                                Search
                            </button>
                            
                            <input type="hidden" name="hybrid_search" value="1">
                        </form>
                        
                        <div class="hybrid-search-filters">
                            <div class="hybrid-search-filters-header">
                                <div class="hybrid-search-filters-title">
                                    <span>🎛️</span>
                                    <span>Filters</span>
                                </div>
                                <button type="button" class="hybrid-search-filters-toggle" onclick="toggleSearchFilters()">
                                    Hide Filters
                                </button>
                            </div>
                            
                            <div class="hybrid-search-filters-content">
                                <div class="hybrid-search-filter-group">
                                    <label class="hybrid-search-filter-label">Content Type</label>
                                    <select class="hybrid-search-filter-select" id="filter-type">
                                        <option value="">All Types</option>
                                        <option value="post">Posts</option>
                                        <option value="page">Pages</option>
                                    </select>
                                </div>
                                
                                <div class="hybrid-search-filter-group">
                                    <label class="hybrid-search-filter-label">Date Range</label>
                                    <select class="hybrid-search-filter-select" id="filter-date">
                                        <option value="">Any Time</option>
                                        <option value="day">Last 24 Hours</option>
                                        <option value="week">Last Week</option>
                                        <option value="month">Last Month</option>
                                        <option value="year">Last Year</option>
                                    </select>
                                </div>
                                
                                <div class="hybrid-search-filter-group">
                                    <label class="hybrid-search-filter-label">Sort By</label>
                                    <select class="hybrid-search-filter-select" id="filter-sort">
                                        <option value="relevance">Relevance</option>
                                        <option value="date-desc">Newest First</option>
                                        <option value="date-asc">Oldest First</option>
                                        <option value="title-asc">Title A-Z</option>
                                    </select>
                                </div>
                                
                                <div class="hybrid-search-filter-group">
                                    <label class="hybrid-search-filter-label">Results Per Page</label>
                                    <select class="hybrid-search-filter-select" id="filter-limit">
                                        <option value="10">10 Results</option>
                                        <option value="25">25 Results</option>
                                        <option value="50">50 Results</option>
                                    </select>
                                </div>
                                
                                <div class="hybrid-search-filters-actions">
                                    <button type="button" class="hybrid-search-filter-apply" onclick="applySearchFilters()">
                                        Apply Filters
                                    </button>
                                    <button type="button" class="hybrid-search-filter-reset" onclick="resetSearchFilters()">
                                        Reset All
                                    </button>
                                </div>
                                
                                <div class="hybrid-search-active-filters" id="active-filters"></div>
                            </div>
                        </div>
                        
                        <div class="hybrid-search-results"></div>
                    `;
                    
                    console.log('Hybrid Search: Created form with results container');
                    
                    // Replace the original form
                    form.parentNode.insertBefore(hybridForm, form);
                    form.style.display = 'none';
                    form.classList.add('hybrid-search-replaced');
                });
            }
            
            // Replace forms on page load
            replaceSearchForms();
            
            // Also replace forms that might be loaded dynamically
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        replaceSearchForms();
                    }
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
        // Handle clear button
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('hybrid-search-clear')) {
                const input = e.target.parentNode.querySelector('.hybrid-search-input');
                if (input) {
                    input.value = '';
                    input.focus();
                }
            }
        });
        
        // Handle search form submission
        document.addEventListener('submit', function(e) {
            if (e.target.classList.contains('hybrid-search-form')) {
                e.preventDefault();
                const input = e.target.querySelector('.hybrid-search-input');
                if (input && input.value.trim()) {
                    // Redirect to search page with query
                    const query = input.value.trim();
                    const searchUrl = '<?php echo esc_url(home_url('/')); ?>?s=' + encodeURIComponent(query);
                    window.location.href = searchUrl;
                }
            }
        });
        
        // Display search results if we're on a search page
        <?php if (is_search()): ?>
        console.log('Hybrid Search: On search page, initializing results display');
        
        function displaySearchResults() {
            console.log('Hybrid Search: displaySearchResults called');
            const resultsContainer = document.querySelector('.hybrid-search-results');
            console.log('Hybrid Search: Results container found:', resultsContainer);
            
            if (!resultsContainer) {
                console.log('Hybrid Search: No results container found');
                return;
            }
            
            // Make AJAX call to get results
            const searchQuery = '<?php echo esc_js(get_search_query()); ?>';
            console.log('Hybrid Search: Search query:', searchQuery);
            
            // Minimum query length validation (3 characters)
            if (!searchQuery || searchQuery.trim().length < 3) {
                console.log('Hybrid Search: Query too short (minimum 3 characters)');
                if (searchQuery && searchQuery.trim().length > 0) {
                    resultsContainer.innerHTML = '<div class="hybrid-search-empty"><div class="hybrid-search-empty-icon">✏️</div><h3 class="hybrid-search-empty-title">Keep typing...</h3><p class="hybrid-search-empty-description">Please enter at least 3 characters to search.</p></div>';
                } else {
                    displayNoResults(resultsContainer);
                }
                return;
            }
            
            // Show loading state
            resultsContainer.innerHTML = '<div class="hybrid-search-loading">Searching...</div>';
            
            // Make AJAX call
            const showAIAnswer = <?php echo get_option('hybrid_search_show_ai_answer', false) ? 'true' : 'false'; ?>;
            const aiInstructions = <?php echo json_encode(get_option('hybrid_search_ai_instructions', '')); ?>;
            fetch('<?php echo admin_url('admin-ajax.php'); ?>', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=hybrid_search&query=' + encodeURIComponent(searchQuery) + '&limit=10&offset=0&include_answer=' + (showAIAnswer ? '1' : '0') + '&ai_instructions=' + encodeURIComponent(aiInstructions)
            })
            .then(response => {
                console.log('Hybrid Search: AJAX response received:', response);
                return response.json();
            })
            .then(data => {
                console.log('Hybrid Search: AJAX data:', data);
                console.log('Hybrid Search: data.success:', data.success);
                console.log('Hybrid Search: data.data:', data.data);
                console.log('Hybrid Search: data.data.results:', data.data ? data.data.results : 'undefined');
                console.log('Hybrid Search: results length:', data.data && data.data.results ? data.data.results.length : 'undefined');
                
                if (data.success && data.data && data.data.results && data.data.results.length > 0) {
                    console.log('Hybrid Search: Calling displayResults with:', data.data.results);
                    console.log('Hybrid Search: Metadata:', data.data.metadata);
                    
                    // AI answer can be in two places due to WordPress wrapping
                    let aiAnswer = '';
                    if (data.data.metadata) {
                        // Check direct answer field
                        if (data.data.metadata.answer && data.data.metadata.answer.trim()) {
                            aiAnswer = data.data.metadata.answer;
                            console.log('Hybrid Search: AI answer found in metadata.answer:', aiAnswer);
                        }
                        // Check nested search_metadata.answer field
                        else if (data.data.metadata.search_metadata && data.data.metadata.search_metadata.answer && data.data.metadata.search_metadata.answer.trim()) {
                            aiAnswer = data.data.metadata.search_metadata.answer;
                            console.log('Hybrid Search: AI answer found in metadata.search_metadata.answer:', aiAnswer);
                        }
                    }
                    
                    // Add AI answer to pagination data if available
                    if (aiAnswer) {
                        console.log('Hybrid Search: Adding AI answer to pagination');
                        if (!data.data.pagination) data.data.pagination = {};
                        data.data.pagination.ai_answer = aiAnswer;
                    } else {
                        console.log('Hybrid Search: No AI answer in response');
                    }
                    
                    displayResults(data.data.results, resultsContainer, data.data.pagination);
                    setupInfiniteScroll(searchQuery, resultsContainer, data.data.pagination);
                } else {
                    console.log('Hybrid Search: No results or failed request - showing no results');
                    displayNoResults(resultsContainer);
                }
            })
            .catch(error => {
                console.error('Hybrid Search: AJAX error:', error);
                displayNoResults(resultsContainer);
            });
        }
        
        function displayResults(results, container, pagination = null, isAppend = false) {
            console.log('Hybrid Search: displayResults called with:', results);
            console.log('Hybrid Search: container element:', container);
            console.log('Hybrid Search: pagination:', pagination);
            console.log('Hybrid Search: isAppend:', isAppend);
            
            if (!results || results.length === 0) {
                console.log('Hybrid Search: No results to display');
                if (!isAppend) {
                    displayNoResults(container);
                }
                return;
            }
            
            if (!isAppend) {
                // First load - create full structure
                console.log('Hybrid Search: Building HTML for', results.length, 'results');
                let html = '';
                
                // Add AI answer if available and enabled
                if (pagination && pagination.ai_answer && pagination.ai_answer.trim()) {
                    console.log('Hybrid Search: Adding AI answer to results');
                    html += buildAIAnswerHTML(pagination.ai_answer);
                }
                
                html += '<div class="hybrid-search-results-header">';
                html += '<div class="hybrid-search-results-count">Found results</div>';
                html += '</div>';
                html += '<div class="hybrid-search-results-list">';
                
                results.forEach((result, index) => {
                    html += buildResultHTML(result, index);
                });
                
                html += '</div>';
                
                // Add infinite scroll trigger
                if (pagination && pagination.has_more) {
                    html += '<div class="hybrid-search-infinite-trigger"></div>';
                }
                
                console.log('Hybrid Search: Final HTML to insert:', html);
                console.log('Hybrid Search: Setting innerHTML on container');
                container.innerHTML = html;
                console.log('Hybrid Search: innerHTML set, container now has:', container.innerHTML.length, 'characters');
            } else {
                // Append mode - just add results to existing list
                const resultsList = container.querySelector('.hybrid-search-results-list');
                if (resultsList) {
                    results.forEach((result, index) => {
                        const existingCount = resultsList.children.length;
                        const resultHTML = buildResultHTML(result, existingCount);
                        resultsList.insertAdjacentHTML('beforeend', resultHTML);
                    });
                    
                    // Update infinite scroll trigger
                    updateInfiniteScrollTrigger(container, pagination);
                }
            }
        }
        
        function buildAIAnswerHTML(aiAnswer) {
            // Check if answer is long enough to need truncation (more than 200 characters)
            const needsTruncation = aiAnswer.length > 200;
            
            let html = '<div class="hybrid-search-ai-answer">';
            html += '<div class="hybrid-search-ai-answer-header">';
            html += '<span class="hybrid-search-ai-answer-icon">🤖</span>';
            html += '<span>AI Answer</span>';
            html += '</div>';
            html += '<div class="hybrid-search-ai-answer-content' + (needsTruncation ? ' collapsed' : '') + '">';
            html += '<p>' + aiAnswer + '</p>';
            html += '</div>';
            
            if (needsTruncation) {
                html += '<button class="hybrid-search-ai-answer-toggle" onclick="toggleAIAnswer(this)">';
                html += '<span>Show more</span>';
                html += '<span class="hybrid-search-ai-answer-toggle-icon">▼</span>';
                html += '</button>';
            }
            
            html += '</div>';
            return html;
        }
        
        function toggleAIAnswer(button) {
            const answerDiv = button.closest('.hybrid-search-ai-answer');
            const content = answerDiv.querySelector('.hybrid-search-ai-answer-content');
            const toggleText = button.querySelector('span:first-child');
            const toggleIcon = button.querySelector('.hybrid-search-ai-answer-toggle-icon');
            
            if (content.classList.contains('collapsed')) {
                // Expand
                content.classList.remove('collapsed');
                toggleText.textContent = 'Show less';
                toggleIcon.textContent = '▲';
                button.classList.add('expanded');
            } else {
                // Collapse
                content.classList.add('collapsed');
                toggleText.textContent = 'Show more';
                toggleIcon.textContent = '▼';
                button.classList.remove('expanded');
            }
        }
        
        function buildResultHTML(result, index) {
            let html = '<article class="hybrid-search-result" data-result-id="' + (result.id || index) + '" data-position="' + (index + 1) + '">';
            html += '<h3 class="hybrid-search-result-title">';
            html += '<a href="' + (result.url || '#') + '" data-result-id="' + (result.id || index) + '" data-title="' + (result.title || '') + '" data-url="' + (result.url || '#') + '" data-position="' + (index + 1) + '" data-score="' + (result.score || 0) + '">';
            html += (result.title || 'Untitled');
            html += '</a>';
            html += '</h3>';
            
            if (result.excerpt) {
                let cleanExcerpt = cleanExcerptText(result.excerpt);
                html += '<div class="hybrid-search-result-excerpt">' + cleanExcerpt + '</div>';
            }
            
            html += '<div class="hybrid-search-result-meta">';
            if (result.score) {
                html += '<span class="hybrid-search-result-score">Score: ' + Math.round(result.score * 100) + '%</span>';
            }
            if (result.type) {
                html += '<span class="hybrid-search-result-type">' + result.type.charAt(0).toUpperCase() + result.type.slice(1) + '</span>';
            }
            if (result.date) {
                html += '<span class="hybrid-search-result-date">' + new Date(result.date).toLocaleDateString() + '</span>';
            }
            html += '</div>';
            html += '</article>';
            return html;
        }
        
        function cleanExcerptText(excerpt) {
            if (!excerpt) return '';
            
            // Remove HTML tags
            let cleanText = excerpt.replace(/<[^>]*>/g, '');
            
            // Remove "Continue reading" and everything after it
            cleanText = cleanText.replace(/\s*Continue reading.*$/i, '');
            
            // Remove text after dots (...) but keep the dots
            cleanText = cleanText.replace(/\s*\.{3,}\s*.*$/g, '...');
            
            // Remove any remaining trailing dots if they're at the end
            cleanText = cleanText.replace(/\.{3,}\s*$/, '...');
            
            // Clean up extra whitespace
            cleanText = cleanText.replace(/\s+/g, ' ').trim();
            
            // Ensure it ends with proper punctuation
            if (cleanText && !cleanText.match(/[.!?]$/)) {
                cleanText += '...';
            }
            
            return cleanText;
        }
        
        function displayNoResults(container) {
            console.log('Hybrid Search: displayNoResults called with container:', container);
            container.innerHTML = `
                <div class="hybrid-search-empty">
                    <div class="hybrid-search-empty-icon">🔍</div>
                    <h3 class="hybrid-search-empty-title">No results found</h3>
                    <p class="hybrid-search-empty-description">
                        Try adjusting your search terms or check the spelling.
                    </p>
                </div>
            `;
        }
        
        // Infinite scroll functionality
        let infiniteScrollObserver = null;
        let isLoadingMore = false;
        
        function setupInfiniteScroll(query, container, pagination) {
            console.log('Hybrid Search: Setting up infinite scroll for query:', query);
            console.log('Hybrid Search: Pagination:', pagination);
            
            // Clean up existing observer
            if (infiniteScrollObserver) {
                infiniteScrollObserver.disconnect();
            }
            
            if (!pagination || !pagination.has_more) {
                console.log('Hybrid Search: No more results, skipping infinite scroll setup');
                return;
            }
            
            // Create intersection observer
            infiniteScrollObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !isLoadingMore) {
                        console.log('Hybrid Search: Infinite scroll triggered');
                        loadMoreResults(query, container, pagination);
                    }
                });
            }, {
                root: null,
                rootMargin: '100px',
                threshold: 0.1
            });
            
            // Observe the trigger element
            const trigger = container.querySelector('.hybrid-search-infinite-trigger');
            if (trigger) {
                infiniteScrollObserver.observe(trigger);
                console.log('Hybrid Search: Infinite scroll observer attached to trigger');
            }
        }
        
        function loadMoreResults(query, container, currentPagination) {
            if (isLoadingMore) {
                console.log('Hybrid Search: Already loading more results, skipping');
                return;
            }
            
            isLoadingMore = true;
            console.log('Hybrid Search: Loading more results for offset:', currentPagination.next_offset);
            
            // Show loading indicator
            const trigger = container.querySelector('.hybrid-search-infinite-trigger');
            if (trigger) {
                trigger.innerHTML = '<div class="hybrid-search-loading">Loading more results...</div>';
            }
            
            // Make AJAX call for more results
            const aiInstructions = <?php echo json_encode(get_option('hybrid_search_ai_instructions', '')); ?>;
            fetch('<?php echo admin_url('admin-ajax.php'); ?>', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=hybrid_search&query=' + encodeURIComponent(query) + '&limit=10&offset=' + currentPagination.next_offset + '&ai_instructions=' + encodeURIComponent(aiInstructions)
            })
            .then(response => response.json())
            .then(data => {
                console.log('Hybrid Search: Load more response:', data);
                if (data.success && data.data && data.data.results && data.data.results.length > 0) {
                    // Append new results
                    displayResults(data.data.results, container, data.data.pagination, true);
                    
                    // Update pagination info
                    currentPagination = data.data.pagination;
                    
                    // Continue infinite scroll if there are more results
                    if (data.data.pagination.has_more) {
                        setupInfiniteScroll(query, container, data.data.pagination);
                    } else {
                        console.log('Hybrid Search: No more results to load');
                        updateInfiniteScrollTrigger(container, null);
                    }
                } else {
                    console.log('Hybrid Search: No more results available');
                    updateInfiniteScrollTrigger(container, null);
                }
            })
            .catch(error => {
                console.error('Hybrid Search: Error loading more results:', error);
                updateInfiniteScrollTrigger(container, null);
            })
            .finally(() => {
                isLoadingMore = false;
            });
        }
        
        function updateInfiniteScrollTrigger(container, pagination) {
            const trigger = container.querySelector('.hybrid-search-infinite-trigger');
            if (trigger) {
                if (pagination && pagination.has_more) {
                    trigger.innerHTML = '';
                    trigger.style.display = 'block';
                } else {
                    trigger.innerHTML = '<div class="hybrid-search-no-more">No more results to load</div>';
                    trigger.style.display = 'block';
                }
            }
        }
        
        // Display results on page load
        displaySearchResults();
        
        // Fallback: ensure results container exists
        setTimeout(function() {
            if (!document.querySelector('.hybrid-search-results')) {
                console.log('Hybrid Search: No results container found, creating one');
                const body = document.querySelector('body');
                if (body) {
                    const fallbackContainer = document.createElement('div');
                    fallbackContainer.className = 'hybrid-search-results';
                    fallbackContainer.style.cssText = 'max-width: 800px; margin: 20px auto; padding: 0 20px;';
                    body.appendChild(fallbackContainer);
                    displaySearchResults();
                }
            }
        }, 1000);
        
        // Make functions globally available
        window.toggleAIAnswer = toggleAIAnswer;
        <?php endif; ?>
        
        // Filter functionality
        let currentFilters = {
            type: '',
            date: '',
            sort: 'relevance',
            limit: 10
        };
        
        window.toggleSearchFilters = function() {
            const filtersContent = document.querySelector('.hybrid-search-filters-content');
            const toggleButton = document.querySelector('.hybrid-search-filters-toggle');
            
            if (filtersContent && toggleButton) {
                if (filtersContent.classList.contains('hidden')) {
                    filtersContent.classList.remove('hidden');
                    toggleButton.textContent = 'Hide Filters';
                } else {
                    filtersContent.classList.add('hidden');
                    toggleButton.textContent = 'Show Filters';
                }
            }
        };
        
        window.applySearchFilters = function() {
            const filterType = document.getElementById('filter-type');
            const filterDate = document.getElementById('filter-date');
            const filterSort = document.getElementById('filter-sort');
            const filterLimit = document.getElementById('filter-limit');
            
            // Update current filters
            currentFilters = {
                type: filterType ? filterType.value : '',
                date: filterDate ? filterDate.value : '',
                sort: filterSort ? filterSort.value : 'relevance',
                limit: filterLimit ? parseInt(filterLimit.value) : 10
            };
            
            console.log('Hybrid Search: Applying filters:', currentFilters);
            
            // Update active filters display
            updateActiveFilters();
            
            // Re-run search with filters (only on search pages)
            <?php if (is_search()): ?>
            const searchQuery = '<?php echo esc_js(get_search_query()); ?>';
            if (searchQuery) {
                const resultsContainer = document.querySelector('.hybrid-search-results');
                if (resultsContainer) {
                    performSearchWithFilters(searchQuery, resultsContainer);
                }
            }
            <?php endif; ?>
        };
        
        window.resetSearchFilters = function() {
            // Reset filter selects
            const filterType = document.getElementById('filter-type');
            const filterDate = document.getElementById('filter-date');
            const filterSort = document.getElementById('filter-sort');
            const filterLimit = document.getElementById('filter-limit');
            
            if (filterType) filterType.value = '';
            if (filterDate) filterDate.value = '';
            if (filterSort) filterSort.value = 'relevance';
            if (filterLimit) filterLimit.value = '10';
            
            // Reset current filters
            currentFilters = {
                type: '',
                date: '',
                sort: 'relevance',
                limit: 10
            };
            
            console.log('Hybrid Search: Filters reset');
            
            // Update active filters display
            updateActiveFilters();
            
            // Re-run search without filters (only on search pages)
            <?php if (is_search()): ?>
            const searchQuery = '<?php echo esc_js(get_search_query()); ?>';
            if (searchQuery) {
                const resultsContainer = document.querySelector('.hybrid-search-results');
                if (resultsContainer) {
                    performSearchWithFilters(searchQuery, resultsContainer);
                }
            }
            <?php endif; ?>
        };
        
        function updateActiveFilters() {
            const activeFiltersContainer = document.getElementById('active-filters');
            if (!activeFiltersContainer) return;
            
            let badges = [];
            
            if (currentFilters.type) {
                badges.push({
                    label: 'Type',
                    value: currentFilters.type === 'post' ? 'Posts' : 'Pages',
                    key: 'type'
                });
            }
            
            if (currentFilters.date) {
                const dateLabels = {
                    'day': 'Last 24 Hours',
                    'week': 'Last Week',
                    'month': 'Last Month',
                    'year': 'Last Year'
                };
                badges.push({
                    label: 'Date',
                    value: dateLabels[currentFilters.date],
                    key: 'date'
                });
            }
            
            if (currentFilters.sort !== 'relevance') {
                const sortLabels = {
                    'date-desc': 'Newest First',
                    'date-asc': 'Oldest First',
                    'title-asc': 'Title A-Z'
                };
                badges.push({
                    label: 'Sort',
                    value: sortLabels[currentFilters.sort],
                    key: 'sort'
                });
            }
            
            if (currentFilters.limit !== 10) {
                badges.push({
                    label: 'Limit',
                    value: currentFilters.limit + ' results',
                    key: 'limit'
                });
            }
            
            if (badges.length === 0) {
                activeFiltersContainer.innerHTML = '';
                return;
            }
            
            let html = '';
            badges.forEach(badge => {
                html += `
                    <div class="hybrid-search-filter-badge">
                        <span>${badge.label}: ${badge.value}</span>
                        <button class="hybrid-search-filter-badge-remove" onclick="removeFilter('${badge.key}')">×</button>
                    </div>
                `;
            });
            
            activeFiltersContainer.innerHTML = html;
        }
        
        window.removeFilter = function(filterKey) {
            // Reset specific filter
            if (filterKey === 'type') {
                currentFilters.type = '';
                const filterType = document.getElementById('filter-type');
                if (filterType) filterType.value = '';
            } else if (filterKey === 'date') {
                currentFilters.date = '';
                const filterDate = document.getElementById('filter-date');
                if (filterDate) filterDate.value = '';
            } else if (filterKey === 'sort') {
                currentFilters.sort = 'relevance';
                const filterSort = document.getElementById('filter-sort');
                if (filterSort) filterSort.value = 'relevance';
            } else if (filterKey === 'limit') {
                currentFilters.limit = 10;
                const filterLimit = document.getElementById('filter-limit');
                if (filterLimit) filterLimit.value = '10';
            }
            
            console.log('Hybrid Search: Filter removed:', filterKey);
            updateActiveFilters();
            
            // Re-run search (only on search pages)
            <?php if (is_search()): ?>
            const searchQuery = '<?php echo esc_js(get_search_query()); ?>';
            if (searchQuery) {
                const resultsContainer = document.querySelector('.hybrid-search-results');
                if (resultsContainer) {
                    performSearchWithFilters(searchQuery, resultsContainer);
                }
            }
            <?php endif; ?>
        };
        
        function performSearchWithFilters(searchQuery, resultsContainer) {
            console.log('Hybrid Search: Performing search with filters:', currentFilters);
            
            // Show loading state
            resultsContainer.innerHTML = '<div class="hybrid-search-loading">Searching...</div>';
            
            // Build request body with filters
            const showAIAnswer = <?php echo get_option('hybrid_search_show_ai_answer', false) ? 'true' : 'false'; ?>;
            const aiInstructions = <?php echo json_encode(get_option('hybrid_search_ai_instructions', '')); ?>;
            
            let requestBody = 'action=hybrid_search&query=' + encodeURIComponent(searchQuery) + 
                             '&limit=' + currentFilters.limit + 
                             '&offset=0' +
                             '&include_answer=' + (showAIAnswer ? '1' : '0') + 
                             '&ai_instructions=' + encodeURIComponent(aiInstructions);
            
            // Add filter parameters
            if (currentFilters.type) {
                requestBody += '&filter_type=' + encodeURIComponent(currentFilters.type);
            }
            if (currentFilters.date) {
                requestBody += '&filter_date=' + encodeURIComponent(currentFilters.date);
            }
            if (currentFilters.sort) {
                requestBody += '&filter_sort=' + encodeURIComponent(currentFilters.sort);
            }
            
            // Make AJAX call
            fetch('<?php echo admin_url('admin-ajax.php'); ?>', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: requestBody
            })
            .then(response => response.json())
            .then(data => {
                console.log('Hybrid Search: Filtered search response:', data);
                
                if (data.success && data.data && data.data.results && data.data.results.length > 0) {
                    // Extract AI answer
                    let aiAnswer = '';
                    if (data.data.metadata) {
                        if (data.data.metadata.answer && data.data.metadata.answer.trim()) {
                            aiAnswer = data.data.metadata.answer;
                        } else if (data.data.metadata.search_metadata && data.data.metadata.search_metadata.answer) {
                            aiAnswer = data.data.metadata.search_metadata.answer;
                        }
                    }
                    
                    if (aiAnswer) {
                        if (!data.data.pagination) data.data.pagination = {};
                        data.data.pagination.ai_answer = aiAnswer;
                    }
                    
                    displayResults(data.data.results, resultsContainer, data.data.pagination);
                    setupInfiniteScroll(searchQuery, resultsContainer, data.data.pagination);
                } else {
                    displayNoResults(resultsContainer);
                }
            })
            .catch(error => {
                console.error('Hybrid Search: Filter search error:', error);
                displayNoResults(resultsContainer);
            });
        }
        
        });
        </script>
        <?php
    }
    
    /**
     * Intercept search requests
     * 
     * @since 2.1.0
     */
    public function interceptSearchRequest() {
        // Intercept all search requests for now - we'll check API URL in the search method
        if (!is_search()) {
            return;
        }
        
        $search_query = get_search_query();
        if (empty($search_query)) {
            return;
        }
        
        // Store the search query for later use
        global $hybrid_search_query;
        $hybrid_search_query = $search_query;
        
        // Add action to replace search results
        add_filter('the_posts', [$this, 'replaceSearchResultsWithHybrid'], 10, 2);
    }
    
    /**
     * Replace search results with hybrid search results
     * 
     * @param array $posts Original posts
     * @param WP_Query $query WordPress query object
     * @return array Modified posts
     * @since 2.1.0
     */
    public function replaceSearchResultsWithHybrid($posts, $query) {
        // Only replace search query results
        if (!$query->is_search()) {
            return $posts;
        }
        
        global $hybrid_search_query;
        if (empty($hybrid_search_query)) {
            return $posts;
        }
        
        // Check if API URL is configured
        $api_url = get_option('hybrid_search_api_url', '');
        if (empty($api_url)) {
            error_log('Hybrid Search: API URL not configured');
            return $posts; // Return original posts if no API URL
        }
        
        error_log('Hybrid Search: Performing search for: ' . $hybrid_search_query . ' with API URL: ' . $api_url);
        
        // Perform hybrid search
        // Only request AI answer if we're going to show it
        $show_ai_answer = get_option('hybrid_search_show_ai_answer', false);
        $search_result = $this->search_api->search($hybrid_search_query, [
            'limit' => get_option('hybrid_search_max_results', 10),
            'include_answer' => $show_ai_answer, // Use show_ai_answer setting for API request
        ]);
        
        error_log('Hybrid Search: Search result: ' . json_encode($search_result));
        
        // Store results globally for JavaScript to display
        global $hybrid_search_results;
        $hybrid_search_results = $search_result;
        
        if (!$search_result['success'] || empty($search_result['results'])) {
            // Return empty results if hybrid search fails
            return [];
        }
        
        // Add a hook to inject results into the page content
        add_action('wp_footer', function() use ($search_result) {
            ?>
            <script type="text/javascript">
            document.addEventListener('DOMContentLoaded', function() {
                // Replace the default search results with hybrid search results
                const defaultResults = document.querySelector('.search-results, .page-content, .entry-content, .content-area');
                if (defaultResults && window.hybridSearchResults) {
                    defaultResults.innerHTML = window.hybridSearchResults;
                }
            });
            </script>
            <?php
        });
        
        // Store results for JavaScript
        global $hybrid_search_results_html;
        $ai_answer = $search_result['metadata']['answer'] ?? '';
        $hybrid_search_results_html = $this->renderSearchResults($search_result['results'], $ai_answer);
        
        // Convert hybrid search results to WordPress post format
        $hybrid_posts = $this->convertResultsToPosts($search_result['results']);
        
        // Update the query to reflect the new results
        $query->found_posts = count($hybrid_posts);
        $query->max_num_pages = 1;
        
        return $hybrid_posts;
    }
    
    /**
     * Clean excerpt text by removing unwanted content
     * 
     * @param string $excerpt Raw excerpt text
     * @return string Cleaned excerpt text
     * @since 2.2.0
     */
    private function cleanExcerptText($excerpt) {
        if (empty($excerpt)) {
            return '';
        }
        
        // Remove HTML tags
        $clean_text = strip_tags($excerpt);
        
        // Remove "Continue reading" and everything after it
        $clean_text = preg_replace('/\s*Continue reading.*$/i', '', $clean_text);
        
        // Remove text after dots (...) but keep the dots
        $clean_text = preg_replace('/\s*\.{3,}\s*.*$/g', '...', $clean_text);
        
        // Remove any remaining trailing dots if they're at the end
        $clean_text = preg_replace('/\.{3,}\s*$/', '...', $clean_text);
        
        // Clean up extra whitespace
        $clean_text = preg_replace('/\s+/', ' ', $clean_text);
        $clean_text = trim($clean_text);
        
        // Ensure it ends with proper punctuation
        if (!empty($clean_text) && !preg_match('/[.!?]$/', $clean_text)) {
            $clean_text .= '...';
        }
        
        return $clean_text;
    }

    /**
     * Convert hybrid search results to WordPress post objects
     * 
     * @param array $results Hybrid search results
     * @return array WordPress post objects
     * @since 2.1.0
     */
    private function convertResultsToPosts($results) {
        $posts = [];
        
        foreach ($results as $result) {
            // Create a fake post object
            $post = new \stdClass();
            $post->ID = $result['id'] ?? 0;
            $post->post_title = $result['title'] ?? '';
            $post->post_content = $result['excerpt'] ?? '';
            $post->post_excerpt = $result['excerpt'] ?? '';
            $post->post_type = $result['type'] ?? 'post';
            $post->post_status = 'publish';
            $post->post_date = $result['date'] ?? current_time('mysql');
            $post->post_author = 1;
            $post->post_name = sanitize_title($result['title'] ?? '');
            $post->post_parent = 0;
            $post->menu_order = 0;
            $post->post_mime_type = '';
            $post->comment_count = 0;
            $post->filter = 'raw';
            
            // Add custom fields
            $post->hybrid_search_score = $result['score'] ?? 0;
            $post->hybrid_search_url = $result['url'] ?? '';
            $post->hybrid_search_type = $result['type'] ?? 'post';
            
            // Make it behave like a post
            $post->post_type = 'hybrid_search_result';
            $post->is_search_result = true;
            
            $posts[] = $post;
        }
        
        return $posts;
    }
    
    /**
     * Replace search results (alternative method)
     * 
     * @param array $posts Original posts
     * @param WP_Query $query WordPress query object
     * @return array Modified posts
     * @since 2.1.0
     */
    public function replaceSearchResults($posts, $query) {
        // This is a fallback method - the main logic is in replaceSearchResultsWithHybrid
        return $posts;
    }
}
