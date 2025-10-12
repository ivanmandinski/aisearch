/**
 * Hybrid Search - Enhanced UI Components
 * Toast notifications, modals, animations, dark mode, etc.
 */

(function($) {
    'use strict';
    
    window.HybridSearchUI = window.HybridSearchUI || {};
    
    // =========================================================================
    // TOAST NOTIFICATIONS
    // =========================================================================
    window.HybridSearchUI.Toast = {
        container: null,
        
        init: function() {
            if ($('#hybrid-search-toast-container').length === 0) {
                this.container = $('<div>')
                    .attr('id', 'hybrid-search-toast-container')
                    .addClass('toast-container')
                    .appendTo('body');
            } else {
                this.container = $('#hybrid-search-toast-container');
            }
        },
        
        show: function(message, type = 'info', duration = 3000) {
            if (!this.container) {
                this.init();
            }
            
            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            };
            
            const $toast = $('<div>')
                .addClass(`toast toast-${type}`)
                .html(`
                    <span class="toast-icon">${icons[type] || icons.info}</span>
                    <span class="toast-message">${message}</span>
                    <button class="toast-close" aria-label="Close">×</button>
                `);
            
            // Close button
            $toast.find('.toast-close').on('click', () => {
                this.hide($toast);
            });
            
            // Add to container
            this.container.append($toast);
            
            // Auto-dismiss
            if (duration > 0) {
                setTimeout(() => {
                    this.hide($toast);
                }, duration);
            }
            
            return $toast;
        },
        
        hide: function($toast) {
            $toast.addClass('toast-out');
            setTimeout(() => {
                $toast.remove();
            }, 300);
        },
        
        success: function(message, duration) {
            return this.show(message, 'success', duration);
        },
        
        error: function(message, duration) {
            return this.show(message, 'error', duration);
        },
        
        warning: function(message, duration) {
            return this.show(message, 'warning', duration);
        },
        
        info: function(message, duration) {
            return this.show(message, 'info', duration);
        }
    };
    
    // =========================================================================
    // PREVIEW MODAL
    // =========================================================================
    window.HybridSearchUI.PreviewModal = {
        modal: null,
        
        init: function() {
            if ($('#hybrid-search-preview-modal').length === 0) {
                const $overlay = $('<div>')
                    .attr('id', 'hybrid-search-preview-modal')
                    .addClass('preview-modal-overlay')
                    .css('display', 'none')
                    .html(`
                        <div class="preview-modal" role="dialog" aria-modal="true" aria-labelledby="preview-title">
                            <div class="preview-header">
                                <div>
                                    <h2 id="preview-title" class="preview-title"></h2>
                                    <div class="preview-meta"></div>
                                </div>
                                <button class="preview-close" aria-label="Close preview">×</button>
                            </div>
                            <div class="preview-body">
                                <div class="preview-content"></div>
                            </div>
                            <div class="preview-footer">
                                <button class="action-btn">
                                    🔗 Copy Link
                                </button>
                                <button class="action-btn">
                                    ⭐ Save
                                </button>
                                <button class="action-btn-primary">
                                    → Read Full Article
                                </button>
                            </div>
                        </div>
                    `);
                
                $('body').append($overlay);
                this.modal = $overlay;
                
                // Click outside to close
                $overlay.on('click', (e) => {
                    if ($(e.target).hasClass('preview-modal-overlay')) {
                        this.hide();
                    }
                });
                
                // Close button
                $overlay.find('.preview-close').on('click', () => {
                    this.hide();
                });
                
                // Keyboard: Esc to close
                $(document).on('keydown', (e) => {
                    if (e.key === 'Escape' && this.modal && this.modal.is(':visible')) {
                        this.hide();
                    }
                });
            } else {
                this.modal = $('#hybrid-search-preview-modal');
            }
        },
        
        show: function(result) {
            if (!this.modal) {
                this.init();
            }
            
            // Update content
            this.modal.find('.preview-title').text(result.title);
            this.modal.find('.preview-meta').html(`
                <span>📄 ${result.type || 'Post'}</span>
                <span>•</span>
                <span>👤 ${result.author || 'Unknown'}</span>
                <span>•</span>
                <span>🕐 ${result.date || 'Unknown date'}</span>
                <span>•</span>
                <span>⭐ Score: ${(result.score * 100).toFixed(0)}%</span>
            `);
            
            // Get full content (or use excerpt as fallback)
            const content = result.content || result.excerpt || 'No preview available.';
            this.modal.find('.preview-content').html(`<p>${content}</p>`);
            
            // Update read full article link
            this.modal.find('.action-btn-primary').off('click').on('click', () => {
                window.open(result.url, '_blank');
                this.hide();
            });
            
            // Copy link button
            this.modal.find('.action-btn').first().off('click').on('click', () => {
                this.copyLink(result.url);
            });
            
            // Save button
            this.modal.find('.action-btn').eq(1).off('click').on('click', () => {
                this.saveResult(result);
            });
            
            // Show modal
            this.modal.fadeIn(200);
            $('body').css('overflow', 'hidden');
            
            // Focus close button for accessibility
            setTimeout(() => {
                this.modal.find('.preview-close').focus();
            }, 100);
        },
        
        hide: function() {
            if (this.modal) {
                this.modal.fadeOut(200);
                $('body').css('overflow', '');
            }
        },
        
        copyLink: function(url) {
            navigator.clipboard.writeText(url).then(() => {
                window.HybridSearchUI.Toast.success('✓ Link copied to clipboard!');
            }).catch(() => {
                window.HybridSearchUI.Toast.error('Failed to copy link');
            });
        },
        
        saveResult: function(result) {
            // Save to localStorage
            const saved = JSON.parse(localStorage.getItem('hybrid_search_saved') || '[]');
            
            if (!saved.find(s => s.id === result.id)) {
                saved.push({
                    id: result.id,
                    title: result.title,
                    url: result.url,
                    savedAt: new Date().toISOString()
                });
                localStorage.setItem('hybrid_search_saved', JSON.stringify(saved));
                window.HybridSearchUI.Toast.success('⭐ Saved to favorites!');
            } else {
                window.HybridSearchUI.Toast.info('Already in favorites');
            }
        }
    };
    
    // =========================================================================
    // DARK MODE TOGGLE
    // =========================================================================
    window.HybridSearchUI.DarkMode = {
        init: function() {
            // Create toggle if doesn't exist
            if ($('.dark-mode-toggle').length === 0) {
                const $toggle = $('<div>')
                    .addClass('dark-mode-toggle')
                    .html(`
                        <button data-theme="light">☀️ Light</button>
                        <button data-theme="dark">🌙 Dark</button>
                        <button data-theme="auto">⚙️ Auto</button>
                    `);
                
                $('body').append($toggle);
                
                // Bind click handlers
                $toggle.find('button').on('click', (e) => {
                    const theme = $(e.currentTarget).data('theme');
                    this.setTheme(theme);
                });
            }
            
            // Load saved preference
            const saved = localStorage.getItem('hybrid_search_theme') || 'auto';
            this.setTheme(saved);
        },
        
        setTheme: function(theme) {
            localStorage.setItem('hybrid_search_theme', theme);
            
            // Update active state
            $('.dark-mode-toggle button').removeClass('active');
            $(`.dark-mode-toggle button[data-theme="${theme}"]`).addClass('active');
            
            // Apply theme
            if (theme === 'dark') {
                $('html').attr('data-theme', 'dark');
            } else if (theme === 'light') {
                $('html').attr('data-theme', 'light');
            } else {
                // Auto: Use system preference
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                $('html').attr('data-theme', prefersDark ? 'dark' : 'light');
            }
        }
    };
    
    // =========================================================================
    // SKELETON LOADERS
    // =========================================================================
    window.HybridSearchUI.Skeleton = {
        show: function(count = 5) {
            const $container = $('#hybrid-search-results');
            $container.empty();
            
            for (let i = 0; i < count; i++) {
                const $skeleton = $(`
                    <div class="skeleton-result" style="--index: ${i}">
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-meta"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton-tags">
                            <div class="skeleton skeleton-tag"></div>
                            <div class="skeleton skeleton-tag"></div>
                            <div class="skeleton skeleton-tag"></div>
                        </div>
                    </div>
                `);
                $container.append($skeleton);
            }
        },
        
        hide: function() {
            $('.skeleton-result').fadeOut(200, function() {
                $(this).remove();
            });
        }
    };
    
    // =========================================================================
    // KEYWORD HIGHLIGHTING
    // =========================================================================
    window.HybridSearchUI.Highlighter = {
        highlight: function(text, keywords) {
            if (!text || !keywords) {
                return text;
            }
            
            // Split keywords by space
            const keywordArray = keywords.toLowerCase().split(/\s+/);
            let highlighted = text;
            
            keywordArray.forEach(keyword => {
                if (keyword.length < 3) return; // Skip short words
                
                const regex = new RegExp(`(${this.escapeRegex(keyword)})`, 'gi');
                highlighted = highlighted.replace(regex, '<span class="hybrid-search-highlight">$1</span>');
            });
            
            return highlighted;
        },
        
        escapeRegex: function(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        },
        
        highlightResults: function(results, query) {
            results.forEach(result => {
                const $result = $(`.hybrid-search-result[data-id="${result.id}"]`);
                if ($result.length) {
                    const $excerpt = $result.find('.hybrid-search-result-excerpt');
                    const highlighted = this.highlight($excerpt.text(), query);
                    $excerpt.html(highlighted);
                }
            });
        }
    };
    
    // =========================================================================
    // KEYBOARD SHORTCUTS
    // =========================================================================
    window.HybridSearchUI.Keyboard = {
        init: function() {
            // Add keyboard hint
            if ($('.keyboard-hint').length === 0) {
                $('<div>')
                    .addClass('keyboard-hint')
                    .html('Press <span class="kbd">?</span> for shortcuts')
                    .appendTo('body')
                    .on('click', () => this.showHelp());
            }
            
            // Global keyboard handlers
            $(document).on('keydown', (e) => {
                // Ctrl+K or / to focus search
                if ((e.ctrlKey && e.key === 'k') || e.key === '/') {
                    e.preventDefault();
                    $('#hybrid-search-input').focus();
                }
                
                // ? to show help
                if (e.key === '?' && !$(e.target).is('input, textarea')) {
                    e.preventDefault();
                    this.showHelp();
                }
            });
        },
        
        showHelp: function() {
            const helpHTML = `
                <div class="keyboard-shortcuts-modal">
                    <h3>⌨️ Keyboard Shortcuts</h3>
                    <div class="shortcuts-grid">
                        <div class="shortcut-group">
                            <h4>General</h4>
                            <div class="shortcut-item">
                                <span class="kbd">Ctrl</span> + <span class="kbd">K</span>
                                <span>Focus search</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">/</span>
                                <span>Focus search</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">Esc</span>
                                <span>Clear / Close</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">?</span>
                                <span>Show this help</span>
                            </div>
                        </div>
                        <div class="shortcut-group">
                            <h4>Navigation</h4>
                            <div class="shortcut-item">
                                <span class="kbd">↑</span> <span class="kbd">↓</span>
                                <span>Navigate suggestions</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">Enter</span>
                                <span>Select / Search</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">Tab</span>
                                <span>Next result</span>
                            </div>
                        </div>
                        <div class="shortcut-group">
                            <h4>Actions</h4>
                            <div class="shortcut-item">
                                <span class="kbd">P</span>
                                <span>Preview result</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">S</span>
                                <span>Save result</span>
                            </div>
                            <div class="shortcut-item">
                                <span class="kbd">C</span>
                                <span>Copy link</span>
                            </div>
                        </div>
                    </div>
                    <button class="action-btn" onclick="$(this).closest('.preview-modal-overlay').fadeOut(200)">
                        Close
                    </button>
                </div>
            `;
            
            const $modal = $('<div>')
                .addClass('preview-modal-overlay')
                .html(`<div class="preview-modal">${helpHTML}</div>`)
                .on('click', function(e) {
                    if ($(e.target).hasClass('preview-modal-overlay')) {
                        $(this).fadeOut(200);
                    }
                });
            
            $('body').append($modal);
            $modal.fadeIn(200);
            
            // Close on Esc
            $(document).one('keydown', function(e) {
                if (e.key === 'Escape') {
                    $modal.fadeOut(200, () => $modal.remove());
                }
            });
        }
    };
    
    // =========================================================================
    // ENHANCED LOADING STATES
    // =========================================================================
    window.HybridSearchUI.Loading = {
        showSkeleton: function(count = 5) {
            window.HybridSearchUI.Skeleton.show(count);
        },
        
        hideSkeleton: function() {
            window.HybridSearchUI.Skeleton.hide();
        },
        
        showButton: function($button) {
            $button.addClass('btn-loading').prop('disabled', true);
        },
        
        hideButton: function($button) {
            $button.removeClass('btn-loading').prop('disabled', false);
        },
        
        showProgressBar: function(containerId) {
            const $container = $(containerId);
            if ($container.find('.loading-bar').length === 0) {
                $container.append(`
                    <div class="loading-bar">
                        <div class="loading-bar-fill"></div>
                    </div>
                `);
            }
        },
        
        hideProgressBar: function(containerId) {
            $(containerId).find('.loading-bar').fadeOut(200, function() {
                $(this).remove();
            });
        }
    };
    
    // =========================================================================
    // RESULT ACTIONS
    // =========================================================================
    window.HybridSearchUI.Actions = {
        preview: function(result) {
            window.HybridSearchUI.PreviewModal.show(result);
        },
        
        copyLink: function(url, title) {
            navigator.clipboard.writeText(url).then(() => {
                window.HybridSearchUI.Toast.success('✓ Link copied!');
            }).catch(() => {
                // Fallback for older browsers
                const $temp = $('<input>').val(url).appendTo('body').select();
                document.execCommand('copy');
                $temp.remove();
                window.HybridSearchUI.Toast.success('✓ Link copied!');
            });
        },
        
        save: function(result) {
            const saved = JSON.parse(localStorage.getItem('hybrid_search_saved') || '[]');
            
            if (!saved.find(s => s.id === result.id)) {
                saved.push({
                    id: result.id,
                    title: result.title,
                    url: result.url,
                    savedAt: new Date().toISOString()
                });
                localStorage.setItem('hybrid_search_saved', JSON.stringify(saved));
                window.HybridSearchUI.Toast.success('⭐ Saved to favorites!');
            } else {
                window.HybridSearchUI.Toast.info('Already in favorites');
            }
        },
        
        share: function(result) {
            if (navigator.share) {
                navigator.share({
                    title: result.title,
                    text: result.excerpt,
                    url: result.url
                }).then(() => {
                    window.HybridSearchUI.Toast.success('✓ Shared successfully!');
                }).catch(() => {
                    // User cancelled, do nothing
                });
            } else {
                // Fallback: copy link
                this.copyLink(result.url, result.title);
            }
        }
    };
    
    // =========================================================================
    // EMPTY STATE HANDLER
    // =========================================================================
    window.HybridSearchUI.EmptyState = {
        show: function(query, suggestions = []) {
            const $container = $('#hybrid-search-results');
            
            let suggestionsHTML = '';
            if (suggestions && suggestions.length > 0) {
                suggestionsHTML = `
                    <div class="empty-state-suggestions">
                        <h4>💡 Try these instead:</h4>
                        <ul class="suggestion-list">
                            ${suggestions.map(s => `
                                <li onclick="$('#hybrid-search-input').val('${s}').closest('form').submit()">
                                    ${s}
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `;
            }
            
            const html = `
                <div class="hybrid-search-no-results fade-in">
                    <div class="empty-state-icon">🔍</div>
                    <h3 class="empty-state-title">No results found</h3>
                    <p class="empty-state-message">
                        We couldn't find anything for "<strong>${query}</strong>"
                    </p>
                    
                    ${suggestionsHTML}
                    
                    <div style="margin-top: 2rem;">
                        <button class="action-btn" onclick="$('#hybrid-search-input').val('').focus()">
                            🔍 Try a different search
                        </button>
                        <button class="action-btn" onclick="window.location.href='/'">
                            🏠 Browse all content
                        </button>
                    </div>
                </div>
            `;
            
            $container.html(html);
        }
    };
    
    // =========================================================================
    // SEARCH STATS BAR
    // =========================================================================
    window.HybridSearchUI.StatsBar = {
        show: function(query, totalResults, responseTime) {
            // Remove existing stats bar
            $('.hybrid-search-stats-bar').remove();
            
            const $statsBar = $(`
                <div class="hybrid-search-stats-bar fade-in">
                    <div class="stats-left">
                        <div class="stat-item">
                            <span class="stat-icon">📊</span>
                            Found <span class="stat-value">${totalResults}</span> results
                        </div>
                        <div class="stat-item">
                            <span class="stat-icon">⚡</span>
                            in <span class="stat-value">${(responseTime / 1000).toFixed(2)}s</span>
                        </div>
                    </div>
                    <div class="stats-right">
                        <select class="view-toggle-btn" onchange="window.HybridSearchUI.StatsBar.changeSort(this.value)">
                            <option value="relevance">Most Relevant</option>
                            <option value="date-desc">Newest First</option>
                            <option value="date-asc">Oldest First</option>
                            <option value="title">A-Z</option>
                        </select>
                    </div>
                </div>
            `);
            
            $('#hybrid-search-results').before($statsBar);
        },
        
        changeSort: function(sortBy) {
            // Trigger search with new sort
            console.log('Changing sort to:', sortBy);
            // Implement sort logic here
        }
    };
    
    // =========================================================================
    // INITIALIZE ALL UI COMPONENTS
    // =========================================================================
    $(document).ready(function() {
        console.log('Initializing Enhanced UI components...');
        
        // Initialize components
        window.HybridSearchUI.Toast.init();
        window.HybridSearchUI.PreviewModal.init();
        window.HybridSearchUI.DarkMode.init();
        window.HybridSearchUI.Keyboard.init();
        
        console.log('Enhanced UI components initialized ✓');
    });
    
})(jQuery);

