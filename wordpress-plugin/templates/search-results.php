<?php
/**
 * Search Results Template for Hybrid Search
 */

get_header(); ?>

<div class="container">
    <div class="search-header">
        <h1 class="search-title">
            <?php 
            $query = get_query_var('s') ?: get_query_var('hybrid_search_query');
            printf(__('Search Results for: %s', 'hybrid-search'), '<span class="search-query">' . esc_html($query) . '</span>');
            ?>
        </h1>
        
        <div class="search-form-container">
            <form role="search" method="get" class="hybrid-search-form" action="<?php echo esc_url(home_url('/')); ?>">
                <input type="search" 
                       class="search-field" 
                       placeholder="<?php echo esc_attr_x('Search...', 'placeholder', 'hybrid-search'); ?>" 
                       value="<?php echo esc_attr($query); ?>" 
                       name="s" 
                       id="hybrid-search-input" />
                <button type="submit" class="search-submit">
                    <span class="screen-reader-text"><?php echo _x('Search', 'submit button', 'hybrid-search'); ?></span>
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"/>
                    </svg>
                </button>
            </form>
        </div>
    </div>

    <div class="search-results-container">
        <div id="search-loading" class="search-loading" style="display: none;">
            <div class="loading-spinner"></div>
            <p><?php _e('Searching...', 'hybrid-search'); ?></p>
        </div>
        
        <div id="search-error" class="search-error" style="display: none;">
            <p><?php _e('Sorry, there was an error performing your search. Please try again.', 'hybrid-search'); ?></p>
        </div>
        
        <div id="search-results" class="search-results">
            <!-- Results will be loaded here via JavaScript -->
        </div>
        
        <div id="search-no-results" class="search-no-results" style="display: none;">
            <h3><?php _e('No results found', 'hybrid-search'); ?></h3>
            <p><?php _e('Try different keywords or check your spelling.', 'hybrid-search'); ?></p>
        </div>
    </div>
</div>

<style>
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.search-header {
    text-align: center;
    margin-bottom: 40px;
}

.search-title {
    font-size: 2.5rem;
    margin-bottom: 20px;
    color: #333;
}

.search-query {
    color: #0073aa;
    font-weight: bold;
}

.search-form-container {
    max-width: 600px;
    margin: 0 auto;
}

.hybrid-search-form {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

.search-field {
    flex: 1;
    padding: 12px 16px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.3s ease;
}

.search-field:focus {
    outline: none;
    border-color: #0073aa;
}

.search-submit {
    padding: 12px 20px;
    background: #0073aa;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.search-submit:hover {
    background: #005a87;
}

.search-loading {
    text-align: center;
    padding: 40px;
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #0073aa;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.search-error {
    background: #f8d7da;
    color: #721c24;
    padding: 20px;
    border-radius: 8px;
    margin: 20px 0;
    text-align: center;
}

.search-results {
    display: grid;
    gap: 30px;
}

.search-result-item {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.search-result-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.search-result-title {
    font-size: 1.5rem;
    margin-bottom: 10px;
}

.search-result-title a {
    color: #0073aa;
    text-decoration: none;
}

.search-result-title a:hover {
    text-decoration: underline;
}

.search-result-meta {
    color: #666;
    font-size: 0.9rem;
    margin-bottom: 15px;
}

.search-result-excerpt {
    color: #555;
    line-height: 1.6;
    margin-bottom: 15px;
}

.search-result-score {
    display: inline-block;
    background: #e8f4fd;
    color: #0073aa;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
}

.search-result-categories {
    margin-top: 15px;
}

.search-result-categories a {
    display: inline-block;
    background: #f0f0f0;
    color: #666;
    padding: 4px 8px;
    margin-right: 8px;
    margin-bottom: 8px;
    border-radius: 4px;
    text-decoration: none;
    font-size: 0.8rem;
}

.search-result-categories a:hover {
    background: #e0e0e0;
}

.ai-answer {
    background: #f8f9fa;
    border-left: 4px solid #0073aa;
    padding: 20px;
    margin-bottom: 30px;
    border-radius: 0 8px 8px 0;
}

.ai-answer h3 {
    color: #0073aa;
    margin-bottom: 15px;
}

.ai-answer p {
    margin: 0;
    line-height: 1.6;
}

.search-no-results {
    text-align: center;
    padding: 60px 20px;
    color: #666;
}

.search-no-results h3 {
    font-size: 1.5rem;
    margin-bottom: 15px;
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .search-title {
        font-size: 2rem;
    }
    
    .hybrid-search-form {
        flex-direction: column;
    }
    
    .search-result-item {
        padding: 20px;
    }
}
</style>

<?php get_footer(); ?>
