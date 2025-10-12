<?php
/**
 * Shortcode Manager
 * 
 * Handles all shortcodes for the Hybrid Search plugin
 * 
 * @package HybridSearch\Frontend
 * @since 2.5.2
 */

namespace HybridSearch\Frontend;

class ShortcodeManager {
    
    /**
     * Frontend Manager instance
     * 
     * @var FrontendManager
     */
    private $frontend_manager;
    
    /**
     * Constructor
     * 
     * @param FrontendManager $frontend_manager
     */
    public function __construct(FrontendManager $frontend_manager) {
        $this->frontend_manager = $frontend_manager;
    }
    
    /**
     * Register WordPress hooks
     * 
     * @since 2.5.2
     */
    public function registerHooks() {
        // Register shortcodes
        add_shortcode('hybrid_search', [$this, 'searchFormShortcode']);
        add_shortcode('hybrid_search_form', [$this, 'searchFormOnlyShortcode']);
        add_shortcode('hybrid_search_results', [$this, 'searchResultsShortcode']);
    }
    
    /**
     * Main search shortcode (form + results)
     * 
     * Usage: [hybrid_search]
     * 
     * @param array $atts Shortcode attributes
     * @return string Shortcode output
     * @since 2.5.2
     */
    public function searchFormShortcode($atts = []) {
        $atts = shortcode_atts([
            'placeholder' => 'Search...',
            'button_text' => 'Search',
            'show_filters' => 'true',
            'show_results' => 'true',
        ], $atts, 'hybrid_search');
        
        ob_start();
        ?>
        <div class="hybrid-search-shortcode-wrapper" data-show-filters="<?php echo esc_attr($atts['show_filters']); ?>">
            <?php 
            // Inject CSS
            $this->frontend_manager->injectSearchFormCSS();
            
            // Render form with filters
            echo $this->frontend_manager->renderSearchForm([
                'placeholder' => $atts['placeholder'],
                'button_text' => $atts['button_text'],
                'show_clear' => true,
            ]); 
            
            // Inject JavaScript
            $this->frontend_manager->injectSearchFormJS();
            ?>
            
            <style>
                /* Shortcode-specific styles */
                .hybrid-search-shortcode-wrapper .hybrid-search-container {
                    max-width: 100%;
                }
                
                <?php if ($atts['show_filters'] === 'true'): ?>
                /* SHOW filters */
                .hybrid-search-shortcode-wrapper .hybrid-search-filters {
                    display: block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    height: auto !important;
                }
                .hybrid-search-shortcode-wrapper .hybrid-search-filters-content {
                    display: grid !important;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important;
                    gap: 20px !important;
                }
                <?php else: ?>
                /* HIDE filters */
                .hybrid-search-shortcode-wrapper .hybrid-search-filters {
                    display: none !important;
                }
                <?php endif; ?>
                
                <?php if ($atts['show_results'] === 'false'): ?>
                /* HIDE results */
                .hybrid-search-shortcode-wrapper .hybrid-search-results {
                    display: none !important;
                }
                <?php endif; ?>
            </style>
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Search form only shortcode (no results)
     * 
     * Usage: [hybrid_search_form]
     * 
     * @param array $atts Shortcode attributes
     * @return string Shortcode output
     * @since 2.5.2
     */
    public function searchFormOnlyShortcode($atts = []) {
        $atts = shortcode_atts([
            'placeholder' => 'Search...',
            'button_text' => 'Search',
            'show_filters' => 'false',
            'redirect' => 'true',
        ], $atts, 'hybrid_search_form');
        
        ob_start();
        ?>
        <div class="hybrid-search-form-only">
            <?php 
            // Inject CSS
            $this->frontend_manager->injectSearchFormCSS();
            ?>
            
            <form class="hybrid-search-form" method="get" action="<?php echo esc_url(home_url('/')); ?>">
                <input type="text" 
                       name="s" 
                       class="hybrid-search-input" 
                       placeholder="<?php echo esc_attr($atts['placeholder']); ?>"
                       autocomplete="off"
                       spellcheck="false"
                       required
                       minlength="3">
                
                <button type="button" class="hybrid-search-clear" aria-label="Clear search">×</button>
                
                <button type="submit" class="hybrid-search-button hybrid-search-button--search">
                    <?php echo esc_html($atts['button_text']); ?>
                </button>
                
                <input type="hidden" name="hybrid_search" value="1">
            </form>
            
            <?php if ($atts['show_filters'] === 'true'): ?>
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
            <?php endif; ?>
            
            <?php 
            // Inject JavaScript for form functionality
            $this->frontend_manager->injectSearchFormJS();
            ?>
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Search results only shortcode
     * 
     * Usage: [hybrid_search_results]
     * 
     * @param array $atts Shortcode attributes
     * @return string Shortcode output
     * @since 2.5.2
     */
    public function searchResultsShortcode($atts = []) {
        // Only show results if there's a search query
        if (!is_search() && empty(get_query_var('s'))) {
            return '<p class="hybrid-search-no-query">Enter a search query to see results.</p>';
        }
        
        $search_query = get_search_query();
        if (empty($search_query)) {
            return '<p class="hybrid-search-no-query">Enter a search query to see results.</p>';
        }
        
        ob_start();
        ?>
        <div class="hybrid-search-results-only">
            <?php 
            // Inject CSS
            $this->frontend_manager->injectSearchFormCSS();
            ?>
            
            <div class="hybrid-search-results"></div>
            
            <?php 
            // Inject JavaScript
            $this->frontend_manager->injectSearchFormJS();
            ?>
        </div>
        <?php
        return ob_get_clean();
    }
}

