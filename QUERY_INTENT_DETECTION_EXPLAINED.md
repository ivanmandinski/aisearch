# Query Intent Detection - Complete Explanation

## What Is Query Intent Detection?

**Query Intent Detection** tells you WHAT the user is looking for, so the search can return the RIGHT type of content.

### The Problem

Same search query = different intents:

| Query | User's Real Intent | Should Show |
|-------|-------------------|-------------|
| "cloud" | Looking for cloud services | Service pages |
| "cloud" | Looking for cloud computing info | Technical articles |
| "cloud" | Looking for a person named Cloud | SCS Professional profile |
| "James Walsh" | Looking for James Walsh person | SCS Professional profile |
| "James Walsh" | Looking for general info about James Walsh | Articles mentioning him |
| "environmental compliance" | Looking for services | Service pages |
| "environmental compliance" | Looking to learn about it | Articles and guides |

---

## How Query Intent Detection Works

### Step 1: Pattern Recognition

Detect intent based on query patterns:

```python
def detect_query_intent(query: str) -> str:
    """
    Detect what the user is looking for.
    
    Returns:
        'person_name', 'service', 'howto', 'navigational', 'general'
    """
    query_lower = query.lower().strip()
    
    # 1. PERSON NAME DETECTION
    # Pattern: "FirstName LastName" (both capitalized)
    # Examples: "James Walsh", "John Smith", "Sarah Johnson"
    import re
    if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', query):
        # Check if it's a first + last name pattern
        words = query.split()
        if len(words) == 2 and len(words[0]) >= 3 and len(words[1]) >= 3:
            logger.info(f"Detected person name query: {query}")
            return 'person_name'
    
    # 2. SERVICE QUERY DETECTION
    # Pattern: "service", "solutions", "consulting", etc.
    service_keywords = ['service', 'services', 'solutions', 'consulting', 
                        'support', 'implementation', 'solutions for']
    if any(keyword in query_lower for keyword in service_keywords):
        logger.info(f"Detected service query: {query}")
        return 'service'
    
    # 3. HOW-TO / INFORMATIONAL QUERY
    # Pattern: "how to", "what is", "why", etc.
    question_patterns = [r'^(how|what|why|when|where)', r'^(how to)', r'^(what is)']
    for pattern in question_patterns:
        if re.match(pattern, query_lower):
            logger.info(f"Detected how-to query: {query}")
            return 'howto'
    
    # 4. NAVIGATIONAL QUERY
    # Pattern: User looking for specific page
    navigational_keywords = ['contact', 'about us', 'team', 'careers', 
                            'locations', 'contact us']
    if any(keyword in query_lower for keyword in navigational_keywords):
        logger.info(f"Detected navigational query: {query}")
        return 'navigational'
    
    # 5. TRANSACTIONAL QUERY
    # Pattern: User wants to do something
    transactional_keywords = ['buy', 'download', 'purchase', 'order', 
                             'get', 'find', 'hire', 'request']
    if any(keyword in query_lower for keyword in transactional_keywords):
        logger.info(f"Detected transactional query: {query}")
        return 'transactional'
    
    # Default
    logger.info(f"Detected general query: {query}")
    return 'general'
```

---

## Step 2: Apply Intent-Based Logic

Once we know the intent, modify search behavior:

```python
async def search_with_intent(self, query: str, intent: str, ...):
    """Search with intent-aware optimizations."""
    
    # Get initial candidates
    candidates = await self.get_candidates(query)
    
    # Apply intent-specific logic
    if intent == 'person_name':
        # For person searches:
        # 1. Boost SCS Professionals post type
        # 2. Boost exact name matches in titles
        # 3. Add to AI instructions
        
        ai_instructions = """
        User is searching for a specific person. Priority:
        1. SCS Professionals profiles (exact match in title)
        2. Biographical information about the person
        3. Don't include general content that mentions the name
        
        CRITICAL: Only show results about THE person being searched for.
        """
        
        # Filter to prioritize professionals
        priority = ['scs-professionals', 'page', 'post', 'attachment']
        
    elif intent == 'service':
        # For service searches:
        # 1. Boost service pages
        # 2. Boost solution descriptions
        # 3. Prioritize actionable content
        
        ai_instructions = """
        User is looking for services or solutions. Priority:
        1. Service description pages
        2. Solution offerings
        3. Capabilities and expertise
        4. Avoid general articles unless highly relevant
        """
        
        priority = ['page', 'scs-services', 'post']
        
    elif intent == 'howto':
        # For how-to queries:
        # 1. Prioritize step-by-step guides
        # 2. Look for instructional content
        
        ai_instructions = """
        User needs actionable guidance. Priority:
        1. Step-by-step guides
        2. Tutorial content
        3. Practical how-to articles
        4. Skip theoretical content unless no practical content exists
        """
        
    elif intent == 'navigational':
        # User looking for specific page:
        # 1. Prioritize exact matches
        # 2. Don't apply post type priority (keep AI order)
        
        ai_instructions = """
        User is looking for a specific page. 
        Match the navigation intent exactly.
        """
        # Don't apply priority for navigational (keep AI order)
        priority = None
        
    else:
        # General query - use default
        ai_instructions = ""
        priority = ['post', 'page', 'scs-professionals']
    
    # Continue with search...
    return search_with_priority(candidates, priority, ai_instructions)
```

---

## Real Examples

### Example 1: "James Walsh"

```python
# Query: "James Walsh"
# Intent Detection: person_name
# Pattern Matched: "FirstName LastName" (both capitalized)

Intent = 'person_name'

AI Instructions Applied:
"""
User is searching for a specific person. Priority:
1. SCS Professionals profiles (exact match in title)
2. Biographical information about the person
"""

Post Type Priority Applied:
Priority order: ['scs-professionals', 'page', 'post', 'attachment']

Search Behavior:
✅ Prioritizes SCS Professionals post type
✅ Boosts results where "James Walsh" appears in title
✅ Ensures exact person profile is #1 result
❌ Does NOT add external context like "musician, singer, etc."
```

**Result**: Shows James Walsh's professional profile first, not general articles.

---

### Example 2: "cloud services"

```python
# Query: "cloud services"
# Intent Detection: service
# Pattern Matched: Contains "services" keyword

Intent = 'service'

AI Instructions Applied:
"""
User is looking for services or solutions. Priority:
1. Service description pages
2. Solution offerings
"""

Post Type Priority Applied:
Priority order: ['page', 'scs-services', 'post']

Search Behavior:
✅ Prioritizes service pages
✅ Boosts "cloud services" pages
✅ Shows practical service info
❌ Does NOT show general cloud computing articles first
```

---

### Example 3: "how to improve environmental compliance"

```python
# Query: "how to improve environmental compliance"
# Intent Detection: howto
# Pattern Matched: Starts with "how"

Intent = 'howto'

AI Instructions Applied:
"""
User needs actionable guidance. Priority:
1. Step-by-step guides
2. Tutorial content
3. Practical how-to articles
"""

Search Behavior:
✅ Prioritizes actionable guides
✅ Looks for "steps to", "ways to", "guide to"
✅ Skips theory-focused content
```

---

## Implementation Plan

### Backend (Python) - Add to `simple_hybrid_search.py`

```python
def detect_query_intent(self, query: str) -> str:
    """Detect what the user is actually looking for."""
    import re
    query_lower = query.lower().strip()
    words = query.split()
    
    # 1. Person name (e.g., "James Walsh", "Sarah Johnson")
    if len(words) == 2:
        first, last = words
        if (first[0].isupper() and last[0].isupper() and 
            len(first) >= 3 and len(last) >= 3):
            return 'person_name'
    
    # 2. Service query
    service_keywords = ['service', 'services', 'solutions', 'consulting']
    if any(kw in query_lower for kw in service_keywords):
        return 'service'
    
    # 3. How-to
    if re.match(r'^(how|what|why|when|where)', query_lower):
        return 'howto'
    
    # 4. Navigational
    nav_keywords = ['contact', 'about', 'team', 'careers', 'locations']
    if any(kw in query_lower for kw in nav_keywords):
        return 'navigational'
    
    # 5. Transactional
    trans_keywords = ['buy', 'download', 'purchase', 'order', 'get']
    if any(kw in query_lower for kw in trans_keywords):
        return 'transactional'
    
    return 'general'
```

### Usage in Search Method

```python
async def search(self, query: str, ...):
    # 1. Detect intent
    intent = self.detect_query_intent(query)
    logger.info(f"Query intent detected: {intent}")
    
    # 2. Generate dynamic AI instructions based on intent
    ai_instructions = self._generate_intent_based_instructions(query, intent)
    
    # 3. Apply intent-based post type priority
    if intent == 'person_name':
        priority = ['scs-professionals', 'page', 'post']
    elif intent == 'service':
        priority = ['scs-services', 'page', 'post']
    elif intent == 'howto':
        priority = ['post', 'page']  # Prioritize articles
    else:
        priority = post_type_priority  # Use custom
    
    # 4. Continue search with intent-based settings
    results = await self.search_with_settings(
        query, 
        ai_instructions=ai_instructions,
        post_type_priority=priority
    )
    
    return results
```

---

## Expected Results

### Before Intent Detection

| Query | Intent | Problem |
|-------|--------|---------|
| "James Walsh" | Unknown | Shows articles, press releases, anything mentioning him |
| "cloud services" | Unknown | Shows general articles before service pages |
| "how to compliance" | Unknown | Shows technical docs instead of guides |

### After Intent Detection

| Query | Intent | Result |
|-------|--------|--------|
| "James Walsh" | `person_name` | Shows SCS Professional profile #1 |
| "cloud services" | `service` | Shows service pages first |
| "how to compliance" | `howto` | Shows step-by-step guides first |

---

## Testing Examples

### Test 1: Person Name Query
```python
Query: "James Walsh"
Detected Intent: person_name
AI Instructions: "User searching for specific person. Prioritize SCS Professionals."
Expected Result: James Walsh professional profile #1
```

### Test 2: Service Query  
```python
Query: "environmental compliance services"
Detected Intent: service
AI Instructions: "User looking for services. Prioritize service pages."
Expected Result: Environmental Compliance Services page #1
```

### Test 3: How-To Query
```python
Query: "how to improve compliance"
Detected Intent: howto
AI Instructions: "User needs actionable guidance. Prioritize guides."
Expected Result: Step-by-step compliance guide #1
```

---

## Impact

### Current: 6/10 Specificity
- Generic search behavior
- No query understanding
- Returns broad results

### After Intent Detection: 9/10 Specificity  
- Understands user intent
- Returns context-appropriate content
- Person searches → people
- Service searches → services
- How-to searches → guides

---

## Implementation Priority

**Status**: HIGH PRIORITY
**Effort**: Medium (2-3 hours)
**Impact**: Very High
**Risk**: Low (can disable if issues)

**Why**: Makes search dramatically more specific by understanding user intent.

