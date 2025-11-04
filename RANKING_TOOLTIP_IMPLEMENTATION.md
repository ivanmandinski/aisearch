# Admin Ranking Tooltip Implementation Plan

## Overview
Add tooltips for admin users that explain why each search result is ranked at its position. This will help admins understand the ranking algorithm and debug search issues.

## Implementation Steps

### Step 1: Backend - Add Ranking Explanation Metadata

#### 1.1 Enhance `cerebras_llm.py` - Add ranking explanation to each result

**Location**: `cerebras_llm.py` in `rerank_results_async()` method

**Changes**:
- After calculating hybrid_score, add `ranking_explanation` field to each result
- Include: TF-IDF score, AI score, hybrid score, post type priority, AI reason, position

**Code to add** (around line 693-704):
```python
# After calculating hybrid_score
if ai_result:
    tfidf_score = result.get('score', 0.0)
    ai_score = ai_result['ai_score'] / 100
    
    tfidf_weight = 1.0 - ai_weight
    hybrid_score = (tfidf_score * tfidf_weight) + (ai_score * ai_weight)
    
    result['ai_score'] = ai_score
    result['ai_reason'] = ai_result.get('reason', '')
    result['hybrid_score'] = hybrid_score
    result['score'] = hybrid_score
    
    # NEW: Add ranking explanation for admin users
    result['ranking_explanation'] = {
        'tfidf_score': round(tfidf_score, 4),
        'ai_score': round(ai_score, 4),
        'ai_score_raw': ai_result['ai_score'],  # 0-100 scale
        'hybrid_score': round(hybrid_score, 4),
        'tfidf_weight': round(tfidf_weight, 2),
        'ai_weight': round(ai_weight, 2),
        'ai_reason': ai_result.get('reason', ''),
        'post_type': result.get('type', 'unknown'),
        'position_before_priority': None,  # Will be set after sorting
    }
else:
    result['ranking_explanation'] = {
        'tfidf_score': round(result.get('score', 0.0), 4),
        'ai_score': None,
        'ai_score_raw': None,
        'hybrid_score': round(result.get('score', 0.0), 4),
        'tfidf_weight': 1.0,
        'ai_weight': 0.0,
        'ai_reason': 'No AI scoring available',
        'post_type': result.get('type', 'unknown'),
        'position_before_priority': None,
    }
```

#### 1.2 Add position and priority info after sorting

**Location**: After sorting (around line 717)

**Code to add**:
```python
# After sorting, add position and priority info
priority_map = {}
if post_type_priority and len(post_type_priority) > 0:
    priority_map = {post_type: idx for idx, post_type in enumerate(post_type_priority)}

for idx, result in enumerate(reranked_results):
    if 'ranking_explanation' in result:
        result['ranking_explanation']['final_position'] = idx + 1
        result['ranking_explanation']['post_type_priority'] = priority_map.get(result.get('type', ''), 9999)
        result['ranking_explanation']['priority_order'] = post_type_priority if post_type_priority else []
```

#### 1.3 Add query intent to metadata

**Location**: `simple_hybrid_search.py` in `search()` method

**Changes**: Pass detected intent to metadata

**Code to add** (around line 404-417):
```python
detected_intent = self.detect_query_intent(query)
logger.info(f"🎯 Query intent detected: {detected_intent}")

# ... existing code ...

# When returning results, add intent to metadata
metadata['query_intent'] = detected_intent
metadata['intent_instructions'] = intent_instructions if intent_instructions else None
```

### Step 2: Backend - Pass Admin Status to Frontend

#### 2.1 Detect admin in WordPress plugin

**Location**: `wordpress-plugin/includes/API/SearchAPI.php`

**Code to add** (in `processSearchResults()` method or where results are processed):
```php
// Add admin status to results
$is_admin = current_user_can('manage_options');
$processed_result['is_admin'] = $is_admin;

// If admin, include ranking explanation
if ($is_admin && isset($result['ranking_explanation'])) {
    $processed_result['ranking_explanation'] = $result['ranking_explanation'];
}
```

#### 2.2 Add admin status to frontend config

**Location**: `wordpress-plugin/includes/Frontend/FrontendManager.php`

**Code to add** (in `enqueueFrontendAssets()` or where JS is localized):
```php
wp_localize_script('hybrid-search-js', 'hybridSearchConfig', [
    // ... existing config ...
    'isAdmin' => current_user_can('manage_options'),
    'showRankingTooltips' => current_user_can('manage_options'),
]);
```

### Step 3: Frontend - Add Tooltip Component

#### 3.1 Create tooltip HTML structure

**Location**: `wordpress-plugin/assets/hybrid-search-consolidated.js`

**Function to add**:
```javascript
function createRankingTooltip(rankingData, position) {
    if (!rankingData) return '';
    
    const {
        tfidf_score,
        ai_score,
        ai_score_raw,
        hybrid_score,
        tfidf_weight,
        ai_weight,
        ai_reason,
        post_type,
        post_type_priority,
        priority_order
    } = rankingData;
    
    const hasAiScore = ai_score !== null && ai_score !== undefined;
    const scoreBreakdown = hasAiScore 
        ? `(${tfidf_score.toFixed(3)} × ${tfidf_weight.toFixed(1)} + ${ai_score.toFixed(3)} × ${ai_weight.toFixed(1)})`
        : '';
    
    return `
        <div class="ranking-tooltip" data-position="${position}">
            <div class="ranking-tooltip-header">
                <span class="ranking-position">#${position}</span>
                <span class="ranking-final-score">Final Score: ${hybrid_score.toFixed(4)}</span>
            </div>
            <div class="ranking-tooltip-body">
                <div class="ranking-section">
                    <strong>Score Breakdown:</strong>
                    <div class="ranking-score-item">
                        <span class="score-label">TF-IDF Score:</span>
                        <span class="score-value">${tfidf_score.toFixed(4)}</span>
                        <span class="score-weight">(${(tfidf_weight * 100).toFixed(0)}% weight)</span>
                    </div>
                    ${hasAiScore ? `
                    <div class="ranking-score-item">
                        <span class="score-label">AI Score:</span>
                        <span class="score-value">${ai_score.toFixed(4)}</span>
                        <span class="score-weight">(${(ai_weight * 100).toFixed(0)}% weight)</span>
                        <span class="score-raw">(${ai_score_raw}/100)</span>
                    </div>
                    <div class="ranking-score-item">
                        <span class="score-label">Hybrid Score:</span>
                        <span class="score-value">${hybrid_score.toFixed(4)}</span>
                        <span class="score-formula">${scoreBreakdown}</span>
                    </div>
                    ` : `
                    <div class="ranking-score-item">
                        <span class="score-label">Final Score:</span>
                        <span class="score-value">${hybrid_score.toFixed(4)}</span>
                        <span class="score-note">(TF-IDF only, AI reranking not used)</span>
                    </div>
                    `}
                </div>
                
                ${hasAiScore && ai_reason ? `
                <div class="ranking-section">
                    <strong>AI Reasoning:</strong>
                    <div class="ranking-reason">${escapeHtml(ai_reason)}</div>
                </div>
                ` : ''}
                
                <div class="ranking-section">
                    <strong>Post Type Priority:</strong>
                    <div class="ranking-priority">
                        <span class="post-type">${post_type}</span>
                        ${priority_order && priority_order.length > 0 ? `
                            <span class="priority-order">
                                Priority: ${priority_order.indexOf(post_type) !== -1 ? priority_order.indexOf(post_type) + 1 : 'N/A'} 
                                (${priority_order.join(' > ')})
                            </span>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}
```

#### 3.2 Add tooltip trigger icon to results

**Location**: `wordpress-plugin/assets/hybrid-search-consolidated.js` in `buildResultHTML()`

**Code to add** (in the result HTML building):
```javascript
// Add tooltip trigger for admin users
if (window.hybridSearchConfig && window.hybridSearchConfig.isAdmin && result.ranking_explanation) {
    html += `<span class="ranking-tooltip-trigger" data-result-position="${position}" title="Click to see ranking explanation">ℹ️</span>`;
}
```

#### 3.3 Add tooltip event handlers

**Location**: `wordpress-plugin/assets/hybrid-search-consolidated.js`

**Code to add**:
```javascript
function initRankingTooltips(container) {
    if (!window.hybridSearchConfig || !window.hybridSearchConfig.isAdmin) {
        return;
    }
    
    container.querySelectorAll('.ranking-tooltip-trigger').forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const position = this.getAttribute('data-result-position');
            const resultElement = this.closest('.hybrid-search-result');
            const resultData = window.currentSearchResults?.[parseInt(position) - 1];
            
            if (!resultData || !resultData.ranking_explanation) {
                return;
            }
            
            // Remove existing tooltip
            const existingTooltip = container.querySelector('.ranking-tooltip-active');
            if (existingTooltip) {
                existingTooltip.remove();
            }
            
            // Create and show tooltip
            const tooltip = document.createElement('div');
            tooltip.className = 'ranking-tooltip-active';
            tooltip.innerHTML = createRankingTooltip(resultData.ranking_explanation, position);
            
            // Position tooltip near the trigger
            const rect = this.getBoundingClientRect();
            tooltip.style.position = 'fixed';
            tooltip.style.top = `${rect.bottom + 5}px`;
            tooltip.style.left = `${rect.left}px`;
            tooltip.style.zIndex = '9999';
            
            document.body.appendChild(tooltip);
            
            // Close tooltip on click outside or ESC
            const closeTooltip = (e) => {
                if (!tooltip.contains(e.target) && e.target !== trigger) {
                    tooltip.remove();
                    document.removeEventListener('click', closeTooltip);
                    document.removeEventListener('keydown', closeEsc);
                }
            };
            
            const closeEsc = (e) => {
                if (e.key === 'Escape') {
                    tooltip.remove();
                    document.removeEventListener('click', closeTooltip);
                    document.removeEventListener('keydown', closeEsc);
                }
            };
            
            setTimeout(() => {
                document.addEventListener('click', closeTooltip);
                document.addEventListener('keydown', closeEsc);
            }, 100);
        });
    });
}

// Call after rendering results
function renderResults(results, container) {
    // ... existing render code ...
    initRankingTooltips(container);
}
```

### Step 4: Frontend - Add CSS Styling

#### 4.1 Add tooltip styles

**Location**: `wordpress-plugin/assets/hybrid-search-consolidated.css`

**CSS to add**:
```css
/* Ranking Tooltip Styles */
.ranking-tooltip-trigger {
    display: inline-block;
    cursor: help;
    margin-left: 8px;
    font-size: 14px;
    opacity: 0.6;
    transition: opacity 0.2s;
    vertical-align: middle;
}

.ranking-tooltip-trigger:hover {
    opacity: 1;
}

.ranking-tooltip-active {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 16px;
    max-width: 400px;
    font-size: 13px;
    line-height: 1.5;
    color: #334155;
    z-index: 9999;
}

.ranking-tooltip-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}

.ranking-position {
    font-weight: 700;
    font-size: 16px;
    color: #1e293b;
}

.ranking-final-score {
    font-weight: 600;
    color: #3b82f6;
}

.ranking-tooltip-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.ranking-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.ranking-section strong {
    color: #1e293b;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.ranking-score-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    background: #f8fafc;
    border-radius: 4px;
}

.score-label {
    font-weight: 500;
    min-width: 100px;
}

.score-value {
    font-weight: 600;
    color: #3b82f6;
    font-family: 'Courier New', monospace;
}

.score-weight {
    color: #64748b;
    font-size: 11px;
}

.score-raw {
    color: #94a3b8;
    font-size: 11px;
    font-style: italic;
}

.score-formula {
    color: #64748b;
    font-size: 11px;
    font-family: 'Courier New', monospace;
}

.score-note {
    color: #94a3b8;
    font-size: 11px;
    font-style: italic;
}

.ranking-reason {
    padding: 8px;
    background: #f1f5f9;
    border-left: 3px solid #3b82f6;
    border-radius: 4px;
    font-style: italic;
    color: #475569;
}

.ranking-priority {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: #eff6ff;
    border-radius: 4px;
}

.post-type {
    font-weight: 600;
    color: #1e40af;
    padding: 2px 6px;
    background: #dbeafe;
    border-radius: 3px;
}

.priority-order {
    color: #64748b;
    font-size: 11px;
}
```

### Step 5: Store Current Results for Tooltip Access

**Location**: `wordpress-plugin/assets/hybrid-search-consolidated.js`

**Code to add**:
```javascript
// Store current results globally for tooltip access
window.currentSearchResults = [];

function renderResults(results, container) {
    // Store results
    window.currentSearchResults = results;
    
    // ... existing render code ...
    initRankingTooltips(container);
}
```

## Data Flow

1. **Backend (Python)**:
   - `cerebras_llm.py` calculates scores and adds `ranking_explanation` to each result
   - `simple_hybrid_search.py` adds query intent to metadata
   
2. **Backend (PHP)**:
   - `SearchAPI.php` checks if user is admin and includes `ranking_explanation` if admin
   - `FrontendManager.php` passes `isAdmin` flag to JavaScript
   
3. **Frontend (JavaScript)**:
   - Checks `window.hybridSearchConfig.isAdmin`
   - Adds tooltip trigger icon to results if admin
   - Shows tooltip on click with ranking explanation

## Example Tooltip Content

```
┌─────────────────────────────────────┐
│ #5    Final Score: 0.7562           │
├─────────────────────────────────────┤
│ SCORE BREAKDOWN:                     │
│ TF-IDF Score: 0.8234  (30% weight)  │
│ AI Score: 0.7123  (70% weight)     │
│            (89/100)                  │
│ Hybrid Score: 0.7562                 │
│ (0.8234 × 0.3 + 0.7123 × 0.7)       │
├─────────────────────────────────────┤
│ AI REASONING:                        │
│ Direct answer to query with detailed │
│ technical analysis                   │
├─────────────────────────────────────┤
│ POST TYPE PRIORITY:                  │
│ scs-professionals                    │
│ Priority: 1 (scs-professionals >    │
│            page > post)              │
└─────────────────────────────────────┘
```

## Testing Checklist

- [ ] Admin users see tooltip trigger icon (ℹ️)
- [ ] Non-admin users don't see tooltip trigger
- [ ] Tooltip shows correct scores
- [ ] Tooltip shows AI reasoning when available
- [ ] Tooltip shows post type priority
- [ ] Tooltip closes on click outside
- [ ] Tooltip closes on ESC key
- [ ] Tooltip positioned correctly
- [ ] Works with pagination
- [ ] Works with different query types

## Security Considerations

- ✅ Only show ranking data to admins (`current_user_can('manage_options')`)
- ✅ Sanitize all output in PHP
- ✅ Escape HTML in JavaScript tooltip content
- ✅ Don't expose sensitive internal scoring details to non-admins

## Performance Considerations

- Ranking explanation is only added when user is admin
- Minimal impact on performance (just adding metadata fields)
- Tooltip only rendered on click (not on page load)

## Future Enhancements

1. Add query intent display in tooltip
2. Show comparison with other results
3. Add color coding for score ranges
4. Export ranking data for analysis
5. Add visual score bars/graphs



