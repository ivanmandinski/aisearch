/**
 * Hybrid Search - UI Integration
 * Connects search functionality with enhanced UI components
 */

(function($) {
    'use strict';
    
    let currentResults = [];
    let currentQuery = '';
    
    window.HybridSearchIntegration = {
        
        /**
         * Initialize integration
         */
        init: function() {
            console.log('Initializing Hybrid Search Integration...');
            
            // Hook into search form
            $('.hybrid-search-form').on('submit', (e) => {
                e.preventDefault();
                this.performSearch();
            });
            
            // Add voice search button if enabled
            if (hybridSearch.enableVoiceSearch) {
                this.addVoiceSearchButton();
            }
            
            // Add back to top button
            this.addBackToTopButton();
            
            // Monitor scroll for back-to-top
            $(window).on('scroll', () => {
                this.updateBackToTop();
            });
            
            console.log('Hybrid Search Integration initialized ✓');
        },
        
        /**
         * Perform search with enhanced UI
         */
        performSearch: function() {
            const query = $('#hybrid-search-input').val().trim();
            
            if (!query) {
                return;
            }
            
            currentQuery = query;
            
            // Show skeleton loaders
            window.HybridSearchUI.Loading.showSkeleton(5);
            
            // Show loading state on button
            const $submitBtn = $('.hybrid-search-submit');
            window.HybridSearchUI.Loading.showButton($submitBtn);
            
            // Perform AJAX search
            $.ajax({
                url: hybridSearch.ajaxUrl,
                type: 'POST',
                data: {
                    action: 'hybrid_search',
                    query: query,
                    limit: hybridSearch.maxResults || 10,
                    include_answer: hybridSearch.includeAnswer || false
                },
                success: (response) => {
                    this.handleSearchSuccess(response, query);
                },
                error: (error) => {
                    this.handleSearchError(error, query);
                },
                complete: () => {
                    window.HybridSearchUI.Loading.hideButton($submitBtn);
                }
            });
        },
        
        /**
         * Handle successful search
         */
        handleSearchSuccess: function(response, query) {
            console.log('Search response:', response);
            
            // Hide skeletons
            window.HybridSearchUI.Loading.hideSkeleton();
            
            if (response.success && response.data) {
                const data = response.data;
                currentResults = data.results || [];
                const metadata = data.metadata || {};
                
                // Show stats bar
                window.HybridSearchUI.StatsBar.show(
                    query,
                    metadata.total_results || currentResults.length,
                    metadata.response_time || 0
                );
                
                if (currentResults.length === 0) {
                    // Handle zero results
                    const suggestions = data.zero_result_handling?.suggestions || [];
                    window.HybridSearchUI.EmptyState.show(query, suggestions);
                } else {
                    // Render results
                    this.renderResults(currentResults, query, metadata);
                }
            } else {
                window.HybridSearchUI.Toast.error('Search failed: ' + (response.data?.message || 'Unknown error'));
            }
        },
        
        /**
         * Handle search error
         */
        handleSearchError: function(error, query) {
            console.error('Search error:', error);
            
            window.HybridSearchUI.Loading.hideSkeleton();
            
            window.HybridSearchUI.Toast.error('Search request failed. Please try again.');
            
            window.HybridSearchUI.EmptyState.show(query, []);
        },
        
        /**
         * Render search results with enhanced UI
         */
        renderResults: function(results, query, metadata) {
            const $container = $('#hybrid-search-results');
            $container.empty();
            
            // Render AI answer if available
            if (metadata.answer) {
                this.renderAIAnswer(metadata.answer, $container);
            }
            
            // Render each result with stagger animation
            results.forEach((result, index) => {
                const $result = this.createResultCard(result, index, query);
                $container.append($result);
            });
            
            // Highlight keywords after render
            setTimeout(() => {
                window.HybridSearchUI.Highlighter.highlightResults(results, query);
            }, 100);
        },
        
        /**
         * Create enhanced result card
         */
        createResultCard: function(result, index, query) {
            const score = result.score || 0;
            const scoreClass = score >= 0.8 ? 'high' : score >= 0.5 ? 'medium' : 'low';
            const scorePercent = Math.round(score * 100);
            
            const $card = $(`
                <div class="hybrid-search-result" data-id="${result.id}" style="--index: ${index}">
                    ${result.featured_image ? `
                        <div class="result-header">
                            <img src="${result.featured_image}" alt="${result.title}" class="result-thumbnail" loading="lazy">
                            <div class="result-main">
                    ` : '<div class="result-main">'}
                    
                    <h3 class="hybrid-search-result-title">
                        <a href="${result.url}" data-id="${result.id}" class="result-link">
                            ${result.title}
                        </a>
                        ${index === 0 ? '<span class="result-badge">🏅 Top Result</span>' : ''}
                    </h3>
                    
                    ${result.featured_image ? '</div></div>' : '</div>'}
                    
                    <div class="hybrid-search-result-meta">
                        <span class="hybrid-search-result-type">${result.type || 'post'}</span>
                        ${result.author ? `<span class="meta-item"><span class="meta-icon">👤</span> ${result.author}</span>` : ''}
                        ${result.date ? `<span class="meta-item"><span class="meta-icon">🕐</span> ${this.formatDate(result.date)}</span>` : ''}
                        <span class="hybrid-search-result-score hybrid-search-score-${scoreClass}">
                            ⭐ ${scorePercent}%
                        </span>
                    </div>
                    
                    <div class="hybrid-search-result-excerpt">
                        ${result.excerpt || 'No excerpt available.'}
                    </div>
                    
                    ${result.ai_reason ? `
                        <div class="ai-reasoning">
                            <div class="ai-reasoning-title">
                                <span>🤖</span> Why this result?
                            </div>
                            <div class="ai-reasoning-content">
                                ${result.ai_reason}
                            </div>
                            ${result.ai_score ? `
                                <div class="relevance-indicators">
                                    <div class="relevance-indicator">
                                        <span>Semantic:</span>
                                        <div class="indicator-bar">
                                            <div class="indicator-fill" style="width: ${Math.round(result.ai_score * 100)}%"></div>
                                        </div>
                                        <span>${Math.round(result.ai_score * 100)}%</span>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}
                    
                    ${result.categories && result.categories.length > 0 ? `
                        <div class="hybrid-search-result-categories">
                            ${result.categories.map(cat => `
                                <a href="#">🏷️ ${cat.name || cat}</a>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    <div class="result-actions">
                        <button class="action-btn preview-btn" data-result-id="${result.id}">
                            👁 Preview
                        </button>
                        <button class="action-btn copy-link-btn" data-url="${result.url}">
                            🔗 Copy Link
                        </button>
                        <button class="action-btn save-btn" data-result-id="${result.id}">
                            ⭐ Save
                        </button>
                        <a href="${result.url}" class="action-btn-primary" target="_blank">
                            → Read Full Article
                        </a>
                    </div>
                </div>
            `);
            
            // Bind action handlers
            $card.find('.preview-btn').on('click', () => {
                window.HybridSearchUI.Actions.preview(result);
            });
            
            $card.find('.copy-link-btn').on('click', () => {
                window.HybridSearchUI.Actions.copyLink(result.url, result.title);
            });
            
            $card.find('.save-btn').on('click', () => {
                window.HybridSearchUI.Actions.save(result);
            });
            
            // Track click
            $card.find('.result-link').on('click', () => {
                this.trackClick(result, index + 1, query);
            });
            
            return $card;
        },
        
        /**
         * Render AI answer box
         */
        renderAIAnswer: function(answer, $container) {
            const $answerBox = $(`
                <div class="hybrid-search-ai-answer fade-in">
                    <div class="ai-answer-header">
                        <h3 class="ai-answer-title">
                            <span>🤖</span> AI Answer
                        </h3>
                        <div class="ai-answer-actions">
                            <button class="ai-answer-btn copy-answer-btn">
                                📋 Copy
                            </button>
                            <button class="ai-answer-btn read-answer-btn">
                                🔊 Read Aloud
                            </button>
                        </div>
                    </div>
                    <div class="ai-answer-body">
                        <p>${answer}</p>
                    </div>
                    <div class="ai-answer-sources">
                        <small>Generated by AI based on search results • Powered by Cerebras</small>
                    </div>
                </div>
            `);
            
            // Copy answer button
            $answerBox.find('.copy-answer-btn').on('click', () => {
                navigator.clipboard.writeText(answer).then(() => {
                    window.HybridSearchUI.Toast.success('✓ Answer copied!');
                });
            });
            
            // Read aloud button
            $answerBox.find('.read-answer-btn').on('click', () => {
                this.readAloud(answer);
            });
            
            $container.append($answerBox);
        },
        
        /**
         * Add voice search button
         */
        addVoiceSearchButton: function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                return; // Voice not supported
            }
            
            const $voiceBtn = $(`
                <button class="voice-search-btn" type="button" aria-label="Voice search" title="Voice search">
                    🎤
                </button>
            `);
            
            $('.hybrid-search-input-wrapper').append($voiceBtn);
            
            $voiceBtn.on('click', () => {
                this.startVoiceSearch();
            });
        },
        
        /**
         * Start voice search
         */
        startVoiceSearch: function() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            
            recognition.lang = 'en-US';
            recognition.continuous = false;
            recognition.interimResults = false;
            
            // Show recording indicator
            const $indicator = $(`
                <div class="voice-recording-indicator">
                    <div class="voice-waveform">
                        <div class="voice-bar"></div>
                        <div class="voice-bar"></div>
                        <div class="voice-bar"></div>
                        <div class="voice-bar"></div>
                        <div class="voice-bar"></div>
                    </div>
                    <p>Listening...</p>
                    <small>Speak your search query</small>
                </div>
            `);
            $('body').append($indicator);
            
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                $('#hybrid-search-input').val(transcript);
                $indicator.remove();
                window.HybridSearchUI.Toast.success(`✓ Heard: "${transcript}"`);
                $('.hybrid-search-form').submit();
            };
            
            recognition.onerror = () => {
                $indicator.remove();
                window.HybridSearchUI.Toast.error('Voice search failed. Please try again.');
            };
            
            recognition.onend = () => {
                $indicator.remove();
            };
            
            recognition.start();
        },
        
        /**
         * Read text aloud
         */
        readAloud: function(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'en-US';
                utterance.rate = 1.0;
                speechSynthesis.speak(utterance);
                window.HybridSearchUI.Toast.info('🔊 Reading aloud...');
            } else {
                window.HybridSearchUI.Toast.warning('Text-to-speech not supported');
            }
        },
        
        /**
         * Track click analytics
         */
        trackClick: function(result, position, query) {
            $.ajax({
                url: hybridSearch.ajaxUrl,
                type: 'POST',
                data: {
                    action: 'track_search_ctr',
                    ctr_data: {
                        result_id: result.id,
                        result_title: result.title,
                        result_url: result.url,
                        result_position: position,
                        result_score: result.score,
                        query: query
                    }
                }
            });
        },
        
        /**
         * Add back to top button
         */
        addBackToTopButton: function() {
            if ($('.back-to-top').length === 0) {
                const $btn = $(`
                    <button class="back-to-top" aria-label="Back to top">
                        ↑
                    </button>
                `);
                
                $btn.on('click', () => {
                    $('html, body').animate({ scrollTop: 0 }, 600);
                });
                
                $('body').append($btn);
            }
        },
        
        /**
         * Update back to top button visibility
         */
        updateBackToTop: function() {
            const $btn = $('.back-to-top');
            if ($(window).scrollTop() > 300) {
                $btn.addClass('visible');
            } else {
                $btn.removeClass('visible');
            }
        },
        
        /**
         * Format date nicely
         */
        formatDate: function(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) {
                return 'Today';
            } else if (diffDays === 1) {
                return 'Yesterday';
            } else if (diffDays < 7) {
                return `${diffDays} days ago`;
            } else if (diffDays < 30) {
                const weeks = Math.floor(diffDays / 7);
                return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
            } else if (diffDays < 365) {
                const months = Math.floor(diffDays / 30);
                return `${months} month${months > 1 ? 's' : ''} ago`;
            } else {
                return date.toLocaleDateString();
            }
        },
        
        /**
         * Add clear button functionality
         */
        initClearButton: function() {
            const $input = $('#hybrid-search-input');
            const $clearBtn = $('.clear-search');
            
            $input.on('input', function() {
                if ($(this).val().length > 0) {
                    $clearBtn.addClass('visible');
                } else {
                    $clearBtn.removeClass('visible');
                }
            });
            
            $clearBtn.on('click', function() {
                $input.val('').focus();
                $clearBtn.removeClass('visible');
                $('#hybrid-search-results').empty();
                $('.hybrid-search-stats-bar').remove();
            });
        }
    };
    
    // =========================================================================
    // AUTO-INITIALIZE ON DOCUMENT READY
    // =========================================================================
    $(document).ready(function() {
        // Only initialize on search pages
        if ($('.hybrid-search-container').length > 0) {
            window.HybridSearchIntegration.init();
            window.HybridSearchIntegration.initClearButton();
        }
    });
    
})(jQuery);

