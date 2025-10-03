/**
 * Hybrid Search JavaScript
 */

(function($) {
    'use strict';
    
    let searchTimeout;
    let currentQuery = '';
    let currentPage = 1;
    let isLoadingMore = false;
    let hasMoreResults = false;
    let allResults = [];
    
    $(document).ready(function() {
        initializeHybridSearch();
    });
    
    function initializeHybridSearch() {
        // Debug: Log configuration
        console.log('Hybrid Search initialized with config:', {
            ajaxUrl: hybridSearch.ajaxUrl,
            apiUrl: hybridSearch.apiUrl,
            maxResults: hybridSearch.maxResults,
            includeAnswer: hybridSearch.includeAnswer,
            hasNonce: !!hybridSearch.nonce
        });
        
        // Auto-focus search input
        setTimeout(function() {
            const searchInput = $('#hybrid-search-input');
            if (searchInput.length && !searchInput.val()) {
                searchInput.focus();
            }
        }, 100);
        
        // Add clear button to search input
        addClearButton();
        
        // Initialize search history
        initializeSearchHistory();
        
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
                addToSearchHistory(query);
                performSearch(query);
            }
        });
        
        // Handle real-time search with suggestions
        $('#hybrid-search-input').on('input', function() {
            const query = $(this).val().trim();
            
            // Toggle clear button visibility
            toggleClearButton(query.length > 0);
            
            clearTimeout(searchTimeout);
            
            if (query.length >= 3) {
                // Show search suggestions
                showSearchSuggestions(query);
                
                searchTimeout = setTimeout(function() {
                    currentQuery = query;
                    updateURL(query);
                    addToSearchHistory(query);
                    performSearch(query);
                }, 500);
            } else if (query.length === 0) {
                clearResults();
                hideSearchSuggestions();
            } else {
                hideSearchSuggestions();
            }
        });
        
        // Handle keyboard navigation
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape') {
                hideSearchSuggestions();
                $('#hybrid-search-input').blur();
            }
        });
        
        // Initialize infinite scroll
        initializeInfiniteScroll();
    }
    
    function performSearch(query, page = 1) {
        if (!query) return;
        
        // Reset pagination for new search
        if (page === 1) {
            currentPage = 1;
            allResults = [];
            showLoading();
        } else {
            // Loading more results
            isLoadingMore = true;
            showLoadMoreIndicator();
        }
        
        hideError();
        hideNoResults();
        
        const searchData = {
            action: 'hybrid_search',
            query: query,
            limit: hybridSearch.maxResults,
            include_answer: hybridSearch.includeAnswer,
            ai_instructions: hybridSearch.aiInstructions || '',
            page: page,
            nonce: hybridSearch.nonce || ''
        };
        
        $.ajax({
            url: hybridSearch.ajaxUrl,
            type: 'POST',
            data: searchData,
            timeout: 30000,
            success: function(response) {
                hideLoading();
                hideLoadMoreIndicator();
                console.log('Search response:', response);
                
                if (response.success && response.data) {
                    if (page === 1) {
                        // New search - replace results
                        allResults = response.data.results || [];
                        displayResults(response.data);
                    } else {
                        // Load more - append results
                        const newResults = response.data.results || [];
                        allResults = allResults.concat(newResults);
                        appendResults(newResults);
                    }
                    
                    // Check if there are more results
                    hasMoreResults = (response.data.results || []).length >= hybridSearch.maxResults;
                    currentPage = page;
                    isLoadingMore = false;
                } else {
                    showError(response.data?.error || response.data?.message || 'Search failed');
                    isLoadingMore = false;
                }
            },
            error: function(xhr, status, error) {
                hideLoading();
                hideLoadMoreIndicator();
                console.error('Search error:', xhr, status, error);
                console.error('Response text:', xhr.responseText);
                
                let errorMessage = 'Network error: ' + error;
                if (xhr.responseText) {
                    try {
                        const errorData = JSON.parse(xhr.responseText);
                        errorMessage = errorData.data?.message || errorData.message || errorMessage;
                    } catch (e) {
                        errorMessage = xhr.responseText || errorMessage;
                    }
                }
                
                showError(errorMessage);
                isLoadingMore = false;
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
        
        // Apply client-side filters if set
        let filteredResults = data.results;
        if (window.currentFilters) {
            filteredResults = applyClientSideFilters(data.results, window.currentFilters);
        }
        
        // Display AI answer if available (only on first page)
        if (data.answer && currentPage === 1) {
            const answerHtml = createAiAnswerHtml(data.answer);
            resultsContainer.append(answerHtml);
        }
        
        // Display search results
        filteredResults.forEach(function(result, index) {
            const resultHtml = createResultHtml(result, index);
            resultsContainer.append(resultHtml);
        });
        
        // Show processing time (only on first page)
        if (data.processing_time && currentPage === 1) {
            const timeHtml = `
                <div class="search-stats">
                    <p>Found ${filteredResults.length} results in ${data.processing_time.toFixed(2)}s</p>
                </div>
            `;
            resultsContainer.append(timeHtml);
        }
        
        // Add load more button or infinite scroll trigger
        if (hasMoreResults && !isLoadingMore) {
            addLoadMoreButton();
        }
        
        resultsContainer.show();
    }
    
    function appendResults(newResults) {
        const resultsContainer = $('#search-results');
        
        // Apply client-side filters if set
        let filteredResults = newResults;
        if (window.currentFilters) {
            filteredResults = applyClientSideFilters(newResults, window.currentFilters);
        }
        
        // Append new results
        filteredResults.forEach(function(result, index) {
            const resultHtml = createResultHtml(result, allResults.length - newResults.length + index);
            resultsContainer.append(resultHtml);
        });
        
        // Update load more button
        if (hasMoreResults && !isLoadingMore) {
            addLoadMoreButton();
        } else {
            removeLoadMoreButton();
        }
    }
    
    function applyClientSideFilters(results, filters) {
        return results.filter(function(result) {
            // Content type filter
            if (filters.type && result.type !== filters.type) {
                return false;
            }
            
            // Date range filter
            if (filters.dateFrom || filters.dateTo) {
                const resultDate = new Date(result.date);
                if (filters.dateFrom && resultDate < new Date(filters.dateFrom)) {
                    return false;
                }
                if (filters.dateTo && resultDate > new Date(filters.dateTo)) {
                    return false;
                }
            }
            
            // Author filter
            if (filters.author && result.author !== filters.author) {
                return false;
            }
            
            return true;
        });
    }
    
    function createAiAnswerHtml(answer) {
        const maxLength = 300; // Characters to show initially
        const shouldTruncate = answer.length > maxLength;
        const shortAnswer = shouldTruncate ? answer.substring(0, maxLength) + '...' : answer;
        
        const uniqueId = 'ai-answer-' + Date.now();
        
        let answerHtml = `
            <div class="ai-answer" id="${uniqueId}">
                <h3>AI Answer</h3>
                <div class="ai-answer-content">
                    <p class="ai-answer-text">${escapeHtml(shortAnswer)}</p>
        `;
        
        if (shouldTruncate) {
            answerHtml += `
                    <p class="ai-answer-full" style="display: none;">${escapeHtml(answer)}</p>
                    <div class="ai-answer-actions">
                        <button class="ai-answer-toggle" onclick="toggleAiAnswer('${uniqueId}')">
                            <span class="show-more">Show more</span>
                            <span class="show-less" style="display: none;">Show less</span>
                        </button>
                        <button class="ai-answer-copy" onclick="copyAiAnswer('${uniqueId}')" title="Copy answer">
                            📋 Copy
                        </button>
                    </div>
            `;
        } else {
            answerHtml += `
                    <div class="ai-answer-actions">
                        <button class="ai-answer-copy" onclick="copyAiAnswer('${uniqueId}')" title="Copy answer">
                            📋 Copy
                        </button>
                    </div>
            `;
        }
        
        answerHtml += `
                </div>
            </div>
        `;
        
        return answerHtml;
    }
    
    function toggleAiAnswer(answerId) {
        const container = document.getElementById(answerId);
        const shortText = container.querySelector('.ai-answer-text');
        const fullText = container.querySelector('.ai-answer-full');
        const showMore = container.querySelector('.show-more');
        const showLess = container.querySelector('.show-less');
        
        if (fullText && fullText.style.display === 'none') {
            // Show full answer
            shortText.style.display = 'none';
            fullText.style.display = 'block';
            showMore.style.display = 'none';
            showLess.style.display = 'inline';
        } else {
            // Show short answer
            shortText.style.display = 'block';
            if (fullText) fullText.style.display = 'none';
            showMore.style.display = 'inline';
            showLess.style.display = 'none';
        }
    }
    
    function copyAiAnswer(answerId) {
        const container = document.getElementById(answerId);
        const fullText = container.querySelector('.ai-answer-full');
        const shortText = container.querySelector('.ai-answer-text');
        
        // Get the text to copy (prefer full text if available)
        const textToCopy = fullText ? fullText.textContent : shortText.textContent;
        
        // Copy to clipboard
        navigator.clipboard.writeText(textToCopy).then(function() {
            // Show feedback
            const copyBtn = container.querySelector('.ai-answer-copy');
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '✅ Copied!';
            copyBtn.style.background = '#28a745';
            
            setTimeout(function() {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
            }, 2000);
        }).catch(function(err) {
            console.error('Failed to copy text: ', err);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        });
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
        
        // Get thumbnail if available
        const thumbnail = result.featured_image || result.thumbnail || '';
        
        return `
            <div class="search-result-item" data-score="${result.score}">
                ${thumbnail ? `
                    <div class="result-thumbnail">
                        <img src="${escapeHtml(thumbnail)}" alt="${escapeHtml(result.title)}" loading="lazy">
                    </div>
                ` : ''}
                
                <div class="result-content">
                    <h2 class="search-result-title">
                        <a href="${escapeHtml(result.url)}">${escapeHtml(result.title)}</a>
                    </h2>
                    
                    <div class="search-result-meta">
                        <span class="result-type">${escapeHtml(result.type)}</span>
                        <span class="result-author">by ${escapeHtml(result.author)}</span>
                        <span class="result-date">${formatDate(result.date)}</span>
                    </div>
                    
                    <div class="search-result-excerpt">
                        ${highlightQuery(excerpt, currentQuery)}
                    </div>
                    
                    ${categoryLinks ? `<div class="search-result-categories">${categoryLinks}</div>` : ''}
                    ${tagLinks ? `<div class="search-result-tags">${tagLinks}</div>` : ''}
                </div>
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
        if (!dateString || dateString === 'Invalid Date') {
            return '';
        }
        
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) {
                return '';
            }
            return date.toLocaleDateString();
        } catch (e) {
            return '';
        }
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
        showLoadingSkeleton();
    }
    
    function hideLoading() {
        $('#search-loading').hide();
        hideLoadingSkeleton();
    }
    
    function showLoadingSkeleton() {
        const skeletonHtml = `
            <div class="loading-skeleton">
                <div class="skeleton-ai-answer">
                    <div class="skeleton-line skeleton-title"></div>
                    <div class="skeleton-line skeleton-text"></div>
                    <div class="skeleton-line skeleton-text"></div>
                    <div class="skeleton-line skeleton-text-short"></div>
                </div>
                ${Array(3).fill(`
                    <div class="skeleton-result">
                        <div class="skeleton-line skeleton-title"></div>
                        <div class="skeleton-line skeleton-meta"></div>
                        <div class="skeleton-line skeleton-text"></div>
                        <div class="skeleton-line skeleton-text"></div>
                        <div class="skeleton-line skeleton-text-short"></div>
                    </div>
                `).join('')}
            </div>
        `;
        
        $('#search-results').html(skeletonHtml).show();
    }
    
    function hideLoadingSkeleton() {
        $('.loading-skeleton').remove();
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
    
    function addClearButton() {
        const searchInput = $('#hybrid-search-input');
        if (searchInput.length) {
            const inputWrapper = searchInput.parent();
            if (!inputWrapper.find('.clear-search').length) {
                inputWrapper.css('position', 'relative');
                inputWrapper.append('<button type="button" class="clear-search" onclick="clearSearch()" style="display: none;">×</button>');
            }
        }
    }
    
    function toggleClearButton(show) {
        $('.clear-search').toggle(show);
    }
    
    function clearSearch() {
        $('#hybrid-search-input').val('').focus();
        toggleClearButton(false);
        clearResults();
        hideSearchSuggestions();
        updateURL('');
    }
    
    function initializeSearchHistory() {
        // Load search history from localStorage
        const history = JSON.parse(localStorage.getItem('hybrid-search-history') || '[]');
        updateSearchHistoryDisplay(history);
        
        // Initialize filters sidebar
        initializeFiltersSidebar();
        
        // Add filters toggle button
        addFiltersToggleButton();
    }
    
    function initializeFiltersSidebar() {
        // Create filters sidebar if it doesn't exist
        if (!$('#search-filters').length) {
            const filtersHtml = `
                <div id="search-filters" class="filters-sidebar">
                    <div class="filters-header">
                        <h3>Filters</h3>
                        <button class="toggle-filters" onclick="toggleFiltersSidebar()">×</button>
                    </div>
                    <div class="filters-content">
                        <div class="filter-group">
                            <label>Content Type</label>
                            <select id="content-type-filter">
                                <option value="">All Types</option>
                                <option value="post">Posts</option>
                                <option value="page">Pages</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>Date Range</label>
                            <input type="date" id="date-from" placeholder="From">
                            <input type="date" id="date-to" placeholder="To">
                        </div>
                        <div class="filter-group">
                            <label>Author</label>
                            <select id="author-filter">
                                <option value="">All Authors</option>
                            </select>
                        </div>
                        <div class="filter-actions">
                            <button class="apply-filters" onclick="applyFilters()">Apply Filters</button>
                            <button class="clear-filters" onclick="clearFilters()">Clear</button>
                        </div>
                    </div>
                </div>
            `;
            
            $('body').append(filtersHtml);
        }
    }
    
    function toggleFiltersSidebar() {
        $('#search-filters').toggleClass('active');
    }
    
    function applyFilters() {
        const filters = {
            type: $('#content-type-filter').val(),
            dateFrom: $('#date-from').val(),
            dateTo: $('#date-to').val(),
            author: $('#author-filter').val()
        };
        
        // Store filters for current search
        window.currentFilters = filters;
        
        // Re-run search with filters
        if (currentQuery) {
            performSearch(currentQuery);
        }
    }
    
    function clearFilters() {
        $('#content-type-filter').val('');
        $('#date-from').val('');
        $('#date-to').val('');
        $('#author-filter').val('');
        window.currentFilters = {};
        
        // Re-run search without filters
        if (currentQuery) {
            performSearch(currentQuery);
        }
    }
    
    function addFiltersToggleButton() {
        if (!$('.filters-toggle-btn').length) {
            const toggleButton = `
                <button class="filters-toggle-btn" onclick="toggleFiltersSidebar()" title="Toggle Filters">
                    🔍
                </button>
            `;
            $('body').append(toggleButton);
        }
    }
    
    function addToSearchHistory(query) {
        if (!query || query.length < 2) return;
        
        let history = JSON.parse(localStorage.getItem('hybrid-search-history') || '[]');
        
        // Remove if already exists
        history = history.filter(item => item !== query);
        
        // Add to beginning
        history.unshift(query);
        
        // Limit to 10 items
        history = history.slice(0, 10);
        
        // Save to localStorage
        localStorage.setItem('hybrid-search-history', JSON.stringify(history));
        
        updateSearchHistoryDisplay(history);
    }
    
    function updateSearchHistoryDisplay(history) {
        const container = $('#search-history');
        if (container.length && history.length > 0) {
            const historyHtml = history.map(item => 
                `<li onclick="searchFromHistory('${escapeHtml(item)}')">${escapeHtml(item)}</li>`
            ).join('');
            
            container.html(`<ul>${historyHtml}</ul>`).show();
        } else if (container.length) {
            container.hide();
        }
    }
    
    function searchFromHistory(query) {
        $('#hybrid-search-input').val(query);
        currentQuery = query;
        updateURL(query);
        performSearch(query);
        hideSearchSuggestions();
    }
    
    function showSearchSuggestions(query) {
        const history = JSON.parse(localStorage.getItem('hybrid-search-history') || '[]');
        const suggestions = history.filter(item => 
            item.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 5);
        
        if (suggestions.length > 0) {
            const suggestionsHtml = suggestions.map(item => 
                `<li onclick="searchFromHistory('${escapeHtml(item)}')">${escapeHtml(item)}</li>`
            ).join('');
            
            let container = $('#search-suggestions');
            if (!container.length) {
                container = $('<div id="search-suggestions"></div>').insertAfter('#hybrid-search-input');
            }
            
            container.html(`<ul>${suggestionsHtml}</ul>`).show();
        }
    }
    
    function hideSearchSuggestions() {
        $('#search-suggestions').hide();
    }
    
    function initializeInfiniteScroll() {
        // Add scroll event listener for infinite scroll
        $(window).on('scroll', function() {
            if (!isLoadingMore && hasMoreResults) {
                const scrollTop = $(window).scrollTop();
                const windowHeight = $(window).height();
                const documentHeight = $(document).height();
                
                // Load more when user is near bottom (100px threshold)
                if (scrollTop + windowHeight >= documentHeight - 100) {
                    loadMoreResults();
                }
            }
        });
    }
    
    function loadMoreResults() {
        if (!isLoadingMore && hasMoreResults && currentQuery) {
            performSearch(currentQuery, currentPage + 1);
        }
    }
    
    function addLoadMoreButton() {
        if (!$('.load-more-btn').length && hasMoreResults) {
            const loadMoreBtn = `
                <div class="load-more-container">
                    <button class="load-more-btn" onclick="loadMoreResults()">
                        Load More Results
                    </button>
                </div>
            `;
            $('#search-results').append(loadMoreBtn);
        }
    }
    
    function removeLoadMoreButton() {
        $('.load-more-btn').parent().remove();
    }
    
    function showLoadMoreIndicator() {
        if (!$('.load-more-indicator').length) {
            const indicator = `
                <div class="load-more-indicator">
                    <div class="loading-spinner"></div>
                    <p>Loading more results...</p>
                </div>
            `;
            $('#search-results').append(indicator);
        }
    }
    
    function hideLoadMoreIndicator() {
        $('.load-more-indicator').remove();
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Add CSS for score indicators and AI answer styling
    $('<style>')
        .prop('type', 'text/css')
        .html(`
            /* Search Input Enhancements */
            .hybrid-search-form {
                position: relative;
                max-width: 600px;
                margin: 0 auto 20px;
            }
            
            .hybrid-search-form input[type="text"] {
                width: 100%;
                padding: 12px 40px 12px 16px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.2s;
            }
            
            .hybrid-search-form input[type="text"]:focus {
                border-color: #007cba;
                outline: none;
                box-shadow: 0 0 0 3px rgba(0, 124, 186, 0.1);
            }
            
            .clear-search {
                position: absolute;
                right: 8px;
                top: 50%;
                transform: translateY(-50%);
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                cursor: pointer;
                font-size: 14px;
                line-height: 1;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .clear-search:hover {
                background: #c82333;
            }
            
            /* Search History and Suggestions */
            #search-history, #search-suggestions {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #dee2e6;
                border-top: none;
                border-radius: 0 0 8px 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                z-index: 1000;
                max-height: 200px;
                overflow-y: auto;
            }
            
            #search-history ul, #search-suggestions ul {
                list-style: none;
                margin: 0;
                padding: 0;
            }
            
            #search-history li, #search-suggestions li {
                padding: 8px 16px;
                cursor: pointer;
                border-bottom: 1px solid #f8f9fa;
            }
            
            #search-history li:hover, #search-suggestions li:hover {
                background: #f8f9fa;
            }
            
            /* Loading Skeletons */
            .loading-skeleton {
                padding: 20px;
            }
            
            .skeleton-line {
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: skeleton-loading 1.5s infinite;
                border-radius: 4px;
                margin-bottom: 10px;
            }
            
            .skeleton-title {
                height: 20px;
                width: 60%;
            }
            
            .skeleton-text {
                height: 16px;
                width: 100%;
            }
            
            .skeleton-text-short {
                height: 16px;
                width: 80%;
            }
            
            .skeleton-meta {
                height: 14px;
                width: 40%;
            }
            
            .skeleton-ai-answer {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .skeleton-result {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
            }
            
            @keyframes skeleton-loading {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
            
            /* AI Answer Enhancements */
            .ai-answer {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .ai-answer h3 {
                margin-top: 0;
                margin-bottom: 15px;
                color: #495057;
                font-size: 1.25rem;
            }
            
            .ai-answer-content p {
                margin-bottom: 15px;
                line-height: 1.6;
                color: #343a40;
            }
            
            .ai-answer-actions {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            
            .ai-answer-toggle, .ai-answer-copy {
                background: #007cba;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: background-color 0.2s;
            }
            
            .ai-answer-toggle:hover, .ai-answer-copy:hover {
                background: #005a87;
            }
            
            /* Search Results with Thumbnails */
            .search-result-item {
                display: flex;
                gap: 15px;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
                transition: box-shadow 0.2s;
            }
            
            .search-result-item:hover {
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            
            .result-thumbnail {
                flex-shrink: 0;
                width: 120px;
                height: 80px;
                overflow: hidden;
                border-radius: 6px;
            }
            
            .result-thumbnail img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            
            .result-content {
                flex: 1;
            }
            
            .search-result-title {
                margin: 0 0 8px 0;
                font-size: 1.1rem;
            }
            
            .search-result-title a {
                color: #007cba;
                text-decoration: none;
            }
            
            .search-result-title a:hover {
                text-decoration: underline;
            }
            
            .search-result-meta {
                display: flex;
                gap: 15px;
                font-size: 0.85rem;
                color: #6c757d;
                margin-bottom: 8px;
            }
            
            .search-result-excerpt {
                color: #495057;
                line-height: 1.5;
            }
            
            /* Filters Sidebar */
            .filters-sidebar {
                position: fixed;
                top: 0;
                right: -350px;
                width: 350px;
                height: 100vh;
                background: white;
                border-left: 1px solid #dee2e6;
                box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
                transition: right 0.3s ease;
                z-index: 1000;
                overflow-y: auto;
            }
            
            .filters-sidebar.active {
                right: 0;
            }
            
            .filters-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid #dee2e6;
                background: #f8f9fa;
            }
            
            .filters-header h3 {
                margin: 0;
                font-size: 1.2rem;
            }
            
            .toggle-filters {
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                cursor: pointer;
                font-size: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .filters-content {
                padding: 20px;
            }
            
            .filter-group {
                margin-bottom: 20px;
            }
            
            .filter-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #495057;
            }
            
            .filter-group select,
            .filter-group input {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 0.9rem;
            }
            
            .filter-group input[type="date"] {
                margin-bottom: 8px;
            }
            
            .filter-actions {
                display: flex;
                gap: 10px;
                margin-top: 30px;
            }
            
            .apply-filters,
            .clear-filters {
                flex: 1;
                padding: 10px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: background-color 0.2s;
            }
            
            .apply-filters {
                background: #007cba;
                color: white;
            }
            
            .apply-filters:hover {
                background: #005a87;
            }
            
            .clear-filters {
                background: #6c757d;
                color: white;
            }
            
            .clear-filters:hover {
                background: #545b62;
            }
            
            /* Filters Toggle Button */
            .filters-toggle-btn {
                position: fixed;
                top: 50%;
                right: 20px;
                transform: translateY(-50%);
                background: #007cba;
                color: white;
                border: none;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                cursor: pointer;
                font-size: 18px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                z-index: 999;
                transition: background-color 0.2s;
            }
            
            .filters-toggle-btn:hover {
                background: #005a87;
            }
            
            /* Mobile Responsive */
            @media (max-width: 768px) {
                .search-result-item {
                    flex-direction: column;
                    gap: 10px;
                }
                
                .result-thumbnail {
                    width: 100%;
                    height: 150px;
                }
                
                .search-result-meta {
                    flex-wrap: wrap;
                    gap: 8px;
                }
                
                .ai-answer-actions {
                    flex-direction: column;
                }
                
                .hybrid-search-form {
                    margin: 0 -15px 20px;
                    padding: 0 15px;
                }
                
                .filters-sidebar {
                    width: 100%;
                    right: -100%;
                }
                
                .filters-toggle-btn {
                    bottom: 20px;
                    top: auto;
                    transform: none;
                }
            }
            
            /* Legacy styles */
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
            
            /* Infinite Scroll and Load More */
            .load-more-container {
                text-align: center;
                margin: 30px 0;
            }
            
            .load-more-btn {
                background: #007cba;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1rem;
                transition: background-color 0.2s;
            }
            
            .load-more-btn:hover {
                background: #005a87;
            }
            
            .load-more-indicator {
                text-align: center;
                padding: 20px;
                color: #6c757d;
            }
            
            .loading-spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #007cba;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `)
        .appendTo('head');
    
})(jQuery);
