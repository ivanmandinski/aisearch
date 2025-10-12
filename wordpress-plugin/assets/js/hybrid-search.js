/**
 * Hybrid Search JavaScript
 */

(function($) {
    'use strict';
    
    let searchTimeout;
    let suggestionTimeout;
    let currentQuery = '';
    let currentPage = 1;
    let isLoadingMore = false;
    let hasMoreResults = false;
    let allResults = [];
    let lastSearchQuery = '';
    let searchHistory = [];
    let suggestionsVisible = false;
    let selectedSuggestionIndex = -1;
    
    $(document).ready(function() {
        initializeHybridSearch();
    });
    
    function initializeHybridSearch() {
        // Debug: Log configuration
        console.log('Hybrid Search initialized with config:', {
            ajaxUrl: hybridSearch.ajaxUrl,
            apiUrl: hybridSearch.apiUrl,
            maxResults: hybridSearch.maxResults,
            includeAnswer: hybridSearch.includeAnswer
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
                }, 800); // Increased from 500ms to 800ms
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
    
    // Search Analytics Tracking
    function trackSearchAnalytics(query, results, timeTaken, userInfo) {
        console.log('trackSearchAnalytics called with:', {
            query: query,
            resultsCount: results.length,
            timeTaken: timeTaken
        });
        
        const analytics = {
            query: query,
            resultCount: results.length,
            timeTaken: timeTaken,
            timestamp: new Date().toISOString(),
            hasResults: results.length > 0,
            userAgent: navigator.userAgent,
            language: navigator.language,
            screenResolution: `${screen.width}x${screen.height}`,
            viewportSize: `${window.innerWidth}x${window.innerHeight}`,
            referrer: document.referrer,
            sessionId: getSessionId(),
            userId: getUserId(),
            ipAddress: null, // Will be filled by server
            location: null, // Will be filled by server
            deviceType: getDeviceType(),
            browserInfo: getBrowserInfo(),
            searchMethod: 'hybrid_search',
            filters: window.currentFilters || {},
            sortMethod: localStorage.getItem('hybrid-search-sort') || 'relevance'
        };
        
        console.log('Analytics data prepared:', analytics);
        
        // Send to server
        sendAnalyticsToServer(analytics);
        
        // Store locally for admin dashboard
        storeLocalAnalytics(analytics);
    }
    
    // CTR Tracking Functions
    let ctrResults = []; // Store results for CTR tracking
    
    function storeResultsForCTRTracking(results, query) {
        console.log('Storing results for CTR tracking:', results.length, 'results');
        ctrResults = results.map((result, index) => ({
            ...result,
            position: index + 1,
            query: query,
            sessionId: getSessionId(),
            userId: getUserId(),
            deviceType: getDeviceType(),
            browserInfo: getBrowserInfo()
        }));
    }
    
    function trackCTRClick(resultId, resultTitle, resultUrl, position, score) {
        console.log('Tracking CTR click:', { resultId, resultTitle, position });
        
        const ctrData = {
            search_id: getLatestSearchId(), // We'll get this from the analytics
            result_id: resultId,
            result_title: resultTitle,
            result_url: resultUrl,
            result_position: position,
            result_score: score,
            session_id: getSessionId(),
            user_id: getUserId(),
            device_type: getDeviceType(),
            browser_name: getBrowserInfo().name,
            query: currentQuery
        };
        
        // Send CTR data to server
        $.ajax({
            url: hybridSearch.ajaxUrl,
            type: 'POST',
            data: {
                action: 'track_search_ctr',
                ctr_data: ctrData
            },
            success: function(response) {
                console.log('CTR tracked successfully:', response);
            },
            error: function(xhr, status, error) {
                console.error('CTR tracking failed:', error);
            }
        });
    }
    
    function getLatestSearchId() {
        // This would ideally come from the search response
        // For now, we'll use a timestamp-based approach
        return Date.now();
    }
    
    // Search deduplication and throttling
    function shouldTrackSearch(query) {
        if (!query || query.length < 3) {
            return false;
        }
        
        // Check if this is a partial/typing search
        if (lastSearchQuery && query.toLowerCase().includes(lastSearchQuery.toLowerCase()) && query.length <= lastSearchQuery.length + 2) {
            return false;
        }
        
        // Check if we've already searched for this exact query recently (within 30 seconds)
        const now = Date.now();
        const recentSearches = searchHistory.filter(item => now - item.timestamp < 30000);
        if (recentSearches.some(item => item.query.toLowerCase() === query.toLowerCase())) {
            return false;
        }
        
        // Check if this is just a partial version of a recent search
        const isPartial = recentSearches.some(item => {
            const recentQuery = item.query.toLowerCase();
            const currentQuery = query.toLowerCase();
            return (currentQuery.length < recentQuery.length && recentQuery.startsWith(currentQuery)) ||
                   (recentQuery.length < currentQuery.length && currentQuery.startsWith(recentQuery));
        });
        
        if (isPartial) {
            return false;
        }
        
        // Add to search history
        searchHistory.push({
            query: query,
            timestamp: now
        });
        
        // Keep only last 10 searches in history
        if (searchHistory.length > 10) {
            searchHistory = searchHistory.slice(-10);
        }
        
        lastSearchQuery = query;
        return true;
    }
    
    function getSessionId() {
        let sessionId = sessionStorage.getItem('hybrid-search-session-id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('hybrid-search-session-id', sessionId);
        }
        return sessionId;
    }
    
    function getUserId() {
        let userId = localStorage.getItem('hybrid-search-user-id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('hybrid-search-user-id', userId);
        }
        return userId;
    }
    
    function getDeviceType() {
        const userAgent = navigator.userAgent.toLowerCase();
        if (/mobile|android|iphone|ipad|phone/i.test(userAgent)) {
            return 'mobile';
        } else if (/tablet|ipad/i.test(userAgent)) {
            return 'tablet';
        } else {
            return 'desktop';
        }
    }
    
    function getBrowserInfo() {
        const userAgent = navigator.userAgent;
        let browser = 'Unknown';
        
        if (userAgent.includes('Chrome')) browser = 'Chrome';
        else if (userAgent.includes('Firefox')) browser = 'Firefox';
        else if (userAgent.includes('Safari')) browser = 'Safari';
        else if (userAgent.includes('Edge')) browser = 'Edge';
        else if (userAgent.includes('Opera')) browser = 'Opera';
        
        return {
            name: browser,
            version: userAgent.match(/(?:Chrome|Firefox|Safari|Edge|Opera)\/(\d+\.\d+)/)?.[1] || 'Unknown',
            full: userAgent
        };
    }
    
    function sendAnalyticsToServer(analytics) {
        console.log('Sending analytics to server:', analytics);
        
        // Send to WordPress admin via AJAX
        $.ajax({
            url: hybridSearch.ajaxUrl,
            type: 'POST',
            data: {
                action: 'track_search_analytics',
                analytics: analytics
            },
            success: function(response) {
                console.log('Analytics tracked successfully:', response);
            },
            error: function(xhr, status, error) {
                console.error('Analytics tracking failed:', {
                    status: status,
                    error: error,
                    responseText: xhr.responseText,
                    statusCode: xhr.status
                });
                
                // Try to show error in console for debugging
                if (xhr.responseText) {
                    try {
                        const errorData = JSON.parse(xhr.responseText);
                        console.error('Server error:', errorData);
                    } catch (e) {
                        console.error('Raw server response:', xhr.responseText);
                    }
                }
            }
        });
    }
    
    function storeLocalAnalytics(analytics) {
        const existingAnalytics = JSON.parse(localStorage.getItem('hybrid-search-analytics') || '[]');
        existingAnalytics.push(analytics);
        
        // Keep only last 1000 searches
        if (existingAnalytics.length > 1000) {
            existingAnalytics.splice(0, existingAnalytics.length - 1000);
        }
        
        localStorage.setItem('hybrid-search-analytics', JSON.stringify(existingAnalytics));
    }
    
    // Smart Query Expansion
    function expandQuery(query) {
        const expansions = {
            'waste': ['waste management', 'waste disposal', 'waste reduction', 'hazardous waste'],
            'environment': ['environmental', 'environmental compliance', 'environmental consulting'],
            'facility': ['facility management', 'facility operations', 'facility maintenance'],
            'sustainability': ['sustainable', 'sustainability services', 'green solutions'],
            'compliance': ['regulatory compliance', 'environmental compliance', 'compliance management'],
            'air': ['air quality', 'air pollution', 'air monitoring', 'air emissions'],
            'water': ['water treatment', 'water quality', 'water management', 'wastewater'],
            'energy': ['energy efficiency', 'energy management', 'renewable energy'],
            'recycling': ['waste recycling', 'material recycling', 'recycling programs'],
            'scs': ['SCS Engineers', 'SCS services', 'SCS consulting']
        };
        
        const words = query.toLowerCase().split(/\s+/);
        let expandedTerms = [...words];
        
        words.forEach(word => {
            if (expansions[word]) {
                expandedTerms = expandedTerms.concat(expansions[word]);
            }
        });
        
        // Remove duplicates and return unique terms
        return [...new Set(expandedTerms)].join(' ');
    }
    
    // Related Results Functionality
    function addRelatedResults(results) {
        if (!results || results.length === 0) return;
        
        const relatedResultsHtml = `
            <div class="related-results-section">
                <h3 class="related-results-title">
                    <span class="related-icon">🔗</span>
                    Related Content
                </h3>
                <div class="related-results-grid">
                    ${results.slice(0, 3).map(result => `
                        <div class="related-result-item" onclick="trackCTRClick('${result.id}', '${escapeHtml(result.title)}', '${result.url}', ${index + 1}, ${result.score || 0}); window.location.href='${result.url}'">
                            <div class="related-result-content">
                                <h4 class="related-result-title">${decodeHtmlEntities(result.title)}</h4>
                                <p class="related-result-excerpt">${decodeHtmlEntities(result.excerpt || '').substring(0, 120)}...</p>
                                <div class="related-result-meta">
                                    <span class="related-result-type">${result.type}</span>
                                    <span class="related-result-date">${formatDate(result.date)}</span>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        $('#search-results').append(relatedResultsHtml);
    }
    
    // Semantic Search Enhancement
    function enhanceSearchWithSemantics(query, results) {
        // Find semantically similar content
        const semanticTerms = generateSemanticTerms(query);
        const enhancedResults = results.map(result => {
            const semanticScore = calculateSemanticScore(result, semanticTerms);
            return {
                ...result,
                semanticScore: semanticScore,
                enhancedScore: (result.score || 0) + (semanticScore * 0.3) // Blend semantic score
            };
        });
        
        // Sort by enhanced score
        return enhancedResults.sort((a, b) => (b.enhancedScore || 0) - (a.enhancedScore || 0));
    }
    
    function generateSemanticTerms(query) {
        const semanticMappings = {
            'waste management': ['recycling', 'disposal', 'minimization', 'diversion', 'treatment'],
            'environmental': ['sustainability', 'green', 'eco-friendly', 'conservation', 'protection'],
            'compliance': ['regulatory', 'standards', 'requirements', 'permits', 'certification'],
            'facility': ['operations', 'maintenance', 'management', 'infrastructure', 'systems'],
            'air quality': ['emissions', 'pollution', 'monitoring', 'testing', 'control'],
            'water treatment': ['wastewater', 'purification', 'filtration', 'quality', 'management'],
            'energy efficiency': ['conservation', 'optimization', 'renewable', 'sustainability', 'reduction']
        };
        
        const terms = [];
        Object.keys(semanticMappings).forEach(key => {
            if (query.toLowerCase().includes(key.toLowerCase())) {
                terms.push(...semanticMappings[key]);
            }
        });
        
        return [...new Set(terms)];
    }
    
    function calculateSemanticScore(result, semanticTerms) {
        const content = (result.content || '').toLowerCase();
        const title = (result.title || '').toLowerCase();
        const excerpt = (result.excerpt || '').toLowerCase();
        
        let score = 0;
        semanticTerms.forEach(term => {
            const termLower = term.toLowerCase();
            if (content.includes(termLower)) score += 0.1;
            if (title.includes(termLower)) score += 0.3;
            if (excerpt.includes(termLower)) score += 0.2;
        });
        
        return Math.min(score, 1); // Cap at 1
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
            session_id: getSessionId()
        };
        
        const startTime = Date.now();
        
        $.ajax({
            url: hybridSearch.ajaxUrl,
            type: 'POST',
            data: searchData,
            timeout: 30000,
            success: function(response) {
                const timeTaken = (Date.now() - startTime) / 1000;
                
                hideLoading();
                hideLoadMoreIndicator();
                console.log('Search response:', response);
                
                if (response.success && response.data) {
                    // Track analytics only for meaningful searches (deduplicated)
                    if (shouldTrackSearch(query)) {
                        trackSearchAnalytics(query, response.data.results || [], timeTaken);
                    }
                    
                    if (page === 1) {
                        // New search - replace results
                        allResults = response.data.results || [];
                        displayResults(response.data);
                        // Store results for CTR tracking
                        storeResultsForCTRTracking(response.data.results || [], query);
                    } else {
                        // Load more - append results
                        const newResults = response.data.results || [];
                        allResults = allResults.concat(newResults);
                        appendResults(newResults);
                        // Store additional results for CTR tracking
                        storeResultsForCTRTracking(newResults, query);
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
        
        // Add search controls
        if (currentPage === 1) {
            addSearchControls();
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
                    <button class="ai-answer-toggle" onclick="window.toggleAiAnswer('${uniqueId}')">
                        <span class="show-more">Show more</span>
                        <span class="show-less" style="display: none;">Show less</span>
                    </button>
                        <button class="ai-answer-copy" onclick="window.copyAiAnswer('${uniqueId}')" title="Copy answer">
                            📋 Copy
                        </button>
                    </div>
            `;
        } else {
            answerHtml += `
                    <div class="ai-answer-actions">
                        <button class="ai-answer-copy" onclick="window.copyAiAnswer('${uniqueId}')" title="Copy answer">
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
    
    window.toggleAiAnswer = function(answerId) {
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
    
    window.copyAiAnswer = function(answerId) {
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
            return `<a href="${getCategoryUrl(cat)}" class="category-link">${escapeHtml(cat.name)}</a>`;
        }).join('');
        
        const tagLinks = tags.map(function(tag) {
            return `<a href="${getTagUrl(tag)}" class="tag-link">${escapeHtml(tag.name)}</a>`;
        }).join('');
        
        let excerpt = result.excerpt || generateSmartExcerpt(result.content || '', currentQuery, 600);
        
        // Remove "Continue reading" text with various patterns
        excerpt = excerpt.replace(/\s*…?\s*Continue reading\s+[^→]*→\s*/g, '');
        excerpt = excerpt.replace(/\s*…?\s*Continue reading\s+[^→]*\s*$/g, '');
        excerpt = excerpt.replace(/\s*…\s*Continue reading.*$/g, '');
        
        // Get thumbnail if available
        const thumbnail = result.featured_image || result.thumbnail || extractFirstImage(result.content) || '';
        
        // Format meta information
        const metaItems = [];
        if (result.type) {
            metaItems.push(`<span class="result-type">${escapeHtml(result.type)}</span>`);
        }
        if (result.author && result.author.trim()) {
            metaItems.push(`<span class="result-author">by ${escapeHtml(result.author)}</span>`);
        }
        const formattedDate = formatDate(result.date);
        if (formattedDate) {
            metaItems.push(`<span class="result-date">${formattedDate}</span>`);
        }
        
        // Calculate reading time
        const wordCount = result.word_count || (result.content ? result.content.split(' ').length : 0);
        const readingTime = Math.ceil(wordCount / 200); // Average reading speed: 200 words per minute
        
        return `
            <div class="search-result-item" data-score="${result.score}">
                ${thumbnail ? `
                    <div class="result-thumbnail">
                        <img src="${escapeHtml(thumbnail)}" alt="${decodeHtmlEntities(result.title)}" loading="lazy">
                        <div class="result-overlay">
                            <span class="result-type-badge">${escapeHtml(result.type || 'Article')}</span>
                        </div>
                    </div>
                ` : ''}
                
                <div class="result-content">
                    <div class="result-header">
                        <h2 class="search-result-title">
                            <a href="${escapeHtml(result.url)}" onclick="trackCTRClick('${result.id}', '${escapeHtml(result.title)}', '${result.url}', ${index + 1}, ${result.score || 0})">${highlightQuery(decodeHtmlEntities(result.title), currentQuery)}</a>
                        </h2>
                        <div class="result-actions">
                            <button class="bookmark-btn" onclick="window.bookmarkResult('${result.id}')" title="Bookmark">
                                <span class="bookmark-icon">🔖</span>
                            </button>
                            <button class="share-btn" onclick="window.shareResult('${result.url}', '${escapeHtml(result.title)}')" title="Share">
                                <span class="share-icon">📤</span>
                            </button>
                        </div>
                    </div>
                    
                    ${metaItems.length > 0 ? `
                        <div class="search-result-meta">
                            ${metaItems.join('')}
                            ${readingTime > 0 ? `<span class="reading-time">${readingTime} min read</span>` : ''}
                        </div>
                    ` : ''}
                    
                    <div class="search-result-excerpt">
                        ${highlightQuery(decodeHtmlEntities(excerpt), currentQuery)}
                    </div>
                    
                    ${categoryLinks || tagLinks ? `
                        <div class="result-taxonomy">
                            ${categoryLinks ? `<div class="search-result-categories">${categoryLinks}</div>` : ''}
                            ${tagLinks ? `<div class="search-result-tags">${tagLinks}</div>` : ''}
                        </div>
                    ` : ''}
                    
                    <div class="result-footer">
                        <a href="${escapeHtml(result.url)}" class="read-more-btn" onclick="trackCTRClick('${result.id}', '${escapeHtml(result.title)}', '${result.url}', ${index + 1}, ${result.score || 0})">
                            Read More →
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    function highlightQuery(text, query) {
        if (!query || !text) return escapeHtml(text);
        
        const terms = query.split(/\s+/).filter(term => term.length > 2);
        let highlighted = escapeHtml(text);
        
        terms.forEach(term => {
            const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
            highlighted = highlighted.replace(regex, '<mark class="search-highlight">$1</mark>');
        });
        
        return highlighted;
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
        
        // Popular search terms (can be customized)
        const popularTerms = [
            'waste management', 'environmental compliance', 'facility management',
            'sustainability', 'recycling', 'hazardous waste', 'air quality',
            'water treatment', 'energy efficiency', 'regulatory compliance',
            'SCS Engineers', 'environmental consulting', 'waste minimization',
            'remediation', 'environmental assessment', 'permitting'
        ];
        
        // Get suggestions from history
        const historySuggestions = history.filter(item => 
            item.toLowerCase().includes(query.toLowerCase()) && item !== query
        ).slice(0, 3);
        
        // Get suggestions from popular terms
        const popularSuggestions = popularTerms.filter(term => 
            term.toLowerCase().includes(query.toLowerCase()) && 
            !historySuggestions.includes(term) &&
            term !== query
        ).slice(0, 2);
        
        const allSuggestions = [...historySuggestions, ...popularSuggestions];
        
        if (allSuggestions.length > 0) {
            // Group suggestions by type
            const historyGroup = historySuggestions.length > 0 ? `
                <div class="suggestion-group">
                    <div class="group-header">
                        <span class="group-icon">🕒</span>
                        <span class="group-title">Recent Searches</span>
                    </div>
                    <div class="group-items">
                        ${historySuggestions.map((item, index) => `
                            <li class="suggestion-item history-suggestion" data-index="${index}" onclick="selectSuggestion('${escapeHtml(item)}')">
                                <div class="suggestion-content">
                                    <span class="suggestion-text">${highlightSuggestion(item, query)}</span>
                                    <span class="suggestion-action">Press Enter</span>
                                </div>
                                <div class="suggestion-indicator"></div>
                            </li>
                        `).join('')}
                    </div>
                </div>
            ` : '';
            
            const popularGroup = popularSuggestions.length > 0 ? `
                <div class="suggestion-group">
                    <div class="group-header">
                        <span class="group-icon">🔥</span>
                        <span class="group-title">Popular Searches</span>
                    </div>
                    <div class="group-items">
                        ${popularSuggestions.map((item, index) => `
                            <li class="suggestion-item popular-suggestion" data-index="${historySuggestions.length + index}" onclick="selectSuggestion('${escapeHtml(item)}')">
                                <div class="suggestion-content">
                                    <span class="suggestion-text">${highlightSuggestion(item, query)}</span>
                                    <span class="suggestion-action">Press Enter</span>
                                </div>
                                <div class="suggestion-indicator"></div>
                            </li>
                        `).join('')}
                    </div>
                </div>
            ` : '';
            
            const suggestionsHtml = `
                <div class="suggestions-container">
                    ${historyGroup}
                    ${popularGroup}
                    <div class="suggestions-footer">
                        <span class="keyboard-hint">
                            <kbd>↑</kbd><kbd>↓</kbd> to navigate • <kbd>Enter</kbd> to select • <kbd>Esc</kbd> to close
                        </span>
                    </div>
                </div>
            `;
            
            let container = $('#search-suggestions');
            if (!container.length) {
                const inputContainer = $('#hybrid-search-input').parent();
                container = $('<div id="search-suggestions" class="suggestions-dropdown"></div>').appendTo(inputContainer);
            }
            
            container.html(suggestionsHtml).show();
            
            // Initialize keyboard navigation
            initializeKeyboardNavigation();
        } else {
            hideSearchSuggestions();
        }
    }
    
    function hideSearchSuggestions() {
        $('#search-suggestions').hide();
        $('#hybrid-search-input').off('keydown.suggestions');
    }
    
    function highlightSuggestion(text, query) {
        if (!query) return escapeHtml(text);
        
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return escapeHtml(text).replace(regex, '<mark class="suggestion-highlight">$1</mark>');
    }
    
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    window.selectSuggestion = function(suggestion) {
        $('#hybrid-search-input').val(suggestion);
        currentQuery = suggestion;
        updateURL(suggestion);
        addToSearchHistory(suggestion);
        performSearch(suggestion);
        hideSearchSuggestions();
    };
    
    function initializeKeyboardNavigation() {
        let selectedIndex = -1;
        
        $('#hybrid-search-input').off('keydown.suggestions').on('keydown.suggestions', function(e) {
            const suggestions = $('#search-suggestions .suggestion-item');
            const totalSuggestions = suggestions.length;
            
            if (totalSuggestions === 0) return;
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, totalSuggestions - 1);
                    updateSelection();
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, -1);
                    updateSelection();
                    break;
                    
                case 'Enter':
                    e.preventDefault();
                    if (selectedIndex >= 0) {
                        const selectedSuggestion = suggestions.eq(selectedIndex).find('.suggestion-text').text();
                        selectSuggestion(selectedSuggestion);
                    }
                    break;
                    
                case 'Escape':
                    hideSearchSuggestions();
                    selectedIndex = -1;
                    break;
            }
        });
        
        function updateSelection() {
            $('#search-suggestions .suggestion-item').removeClass('selected');
            if (selectedIndex >= 0) {
                $('#search-suggestions .suggestion-item').eq(selectedIndex).addClass('selected');
            }
        }
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
    
    function addSearchControls() {
        // Remove existing controls
        $('.search-controls').remove();
        
        const controlsHtml = `
            <div class="search-controls">
                <div class="search-sort">
                    <span class="sort-label">Sort by:</span>
                    <button class="sort-btn active" data-sort="relevance" title="Sort by relevance">
                        <span class="sort-icon">🎯</span> Relevance
                    </button>
                    <button class="sort-btn" data-sort="date" title="Sort by date">
                        <span class="sort-icon">📅</span> Date
                    </button>
                    <button class="sort-btn" data-sort="title" title="Sort by title">
                        <span class="sort-icon">📝</span> Title
                    </button>
                </div>
                <div class="date-range-filter">
                    <span class="filter-label">Date range:</span>
                    <select class="date-range-select">
                        <option value="">All time</option>
                        <option value="week">Last week</option>
                        <option value="month">Last month</option>
                        <option value="year">Last year</option>
                    </select>
                </div>
                <div class="search-stats" id="search-stats"></div>
            </div>
        `;
        
        $('#search-results').before(controlsHtml);
        
        // Add event listeners for sort buttons
        $('.sort-btn').on('click', function() {
            const sortType = $(this).data('sort');
            sortResults(sortType);
            
            // Update active state
            $('.sort-btn').removeClass('active');
            $(this).addClass('active');
            
            // Save sort preference
            localStorage.setItem('hybrid-search-sort', sortType);
        });
        
        // Add event listener for date range filter
        $('.date-range-select').on('change', function() {
            const dateRange = $(this).val();
            filterByDateRange(dateRange);
        });
        
        // Load saved sort preference
        const savedSort = localStorage.getItem('hybrid-search-sort') || 'relevance';
        if (savedSort !== 'relevance') {
            $(`.sort-btn[data-sort="${savedSort}"]`).click();
        }
    }
    
    function sortResults(sortType) {
        const resultsContainer = $('#search-results');
        const resultItems = resultsContainer.find('.search-result-item').toArray();
        
        // Sort the results
        resultItems.sort(function(a, b) {
            const $a = $(a);
            const $b = $(b);
            
            switch(sortType) {
                case 'relevance':
                    const scoreA = parseFloat($a.data('score')) || 0;
                    const scoreB = parseFloat($b.data('score')) || 0;
                    return scoreB - scoreA; // Higher scores first
                    
                case 'date':
                    const dateTextA = $a.find('.result-date').text().trim();
                    const dateTextB = $b.find('.result-date').text().trim();
                    
                    // Try to parse dates, fallback to string comparison
                    const dateA = parseDate(dateTextA);
                    const dateB = parseDate(dateTextB);
                    
                    if (dateA && dateB) {
                        return dateB - dateA; // Newer dates first
                    }
                    
                    // Fallback to string comparison
                    return dateTextB.localeCompare(dateTextA);
                    
                case 'title':
                    const titleA = $a.find('.search-result-title a').text().toLowerCase().trim();
                    const titleB = $b.find('.search-result-title a').text().toLowerCase().trim();
                    return titleA.localeCompare(titleB);
                    
                default:
                    return 0;
            }
        });
        
        // Re-append sorted results
        resultsContainer.empty();
        resultItems.forEach(item => resultsContainer.append(item));
        
        // Add smooth animation
        resultsContainer.hide().fadeIn(300);
    }
    
    function parseDate(dateString) {
        if (!dateString || dateString === 'Invalid Date') return null;
        
        // Try different date formats
        const formats = [
            new Date(dateString),
            new Date(dateString.replace(/(\d{1,2})\/(\d{1,2})\/(\d{4})/, '$3-$1-$2')),
            new Date(dateString.replace(/(\d{1,2})-(\d{1,2})-(\d{4})/, '$3-$1-$2'))
        ];
        
        for (let date of formats) {
            if (!isNaN(date.getTime())) {
                return date;
            }
        }
        
        return null;
    }
    
    function filterByDateRange(dateRange) {
        if (!dateRange) {
            // Show all results
            $('.search-result-item').show();
            return;
        }
        
        const now = new Date();
        let cutoffDate;
        
        switch(dateRange) {
            case 'week':
                cutoffDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            case 'month':
                cutoffDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                break;
            case 'year':
                cutoffDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                break;
            default:
                return;
        }
        
        $('.search-result-item').each(function() {
            const $item = $(this);
            const dateText = $item.find('.result-date').text().trim();
            const itemDate = parseDate(dateText);
            
            if (itemDate && itemDate >= cutoffDate) {
                $item.show();
            } else {
                $item.hide();
            }
        });
        
        // Update stats
        const visibleCount = $('.search-result-item:visible').length;
        const totalCount = $('.search-result-item').length;
        $('#search-stats').text(`Showing ${visibleCount} of ${totalCount} results`);
    }
    
    function generateSmartExcerpt(content, query, maxLength) {
        if (!content || !query) {
            return truncateText(content, maxLength);
        }
        
        // Clean content
        const cleanContent = content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        const queryTerms = query.toLowerCase().split(/\s+/).filter(term => term.length > 2);
        
        if (queryTerms.length === 0) {
            return truncateText(cleanContent, maxLength);
        }
        
        // Find the best context around search terms
        let bestContext = '';
        let bestScore = 0;
        
        // Split content into sentences
        const sentences = cleanContent.split(/[.!?]+/).filter(s => s.trim().length > 10);
        
        // Score each sentence based on query term matches
        sentences.forEach(sentence => {
            const lowerSentence = sentence.toLowerCase();
            let score = 0;
            
            queryTerms.forEach(term => {
                const matches = (lowerSentence.match(new RegExp(term, 'g')) || []).length;
                score += matches * (term.length / 10); // Longer terms get higher weight
            });
            
            if (score > bestScore) {
                bestScore = score;
                bestContext = sentence.trim();
            }
        });
        
        // If we found a good context, use it
        if (bestContext && bestContext.length <= maxLength) {
            return bestContext;
        }
        
        // Otherwise, find the position of the first query term and extract around it
        const firstTerm = queryTerms[0];
        const termIndex = cleanContent.toLowerCase().indexOf(firstTerm);
        
        if (termIndex !== -1) {
            const start = Math.max(0, termIndex - maxLength / 2);
            const end = Math.min(cleanContent.length, start + maxLength);
            let excerpt = cleanContent.substring(start, end);
            
            // Add ellipsis if we're not at the beginning/end
            if (start > 0) excerpt = '...' + excerpt;
            if (end < cleanContent.length) excerpt = excerpt + '...';
            
            return excerpt;
        }
        
        // Fallback to simple truncation
        return truncateText(cleanContent, maxLength);
    }
    
    function extractFirstImage(content) {
        if (!content) return '';
        
        // Look for img tags
        const imgMatch = content.match(/<img[^>]+src=["']([^"']+)["'][^>]*>/i);
        if (imgMatch) {
            return imgMatch[1];
        }
        
        // Look for WordPress image URLs in content
        const wpImageMatch = content.match(/https:\/\/[^"\s]+\.(jpg|jpeg|png|gif|webp)/i);
        if (wpImageMatch) {
            return wpImageMatch[0];
        }
        
        return '';
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
    
    window.bookmarkResult = function(resultId) {
        // Get bookmarked items from localStorage
        let bookmarks = JSON.parse(localStorage.getItem('hybrid-search-bookmarks') || '[]');
        
        if (bookmarks.includes(resultId)) {
            // Remove bookmark
            bookmarks = bookmarks.filter(id => id !== resultId);
            localStorage.setItem('hybrid-search-bookmarks', JSON.stringify(bookmarks));
            
            // Update button state
            const btn = event.target.closest('.bookmark-btn');
            btn.classList.remove('bookmarked');
            btn.title = 'Bookmark';
            btn.querySelector('.bookmark-icon').textContent = '🔖';
        } else {
            // Add bookmark
            bookmarks.push(resultId);
            localStorage.setItem('hybrid-search-bookmarks', JSON.stringify(bookmarks));
            
            // Update button state
            const btn = event.target.closest('.bookmark-btn');
            btn.classList.add('bookmarked');
            btn.title = 'Remove Bookmark';
            btn.querySelector('.bookmark-icon').textContent = '🔖';
        }
    }
    
    window.shareResult = function(url, title) {
        if (navigator.share) {
            // Use native share API if available
            navigator.share({
                title: title,
                url: url
            }).catch(err => {
                console.log('Error sharing:', err);
                fallbackShare(url, title);
            });
        } else {
            fallbackShare(url, title);
        }
    }
    
    function fallbackShare(url, title) {
        // Fallback: copy to clipboard
        const shareText = `${title}\n${url}`;
        
        navigator.clipboard.writeText(shareText).then(function() {
            // Show feedback
            const btn = event.target.closest('.share-btn');
            const originalIcon = btn.querySelector('.share-icon').textContent;
            btn.querySelector('.share-icon').textContent = '✅';
            btn.style.background = '#28a745';
            
            setTimeout(function() {
                btn.querySelector('.share-icon').textContent = originalIcon;
                btn.style.background = '';
            }, 2000);
        }).catch(function(err) {
            console.error('Failed to copy to clipboard:', err);
            alert('Failed to copy link to clipboard');
        });
    }
    
    function decodeHtmlEntities(text) {
        if (!text) return '';
        
        const textarea = document.createElement('textarea');
        textarea.innerHTML = text;
        return textarea.value;
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
            
            .search-input-container {
                position: relative;
            }
            
            .hybrid-search-form input[type="text"] {
                width: 100%;
                padding: 12px 60px 12px 16px;
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
            
            .suggestions-dropdown {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-top: none;
                border-radius: 0 0 16px 16px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.1),
                    0 2px 8px rgba(0, 0, 0, 0.05),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
                z-index: 1000;
                max-height: 400px;
                overflow-y: auto;
                display: none;
                margin-top: -1px;
                animation: slideDown 0.2s ease-out;
            }
            
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .suggestions-container {
                padding: 8px 0;
            }
            
            .suggestion-group {
                margin-bottom: 8px;
            }
            
            .suggestion-group:last-of-type {
                margin-bottom: 0;
            }
            
            .group-header {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px 4px;
                font-size: 0.75rem;
                font-weight: 600;
                color: #6c757d;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                margin-bottom: 4px;
            }
            
            .group-icon {
                font-size: 0.8rem;
                opacity: 0.8;
            }
            
            .group-title {
                flex: 1;
            }
            
            .group-items {
                list-style: none;
                margin: 0;
                padding: 0;
            }
            
            .suggestion-item {
                position: relative;
                cursor: pointer;
                transition: all 0.2s ease;
                border-radius: 8px;
                margin: 2px 8px;
                overflow: hidden;
            }
            
            .suggestion-item:hover {
                background: rgba(0, 124, 186, 0.08);
                transform: translateX(4px);
            }
            
            .suggestion-item.selected {
                background: linear-gradient(135deg, rgba(0, 124, 186, 0.15) 0%, rgba(0, 124, 186, 0.08) 100%);
                transform: translateX(6px);
                box-shadow: 0 2px 8px rgba(0, 124, 186, 0.2);
            }
            
            .suggestion-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                position: relative;
                z-index: 2;
            }
            
            .suggestion-text {
                flex: 1;
                font-size: 0.95rem;
                color: #2c3e50;
                font-weight: 500;
                line-height: 1.4;
            }
            
            .suggestion-action {
                font-size: 0.75rem;
                color: #6c757d;
                opacity: 0;
                transition: opacity 0.2s ease;
                font-weight: 500;
            }
            
            .suggestion-item:hover .suggestion-action,
            .suggestion-item.selected .suggestion-action {
                opacity: 1;
            }
            
            .suggestion-indicator {
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 3px;
                background: linear-gradient(180deg, #007cba 0%, #005a87 100%);
                transform: scaleY(0);
                transition: transform 0.2s ease;
                border-radius: 0 2px 2px 0;
            }
            
            .suggestion-item:hover .suggestion-indicator,
            .suggestion-item.selected .suggestion-indicator {
                transform: scaleY(1);
            }
            
            .history-suggestion .suggestion-indicator {
                background: linear-gradient(180deg, #6c757d 0%, #495057 100%);
            }
            
            .popular-suggestion .suggestion-indicator {
                background: linear-gradient(180deg, #fd7e14 0%, #e8590c 100%);
            }
            
            .suggestions-footer {
                padding: 8px 16px;
                border-top: 1px solid rgba(0, 0, 0, 0.05);
                margin-top: 8px;
            }
            
            .keyboard-hint {
                font-size: 0.7rem;
                color: #6c757d;
                display: flex;
                align-items: center;
                gap: 4px;
                justify-content: center;
            }
            
            .keyboard-hint kbd {
                background: rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 0.65rem;
                font-family: monospace;
                color: #495057;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
            }
            
            .suggestion-highlight {
                background: linear-gradient(120deg, rgba(255, 193, 7, 0.3) 0%, rgba(255, 193, 7, 0.2) 100%);
                padding: 2px 4px;
                border-radius: 4px;
                font-weight: 700;
                color: #856404;
                position: relative;
                overflow: hidden;
            }
            
            .suggestion-highlight::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
                animation: shimmer 2s infinite;
            }
            
            @keyframes shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            /* Related Results Styling */
            .related-results-section {
                margin-top: 40px;
                padding: 24px;
                background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                border-radius: 12px;
                border: 1px solid #e9ecef;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            }
            
            .related-results-title {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 0 0 20px 0;
                font-size: 1.2rem;
                font-weight: 600;
                color: #2c3e50;
            }
            
            .related-icon {
                font-size: 1.1rem;
            }
            
            .related-results-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 16px;
            }
            
            .related-result-item {
                background: white;
                border-radius: 8px;
                padding: 16px;
                border: 1px solid #e9ecef;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            
            .related-result-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                border-color: #007cba;
            }
            
            .related-result-title {
                margin: 0 0 8px 0;
                font-size: 1rem;
                font-weight: 600;
                color: #2c3e50;
                line-height: 1.4;
            }
            
            .related-result-excerpt {
                margin: 0 0 12px 0;
                font-size: 0.9rem;
                color: #6c757d;
                line-height: 1.5;
            }
            
            .related-result-meta {
                display: flex;
                gap: 12px;
                font-size: 0.8rem;
                color: #6c757d;
            }
            
            .related-result-type {
                background: #e9ecef;
                padding: 2px 8px;
                border-radius: 12px;
                font-weight: 500;
            }
            
            .related-result-date {
                font-weight: 500;
            }
            
            /* Search Controls */
            .search-controls {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 20px 0;
                padding: 16px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
            
            .search-sort {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .sort-label {
                font-weight: 600;
                color: #495057;
                margin-right: 8px;
            }
            
            .sort-btn {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 6px 12px;
                border: 1px solid #dee2e6;
                background: white;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 0.9rem;
                color: #495057;
            }
            
            .sort-btn:hover {
                border-color: #007cba;
                background: #f8f9fa;
            }
            
            .sort-btn.active {
                background: #007cba;
                border-color: #007cba;
                color: white;
            }
            
            .sort-icon {
                font-size: 0.8rem;
            }
            
            .search-stats {
                font-size: 0.9rem;
                color: #6c757d;
                font-weight: 500;
            }
            
            /* Date Range Filter */
            .date-range-filter {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .filter-label {
                font-weight: 600;
                color: #495057;
                font-size: 0.9rem;
            }
            
            .date-range-select {
                padding: 6px 12px;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
                font-size: 0.9rem;
                color: #495057;
                cursor: pointer;
                transition: border-color 0.2s;
            }
            
            .date-range-select:hover,
            .date-range-select:focus {
                border-color: #007cba;
                outline: none;
            }
            
            /* Enhanced Search Highlighting */
            .search-highlight {
                background: linear-gradient(120deg, #fff3cd 0%, #ffeaa7 100%);
                padding: 2px 4px;
                border-radius: 3px;
                font-weight: 600;
                color: #856404;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            
            .clear-search {
                position: absolute;
                right: 50px;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(220, 53, 69, 0.9);
                color: white;
                border: none;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                cursor: pointer;
                font-size: 12px;
                line-height: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
                z-index: 10;
                backdrop-filter: blur(10px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .clear-search:hover {
                background: rgba(200, 35, 51, 0.95);
                transform: translateY(-50%) scale(1.1);
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
            
            /* Enhanced Search Results */
            .search-result-item {
                display: flex;
                gap: 20px;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
                background: white;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .search-result-item::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
                height: 100%;
                background: linear-gradient(135deg, #007cba, #005a87);
                transform: scaleY(0);
                transition: transform 0.3s ease;
            }
            
            .search-result-item:hover {
                box-shadow: 0 8px 25px rgba(0, 124, 186, 0.15);
                border-color: #007cba;
                transform: translateY(-2px);
            }
            
            .search-result-item:hover::before {
                transform: scaleY(1);
            }
            
            .result-thumbnail {
                flex-shrink: 0;
                width: 150px;
                height: 100px;
                overflow: hidden;
                border-radius: 8px;
                position: relative;
                background: #f8f9fa;
            }
            
            .result-thumbnail img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.3s ease;
            }
            
            .search-result-item:hover .result-thumbnail img {
                transform: scale(1.05);
            }
            
            .result-overlay {
                position: absolute;
                top: 8px;
                left: 8px;
            }
            
            .result-type-badge {
                background: rgba(0, 124, 186, 0.9);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .result-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .result-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 15px;
            }
            
            .search-result-title {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 600;
                line-height: 1.4;
                flex: 1;
            }
            
            .search-result-title a {
                color: #2c3e50;
                text-decoration: none;
                transition: color 0.2s ease;
            }
            
            .search-result-title a:hover {
                color: #007cba;
            }
            
            .result-actions {
                display: flex;
                gap: 8px;
                flex-shrink: 0;
            }
            
            .bookmark-btn,
            .share-btn {
                width: 36px;
                height: 36px;
                border: 1px solid #dee2e6;
                background: white;
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
                font-size: 14px;
            }
            
            .bookmark-btn:hover,
            .share-btn:hover {
                background: #f8f9fa;
                border-color: #007cba;
                transform: translateY(-1px);
            }
            
            .bookmark-btn.bookmarked {
                background: #007cba;
                color: white;
                border-color: #007cba;
            }
            
            .search-result-meta {
                display: flex;
                gap: 16px;
                font-size: 0.875rem;
                color: #6c757d;
                flex-wrap: wrap;
            }
            
            .search-result-meta span {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            .result-type {
                background: #e3f2fd;
                color: #1976d2;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 500;
                text-transform: uppercase;
            }
            
            .result-author {
                color: #495057;
                font-weight: 500;
            }
            
            .result-date {
                color: #6c757d;
            }
            
            .reading-time {
                background: #f8f9fa;
                color: #495057;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 500;
            }
            
            .search-result-excerpt {
                color: #2c3e50;
                line-height: 1.8;
                font-size: 1rem;
                margin: 12px 0;
                padding: 16px 20px;
                background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                border-radius: 8px;
                position: relative;
                font-style: normal;
                font-weight: 400;
                letter-spacing: 0.3px;
                text-shadow: 0 1px 2px rgba(0,0,0,0.05);
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border: 1px solid #e9ecef;
            }
            
            .search-result-excerpt::after {
                content: '';
                position: absolute;
                top: 50%;
                right: 16px;
                transform: translateY(-50%);
                width: 20px;
                height: 20px;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23007cba"><path d="M14,17H7V15H14M17,13H7V11H17M17,9H7V7H17M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3Z"/></svg>') no-repeat center;
                background-size: contain;
                opacity: 0.3;
            }
            
            .result-taxonomy {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                align-items: center;
            }
            
            .search-result-categories,
            .search-result-tags {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .category-link,
            .tag-link {
                background: #f8f9fa;
                color: #495057;
                padding: 4px 10px;
                border-radius: 16px;
                text-decoration: none;
                font-size: 0.8rem;
                font-weight: 500;
                transition: all 0.2s ease;
                border: 1px solid #e9ecef;
            }
            
            .category-link:hover,
            .tag-link:hover {
                background: #007cba;
                color: white;
                border-color: #007cba;
                transform: translateY(-1px);
            }
            
            .result-footer {
                display: flex;
                justify-content: flex-end;
                align-items: center;
                margin-top: 8px;
                padding-top: 12px;
                border-top: 1px solid #f1f3f4;
            }
            
            .result-relevance {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .relevance-score {
                font-size: 0.8rem;
                color: #6c757d;
                font-weight: 500;
                min-width: 60px;
            }
            
            .relevance-bar {
                width: 80px;
                height: 4px;
                background: #e9ecef;
                border-radius: 2px;
                overflow: hidden;
            }
            
            .relevance-fill {
                height: 100%;
                background: linear-gradient(90deg, #28a745, #007cba);
                transition: width 0.3s ease;
            }
            
            .read-more-btn {
                background: #007cba;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 500;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            .read-more-btn:hover {
                background: #005a87;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 124, 186, 0.3);
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
                    gap: 16px;
                    padding: 20px;
                    margin-bottom: 16px;
                }
                
                .result-thumbnail {
                    width: 100%;
                    height: 180px;
                }
                
                .result-header {
                    flex-direction: column;
                    gap: 12px;
                }
                
                .result-actions {
                    align-self: flex-end;
                }
                
                .search-result-meta {
                    flex-wrap: wrap;
                    gap: 8px;
                    font-size: 0.8rem;
                }
                
                .search-result-excerpt {
                    padding: 14px 16px;
                    font-size: 0.95rem;
                    margin: 8px 0;
                    line-height: 1.7;
                }
                
                .search-result-excerpt::after {
                    width: 16px;
                    height: 16px;
                    right: 12px;
                }
                
                .result-footer {
                    flex-direction: column;
                    gap: 12px;
                    align-items: center;
                }
                
                .result-relevance {
                    justify-content: center;
                }
                
                .read-more-btn {
                    text-align: center;
                    justify-content: center;
                }
                
                .ai-answer-actions {
                    flex-direction: column;
                }
                
                .hybrid-search-form {
                    margin: 0 -15px 20px;
                    padding: 0 15px;
                }
                
                .search-controls {
                    flex-direction: column;
                    gap: 12px;
                    margin: 15px 0;
                    padding: 12px;
                }
                
                .search-sort {
                    justify-content: center;
                    gap: 6px;
                }
                
                .date-range-filter {
                    justify-content: center;
                }
                
                .sort-btn {
                    padding: 8px 10px;
                    font-size: 0.85rem;
                }
                
                .date-range-select {
                    padding: 8px 10px;
                    font-size: 0.85rem;
                }
                
                .search-stats {
                    text-align: center;
                    font-size: 0.85rem;
                }
                
                .suggestions-dropdown {
                    max-height: 250px;
                    border-radius: 0 0 12px 12px;
                }
                
                .suggestion-content {
                    padding: 10px 12px;
                }
                
                .suggestion-text {
                    font-size: 0.9rem;
                }
                
                .suggestion-action {
                    font-size: 0.7rem;
                }
                
                .group-header {
                    padding: 6px 12px 3px;
                    font-size: 0.7rem;
                }
                
                .keyboard-hint {
                    font-size: 0.65rem;
                    flex-wrap: wrap;
                    gap: 2px;
                }
                
                .keyboard-hint kbd {
                    font-size: 0.6rem;
                    padding: 1px 3px;
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
