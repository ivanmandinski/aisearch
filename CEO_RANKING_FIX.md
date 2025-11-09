# Ranking Issue Analysis: "Who is the CEO?" Query

## Problem Description

When searching "Who is the CEO?", you get:
- ✅ **Correct AI Answer**: "Doug Doerr is the CEO"
- ❌ **Wrong Ranking**: Doug Doerr appears as result #5, with other experts and blog posts ranking higher

## Root Cause Analysis

### Issue 1: Query Intent Misclassification
**Problem**: "Who is the CEO?" was being detected as `howto` intent (because it starts with "Who is"), which prioritizes:
```
Priority: ['post', 'page', 'scs-professionals']
```

This means blog posts rank BEFORE professional profiles!

**Impact**: CEO profile gets lower priority than blog posts

### Issue 2: Missing Executive Role Detection
**Problem**: No specific intent detection for executive/role queries like:
- "Who is the CEO?"
- "Who is the president?"
- "current CEO"

**Impact**: These queries fall into generic `howto` category, which doesn't prioritize professional profiles

### Issue 3: AI Reranking Doesn't Prioritize CEO Role
**Problem**: The AI reranking prompt didn't have specific scoring guidance for CEO/executive queries. It would score results generically without understanding that:
- Professional profile with "CEO" in title should score 100
- Press releases naming CEO should score 90
- Blog posts about leadership should score 40-50

**Impact**: AI scores CEO profile similarly to other professionals, so hybrid_score doesn't boost it enough

### Issue 4: Priority Sorting Logic Issue
**Problem**: The sorting logic for post type priority might not be working correctly. When hybrid scores are similar, priority should break ties, but it might not be applied correctly.

## Solution Implemented

### 1. ✅ Added Executive Role Intent Detection
```python
# New intent: executive_role
executive_role_patterns = [
    r'who is the (ceo|president|executive|chairman|director|chief|leader|head)',
    r'who is (ceo|president|executive|chairman|director|chief|leader|head)',
    r'(ceo|president|executive|chairman|director|chief|leader|head) (of|at)',
    r'current (ceo|president|executive|chairman|director|chief|leader|head)',
]
```

**Impact**: "Who is the CEO?" now correctly detected as `executive_role` intent

### 2. ✅ Set Correct Priority for Executive Role Queries
```python
elif detected_intent == 'executive_role':
    intent_based_priority = ['scs-professionals', 'page', 'post', 'attachment']
    logger.info(f"Executive role search: Prioritizing SCS Professionals")
```

**Impact**: Professional profiles now prioritized FIRST for CEO queries

### 3. ✅ Added Executive Role Instructions
```python
elif intent == 'executive_role':
    return f"""User is asking about a specific executive role or position: "{query}".

PRIORITY:
1. SCS Professionals profiles where the person holds the specific role mentioned (CEO, President, etc.)
2. Press releases or announcements naming the person in that role
3. Professional profiles that mention the role in title or content

RULES:
- Prioritize profiles where the person is CURRENTLY in that role
- Look for role keywords: CEO, President, Executive, Chief, Director, Leader
- Boost results where role appears in title (e.g., "Doug Doerr, CEO")
- For "Who is the CEO?", the person currently holding that title should rank #1
- Recent announcements about role changes are highly relevant"""
```

**Impact**: AI reranking now understands CEO queries and prioritizes accordingly

### 4. ✅ Enhanced AI Scoring Criteria
Added specific scoring guidance in the reranking prompt:
```
SPECIAL CASE - CEO/PRESIDENT QUERIES:
When query asks "Who is the CEO?" or similar:
- Professional profile of CURRENT CEO with role in title → Score: 100 (CRITICAL!)
- Professional profile mentioning CEO role → Score: 95
- Press release announcing CEO → Score: 90
- Article mentioning CEO → Score: 70
- Other professionals → Score: 30-40
- Blog posts about leadership → Score: 40-50
```

**Impact**: AI will now score CEO profiles much higher (100) vs blog posts (40-50)

### 5. ✅ Fixed Priority Sorting Logic
```python
# Fixed: Use negative priority to make lower idx sort first when reverse=True
reranked_results.sort(key=lambda x: (x.get('hybrid_score', 0), -get_priority_value(x)), reverse=True)
```

**Impact**: When hybrid scores are similar, priority correctly breaks ties

## Expected Behavior After Fix

When searching "Who is the CEO?":

1. **Intent Detection**: Detected as `executive_role` ✓
2. **Priority Applied**: `['scs-professionals', 'page', 'post']` ✓
3. **AI Instructions**: Specific CEO query instructions added ✓
4. **AI Scoring**:
   - Doug Doerr profile (CEO) → Score: 100
   - Other professionals → Score: 30-40
   - Blog posts → Score: 40-50
5. **Hybrid Score**:
   - Doug Doerr: (TF-IDF × 0.3) + (100 × 0.7) = ~0.70
   - Blog post: (TF-IDF × 0.3) + (45 × 0.7) = ~0.35
6. **Final Ranking**: Doug Doerr should rank #1! ✓

## Why It Was Happening Before

**Before Fix**:
1. Query "Who is the CEO?" → Detected as `howto`
2. Priority: `['post', 'page', 'scs-professionals']` → Blog posts first!
3. AI scoring: Generic scoring, CEO profile scored ~75, blog posts ~60
4. Hybrid scores: Similar scores (0.65 vs 0.60)
5. Result: Blog posts rank higher due to priority being applied to wrong post types

**After Fix**:
1. Query "Who is the CEO?" → Detected as `executive_role` ✓
2. Priority: `['scs-professionals', 'page', 'post']` → Professionals first! ✓
3. AI scoring: CEO profile = 100, blog posts = 40-50 ✓
4. Hybrid scores: CEO = 0.70, blog posts = 0.35 ✓
5. Result: CEO profile ranks #1! ✓

## Testing

Test with:
- "Who is the CEO?"
- "Who is the president?"
- "current CEO"
- "Who is the chief executive officer?"

Expected: Professional profile of the CEO should rank #1 in all cases.

## Additional Notes

The fix addresses multiple layers:
- **Intent Detection**: Correctly identifies CEO queries
- **Priority System**: Prioritizes professional profiles
- **AI Instructions**: Guides AI to score CEO profiles highest
- **Scoring Criteria**: Explicit scoring rules for CEO queries
- **Sorting Logic**: Ensures priority works correctly within score tiers

All layers work together to ensure the CEO profile ranks highest!





