/**
 * Hybrid Search JavaScript
 */

(function($) {
    'use strict';
    
    let searchTimeout;
    let currentQuery = '';
    
    $(document).ready(function() {
        initializeHybridSearch();
    });
    
    function initializeHybridSearch() {
        // Get search query from URL
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('s') || '';
        
        if (query) {
            currentQuery = query;
            performSearch(query);
        }
        
        // Handle search form submission
        $('.hybrid-search-form').on('submit', function(e) {
            e.preventDefault();
            const query = $(this).find('#hybrid-search-input').val().trim();
            
            if (query) {
                currentQuery = query;
                updateURL(query);
                performSearch(query);
            }
        });
        
        // Handle real-time search (optional)
        $('#hybrid-search-input').on('input', function() {
            const query = $(this).val().trim();
            
            clearTimeout(searchTimeout);
            
            if (query.length >= 3) {
                searchTimeout = setTimeout(function() {
                    currentQuery = query;
                    updateURL(query);
                    performSearch(query);
                }, 500);
            } else if (query.length === 0) {
                clearResults();
            }
        });
    }
    
    function performSearch(query) {
        if (!query) return;
        
        showLoading();
        hideError();
        hideNoResults();
        
        const searchData = {
            action: 'hybrid_search',
            query: query,
            limit: hybridSearch.maxResults,
            include_answer: hybridSearch.includeAnswer,
            nonce: hybridSearch.nonce || ''
        };
        
        $.ajax({
            url: hybridSearch.ajaxUrl,
            type: 'POST',
            data: searchData,
            timeout: 30000,
            success: function(response) {
                hideLoading();
                
                if (response.success && response.data) {
                    displayResults(response.data);
                } else {
                    showError(response.data?.error || 'Search failed');
                }
            },
            error: function(xhr, status, error) {
                hideLoading();
                showError('Network error: ' + error);
            }
        });
    }
    
    function displayResults(data) {
        const resultsContainer = $('#search-results');
        resultsContainer.empty();
        
        if (!data.results || data.results.length === 0) {
            showNoResults();
            return;
        }
        
        // Display AI answer if available
        if (data.answer) {
            const answerHtml = `
                <div class="ai-answer">
                    <h3>AI Answer</h3>
                    <p>${escapeHtml(data.answer)}</p>
                </div>
            `;
            resultsContainer.append(answerHtml);
        }
        
        // Display search results
        data.results.forEach(function(result, index) {
            const resultHtml = createResultHtml(result, index);
            resultsContainer.append(resultHtml);
        });
        
        // Show processing time
        if (data.processing_time) {
            const timeHtml = `
                <div class="search-stats">
                    <p>Found ${data.total_results} results in ${data.processing_time.toFixed(2)}s</p>
                </div>
            `;
            resultsContainer.append(timeHtml);
        }
        
        resultsContainer.show();
    }
    
    function createResultHtml(result, index) {
        const categories = result.categories || [];
        const tags = result.tags || [];
        
        const categoryLinks = categories.map(function(cat) {
            return `<a href="${getCategoryUrl(cat)}">${escapeHtml(cat.name)}</a>`;
        }).join('');
        
        const tagLinks = tags.map(function(tag) {
            return `<a href="${getTagUrl(tag)}">${escapeHtml(tag.name)}</a>`;
        }).join('');
        
        const excerpt = result.excerpt || truncateText(result.content, 200);
        const scoreClass = getScoreClass(result.score);
        
        return `
            <div class="search-result-item" data-score="${result.score}">
                <h2 class="search-result-title">
                    <a href="${escapeHtml(result.url)}">${escapeHtml(result.title)}</a>
                </h2>
                
                <div class="search-result-meta">
                    <span class="result-type">${escapeHtml(result.type)}</span>
                    <span class="result-author">by ${escapeHtml(result.author)}</span>
                    <span class="result-date">${formatDate(result.date)}</span>
                    <span class="search-result-score ${scoreClass}">${(result.score * 100).toFixed(1)}% match</span>
                </div>
                
                <div class="search-result-excerpt">
                    ${highlightQuery(excerpt, currentQuery)}
                </div>
                
                ${categoryLinks ? `<div class="search-result-categories">${categoryLinks}</div>` : ''}
                ${tagLinks ? `<div class="search-result-tags">${tagLinks}</div>` : ''}
            </div>
        `;
    }
    
    function highlightQuery(text, query) {
        if (!query) return escapeHtml(text);
        
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return escapeHtml(text).replace(regex, '<mark>$1</mark>');
    }
    
    function getScoreClass(score) {
        if (score >= 0.8) return 'score-high';
        if (score >= 0.6) return 'score-medium';
        if (score >= 0.4) return 'score-low';
        return 'score-very-low';
    }
    
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }
    
    function truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    function getCategoryUrl(category) {
        return `${hybridSearch.siteUrl}/category/${category.slug}/`;
    }
    
    function getTagUrl(tag) {
        return `${hybridSearch.siteUrl}/tag/${tag.slug}/`;
    }
    
    function updateURL(query) {
        const url = new URL(window.location);
        url.searchParams.set('s', query);
        window.history.pushState({}, '', url);
    }
    
    function showLoading() {
        $('#search-loading').show();
        $('#search-results').hide();
    }
    
    function hideLoading() {
        $('#search-loading').hide();
    }
    
    function showError(message) {
        $('#search-error').html(`<p>${escapeHtml(message)}</p>`).show();
        $('#search-results').hide();
    }
    
    function hideError() {
        $('#search-error').hide();
    }
    
    function showNoResults() {
        $('#search-no-results').show();
        $('#search-results').hide();
    }
    
    function hideNoResults() {
        $('#search-no-results').hide();
    }
    
    function clearResults() {
        $('#search-results').empty().hide();
        hideError();
        hideNoResults();
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Add CSS for score indicators
    $('<style>')
        .prop('type', 'text/css')
        .html(`
            .score-high { background: #d4edda; color: #155724; }
            .score-medium { background: #fff3cd; color: #856404; }
            .score-low { background: #f8d7da; color: #721c24; }
            .score-very-low { background: #f5c6cb; color: #721c24; }
            
            mark {
                background: #ffeb3b;
                padding: 2px 4px;
                border-radius: 2px;
            }
            
            .search-stats {
                text-align: center;
                color: #666;
                font-size: 0.9rem;
                margin-top: 20px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
            }
        `)
        .appendTo('head');
    
})(jQuery);
