# AI Instructions Improvements - Analysis & Suggestions

## Current State Analysis

### ✅ What's Working Well

1. **Strict Mode Implementation**
   - Prevents hallucination
   - Forces AI to use only search results
   - Good examples of what NOT to do

2. **Clear Scoring Criteria**
   - Semantic Relevance (40 points)
   - User Intent (30 points)
   - Content Quality (20 points)
   - Specificity (10 points)

3. **Structured Prompts**
   - Well-organized with sections
   - Clear return format requirements

### ❌ What Needs Improvement

#### Problem 1: **Too Generic**
Current instructions don't know what SCS Engineers is about.

#### Problem 2: **No Business Context**
AI doesn't understand:
- What post types mean (scs-professionals, scs-services)
- What users are typically looking for
- Domain-specific knowledge

#### Problem 3: **Scoring is Too Theoretical**
Criteria are abstract, not actionable for real-world scenarios.

#### Problem 4: **Missing Examples**
Few concrete examples of good vs bad scoring.

---

## 💡 Suggested Improvements

### 1. **Add Business Context to System Prompt** ⭐ HIGH PRIORITY

**Current:**
```
You are an expert search relevance analyzer.
Your job is to score how well each search result matches...
```

**Improved:**
```
You are an expert search relevance analyzer for SCS Engineers, a professional environmental consulting firm.

BUSINESS CONTEXT:
- SCS Engineers provides environmental, engineering, and consulting services
- Main services include: waste management, environmental compliance, sustainability consulting
- Post types you'll see:
  - "scs-professionals": Staff member profiles
  - "scs-services": Service descriptions
  - "page": General pages (About, Services, Projects)
  - "post": Blog articles, case studies, news

YOUR JOB:
Score search results based on how well they match user queries for this business context.
```

**Why:** AI needs to understand the business to make better decisions.

---

### 2. **Enhance Scoring Criteria with Concrete Examples** ⭐ HIGH PRIORITY

**Current:**
```
1. **Semantic Relevance** (40 points)
   - Does the content match the query's semantic meaning?
   - Is it exactly what the user is looking for?
```

**Improved:**
```
1. **Semantic Relevance** (40 points)
   - Does the content match the query's semantic meaning?
   - Is it exactly what the user is looking for?
   
   EXAMPLES:
   ✅ Query: "hazardous waste management" 
      Result: "Hazardous Waste Management Services" → Score: 95 (exact match)
      
   ✅ Query: "toxic site remediation"
      Result: "Environmental Remediation Services" → Score: 85 (conceptually related)
      
   ❌ Query: "water treatment"
      Result: "Solid Waste Management" → Score: 25 (not relevant)
```

**Why:** Concrete examples help AI understand better.

---

### 3. **Add Post Type Priority Understanding** ⭐ MEDIUM PRIORITY

**Current:** Post type is just shown, not understood.

**Improved:**
```
When scoring results, understand the post type priority:

1. **scs-professionals** (People profiles)
   - Highest priority for queries like "James Walsh", "find engineer"
   - These show staff expertise
   - Boost if query matches person's name or specialty
   
2. **scs-services** (Service pages)
   - Highest priority for "cloud services", "consulting", "environmental solutions"
   - These describe what the company offers
   - Boost if query matches service name/topic
   
3. **page** (General pages)
   - Good for navigational queries (contact, about, locations)
   - Medium priority for informational queries
   
4. **post** (Articles)
   - Good for "how to", "case study", "news" queries
   - Lower priority for service queries

BOOST LOGIC:
- If query = person name AND result type = "scs-professionals" → +15 points
- If query = service term AND result type = "scs-services" → +15 points
- If query = "contact/about/locations" AND result type = "page" → +10 points
```

**Why:** AI should understand what each post type means for ranking.

---

### 4. **Improve AI Answer Instructions with Better Examples** ⭐ MEDIUM PRIORITY

**Current:** Has good strict rules, but examples could be more detailed.

**Improved:**
```
STRICT MODE: Answer using ONLY the provided search results.

CRITICAL RULES - DO NOT VIOLATE:
1. ONLY use information that appears in the search results
2. Do NOT add ANY external knowledge, assumptions, or context
3. Do NOT infer what the user might be looking for
4. Do NOT add details that don't appear in the results
5. If information isn't there, explicitly state "The search results do not include information about [topic]"

HOW TO ANSWER - STEP BY STEP:
1. Read all source titles and excerpts
2. Extract ONLY facts that are explicitly stated
3. If you see conflicting information, mention both sources
4. Cite your sources clearly (Source 1, Source 2)
5. If you can't answer from results, say "Based on the available search results, I cannot find specific information about [topic]"

BAD EXAMPLES (DON'T DO THIS):
❌ "James Walsh is a musician, singer, and songwriter"
   → WRONG! You added "musician" - that's not in search results!
   
❌ "The project is located in California"
   → WRONG! You inferred location from company info - not in results!

❌ "SCS provides comprehensive environmental consulting services"
   → TOO VAGUE! Be specific - what does 'comprehensive' mean?

GOOD EXAMPLES (DO THIS):
✅ "The search results show James Walsh is the CEO of SCS Engineers (Source 1). The results do not include information about his personal interests or hobbies."

✅ "Based on Source 1, the project involved soil remediation. Source 2 mentions the project lasted 18 months. No specific location is mentioned in these results."

✅ "According to Source 1, SCS Engineers provides hazardous waste management services. Source 2 adds that they also offer environmental compliance consulting."

CONTEXT AWARENESS:
- User is likely looking for professional information about SCS Engineers
- Common queries: staff members, services, projects, environmental solutions
- Avoid making this sound like generic web content
```

**Why:** More detailed examples prevent common errors.

---

### 5. **Add Intent-Based Scoring Guidance** ⭐ MEDIUM PRIORITY

**Current:** User intent criteria is generic.

**Improved:**
```
2. **User Intent** (30 points)
   - Does it address what the user wants to accomplish?
   
   INTENT DETECTION & SCORING:
   
   PERSON NAME QUERIES ("James Walsh"):
   - Best: Staff profile page with exact name match → Score: 95
   - Good: News/article mentioning the person → Score: 75
   - Bad: Generic article about company → Score: 30
   
   SERVICE QUERIES ("hazardous waste services"):
   - Best: Service description page with exact match → Score: 95
   - Good: Project case study featuring the service → Score: 80
   - Bad: General blog post mentioning service → Score: 50
   
   HOW-TO QUERIES ("how to manage waste"):
   - Best: Step-by-step guide or detailed article → Score: 90
   - Good: Case study with relevant information → Score: 70
   - Bad: General page with no actionable content → Score: 40
   
   NAVIGATIONAL QUERIES ("contact", "about us"):
   - Best: Exact page matching the navigation intent → Score: 100
   - Good: Related page (e.g., locations page) → Score: 65
   - Bad: Article mentioning the term → Score: 25
   
   TRANSACTIONAL QUERIES ("request quote", "download"):
   - Best: Page where user can perform the action → Score: 95
   - Good: Page that mentions the service/action → Score: 60
   - Bad: Article about the topic → Score: 35
```

**Why:** Intent-specific scoring produces more relevant results.

---

### 6. **Add Common Query Examples** ⭐ LOW PRIORITY

**Add a section with common queries:**

```
📝 COMMON QUERY PATTERNS:

1. Person Searches
   - "James Walsh" → Expect: Staff profile
   - "Sarah Johnson" → Expect: Staff profile
   
2. Service Searches  
   - "waste management" → Expect: Service page
   - "environmental consulting" → Expect: Service page
   
3. Project Searches
   - "landfill project" → Expect: Case study or project page
   - "remediation" → Expect: Project or service page
   
4. Question Searches
   - "how to compliance" → Expect: Guide or article
   - "what is environmental consulting" → Expect: Explanation page
   
5. Contact Searches
   - "contact" → Expect: Contact page
   - "locations" → Expect: Locations/offices page
```

**Why:** Helps AI understand expected result types.

---

## 🎯 Recommended Implementation Priority

### Phase 1: **Business Context** (Day 1)
- Add SCS Engineers business context
- Add post type descriptions
- Expected impact: **High**

### Phase 2: **Intent-Based Scoring** (Day 2-3)
- Add intent detection examples
- Add scoring patterns for each intent
- Expected impact: **High**

### Phase 3: **Enhanced Examples** (Day 4-5)
- Add more concrete examples to criteria
- Add common query patterns
- Expected impact: **Medium**

### Phase 4: **AI Answer Improvements** (Day 6)
- Better examples of strict mode
- More detailed step-by-step guidance
- Expected impact: **Medium**

---

## 💻 Code Changes Needed

### 1. Update `cerebras_llm.py` - System Prompt

**File:** `cerebras_llm.py`  
**Location:** Line ~688 in `rerank_results_async()` method

Replace generic system prompt with business-aware prompt.

### 2. Update `cerebras_llm.py` - User Prompt

**File:** `cerebras_llm.py`  
**Location:** Line ~695 in `rerank_results_async()` method

Add concrete examples to each scoring criterion.

### 3. Update `cerebras_llm.py` - AI Answer Instructions

**File:** `cerebras_llm.py`  
**Location:** Line ~120 in `generate_answer()` method

Enhance with better examples and step-by-step guidance.

---

## 📊 Expected Impact

### Before Improvements:
- Generic scoring criteria
- AI doesn't understand business context
- Few concrete examples
- Results may not match business needs

### After Improvements:
- ✅ Better understanding of SCS Engineers business
- ✅ More relevant results for service/person queries
- ✅ Better AI answers with fewer hallucinations
- ✅ Intent-specific scoring produces better rankings
- ✅ **Estimated 25-35% improvement in result relevance**

---

Would you like me to implement these improvements? I recommend starting with **Phase 1** (Business Context) as it has the highest impact with minimal changes.





