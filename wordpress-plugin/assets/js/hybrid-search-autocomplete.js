/**
 * Hybrid Search Autocomplete Module
 * Provides real-time search suggestions as user types
 */

(function($) {
    'use strict';
    
    // Autocomplete state
    let suggestionTimeout = null;
    let selectedSuggestionIndex = -1;
    let currentSuggestions = [];
    
    /**
     * Initialize autocomplete functionality
     */
    window.HybridSearch = window.HybridSearch || {};
    window.HybridSearch.Autocomplete = {
        
        init: function() {
            const $searchInput = $('#hybrid-search-input');
            
            if (!$searchInput.length) {
                return;
            }
            
            // Create suggestions container
            this.createSuggestionsContainer($searchInput);
            
            // Bind input handler
            $searchInput.on('input', (e) => this.handleInput(e));
            
            // Bind keyboard navigation
            $searchInput.on('keydown', (e) => this.handleKeyDown(e));
            
            // Hide suggestions on click outside
            $(document).on('click', (e) => this.handleClickOutside(e));
            
            console.log('Autocomplete initialized');
        },
        
        /**
         * Create suggestions dropdown container
         */
        createSuggestionsContainer: function($input) {
            if ($('#hybrid-search-suggestions').length) {
                return; // Already exists
            }
            
            const $container = $('<div>')
                .attr('id', 'hybrid-search-suggestions')
                .addClass('hybrid-search-suggestions')
                .css({
                    'position': 'absolute',
                    'display': 'none',
                    'background': '#fff',
                    'border': '1px solid #ddd',
                    'border-top': 'none',
                    'max-height': '300px',
                    'overflow-y': 'auto',
                    'z-index': 1000,
                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                    'width': $input.outerWidth() + 'px'
                });
            
            $input.after($container);
            
            // Update width on window resize
            $(window).on('resize', () => {
                $container.css('width', $input.outerWidth() + 'px');
            });
        },
        
        /**
         * Handle input event
         */
        handleInput: function(e) {
            const query = $(e.target).val().trim();
            
            // Clear previous timeout
            if (suggestionTimeout) {
                clearTimeout(suggestionTimeout);
            }
            
            // Hide suggestions if query too short
            if (query.length < 2) {
                this.hideSuggestions();
                return;
            }
            
            // Debounce: Wait 300ms before fetching suggestions
            suggestionTimeout = setTimeout(() => {
                this.fetchSuggestions(query);
            }, 300);
        },
        
        /**
         * Fetch suggestions from API
         */
        fetchSuggestions: async function(query) {
            try {
                const apiUrl = hybridSearch.apiUrl || '';
                
                if (!apiUrl) {
                    console.warn('API URL not configured');
                    return;
                }
                
                const response = await fetch(`${apiUrl}/suggest?query=${encodeURIComponent(query)}&limit=8`);
                
                if (!response.ok) {
                    throw new Error('Failed to fetch suggestions');
                }
                
                const data = await response.json();
                
                if (data.suggestions && data.suggestions.length > 0) {
                    this.displaySuggestions(data.suggestions, query);
                } else {
                    this.hideSuggestions();
                }
                
            } catch (error) {
                console.error('Error fetching suggestions:', error);
                this.hideSuggestions();
            }
        },
        
        /**
         * Display suggestions
         */
        displaySuggestions: function(suggestions, originalQuery) {
            const $container = $('#hybrid-search-suggestions');
            
            if (!$container.length) {
                return;
            }
            
            currentSuggestions = suggestions;
            selectedSuggestionIndex = -1;
            
            $container.empty();
            
            suggestions.forEach((suggestion, index) => {
                const $item = $('<div>')
                    .addClass('suggestion-item')
                    .attr('data-index', index)
                    .css({
                        'padding': '10px 15px',
                        'cursor': 'pointer',
                        'border-bottom': '1px solid #f0f0f0'
                    })
                    .on('mouseenter', function() {
                        $('.suggestion-item').removeClass('selected');
                        $(this).addClass('selected').css('background', '#f5f5f5');
                        selectedSuggestionIndex = index;
                    })
                    .on('mouseleave', function() {
                        $(this).removeClass('selected').css('background', '');
                    })
                    .on('click', () => this.selectSuggestion(suggestion));
                
                // Highlight matching part
                const highlightedText = this.highlightMatch(suggestion, originalQuery);
                $item.html(highlightedText);
                
                $container.append($item);
            });
            
            $container.show();
        },
        
        /**
         * Highlight matching text
         */
        highlightMatch: function(text, query) {
            const regex = new RegExp('(' + this.escapeRegex(query) + ')', 'gi');
            return text.replace(regex, '<strong>$1</strong>');
        },
        
        /**
         * Escape regex special characters
         */
        escapeRegex: function(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        },
        
        /**
         * Hide suggestions
         */
        hideSuggestions: function() {
            $('#hybrid-search-suggestions').hide();
            currentSuggestions = [];
            selectedSuggestionIndex = -1;
        },
        
        /**
         * Handle keyboard navigation
         */
        handleKeyDown: function(e) {
            const $container = $('#hybrid-search-suggestions');
            
            if (!$container.is(':visible') || currentSuggestions.length === 0) {
                return;
            }
            
            switch (e.keyCode) {
                case 38: // Up arrow
                    e.preventDefault();
                    this.navigateUp();
                    break;
                    
                case 40: // Down arrow
                    e.preventDefault();
                    this.navigateDown();
                    break;
                    
                case 13: // Enter
                    if (selectedSuggestionIndex >= 0) {
                        e.preventDefault();
                        this.selectSuggestion(currentSuggestions[selectedSuggestionIndex]);
                    }
                    break;
                    
                case 27: // Escape
                    e.preventDefault();
                    this.hideSuggestions();
                    break;
            }
        },
        
        /**
         * Navigate up in suggestions
         */
        navigateUp: function() {
            if (selectedSuggestionIndex > 0) {
                selectedSuggestionIndex--;
            } else {
                selectedSuggestionIndex = currentSuggestions.length - 1;
            }
            this.highlightSelectedSuggestion();
        },
        
        /**
         * Navigate down in suggestions
         */
        navigateDown: function() {
            if (selectedSuggestionIndex < currentSuggestions.length - 1) {
                selectedSuggestionIndex++;
            } else {
                selectedSuggestionIndex = 0;
            }
            this.highlightSelectedSuggestion();
        },
        
        /**
         * Highlight selected suggestion
         */
        highlightSelectedSuggestion: function() {
            $('.suggestion-item').removeClass('selected').css('background', '');
            
            const $selected = $('.suggestion-item[data-index="' + selectedSuggestionIndex + '"]');
            $selected.addClass('selected').css('background', '#f5f5f5');
            
            // Update input with selected suggestion
            if (selectedSuggestionIndex >= 0 && currentSuggestions[selectedSuggestionIndex]) {
                $('#hybrid-search-input').val(currentSuggestions[selectedSuggestionIndex]);
            }
        },
        
        /**
         * Select a suggestion
         */
        selectSuggestion: function(suggestion) {
            const $input = $('#hybrid-search-input');
            $input.val(suggestion);
            this.hideSuggestions();
            
            // Trigger search
            $input.closest('form').trigger('submit');
        },
        
        /**
         * Handle click outside
         */
        handleClickOutside: function(e) {
            const $container = $('#hybrid-search-suggestions');
            const $input = $('#hybrid-search-input');
            
            if (!$container.is(e.target) && 
                $container.has(e.target).length === 0 &&
                !$input.is(e.target)) {
                this.hideSuggestions();
            }
        }
    };
    
    // Initialize on document ready
    $(document).ready(function() {
        window.HybridSearch.Autocomplete.init();
    });
    
})(jQuery);

