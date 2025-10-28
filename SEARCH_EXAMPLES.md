# 10 Examples: How Search Works with AI Scores + Priority

## Configuration
- **Post Type Priority**: `['post', 'page']` (post has higher priority than page)
- **AI Weight**: 0.7 (70% AI, 30% TF-IDF)
- **Custom Instructions**: "Prioritize recent compliance documents"

---

## Example 1: Clear Winner with Priority Tie-Breaker

**Query**: "environmental compliance audit"

**Initial TF-IDF Results** (before AI):
```
Result A: post,      TF-IDF=0.85, title="Environmental Compliance Audit Checklist"
Result B: page,      TF-IDF=0.85, title="Environmental Compliance Guidelines"
Result C: post,      TF-IDF=0.80, title="Audit Requirements for Facilities"
```

**AI Scores Results**:
- Result A: AI=92 (exact match + recent + compliance)
- Result B: AI=91 (good match + guidelines)
- Result C: AI=88 (related but less specific)

**Hybrid Score Calculation** (`TF-IDF * 0.3 + AI * 0.7`):
- Result A: 0.85×0.3 + 0.92×0.7 = **0.899**
- Result B: 0.85×0.3 + 0.91×0.7 = **0.892**
- Result C: 0.80×0.3 + 0.88×0.7 = **0.856**

**Final Sorting** (hybrid DESC, then priority ASC):
```
1. Result A: post, hybrid=0.899, priority=0 ✅
2. Result B: page, hybrid=0.892, priority=1
3. Result C: post, hybrid=0.856, priority=0
```
**Winner**: Post wins because it has the same hybrid score as page but higher priority!

---

## Example 2: AI Disagrees with Priority

**Query**: "RCRA hazardous waste"

**Initial Results**:
```
Result A: post,    TF-IDF=0.88, title="RCRA Compliance Guide"
Result B: page,    TF-IDF=0.90, title="RCRA Waste Categories"
Result C: post,    TF-IDF=0.82, title="Hazardous Waste Management"
```

**AI Scores**:
- Result A: AI=95 (comprehensive compliance guide)
- Result B: AI=72 (basic reference, less helpful)
- Result C: AI=90 (related but less specific)

**Hybrid Scores**:
- Result A: **0.913**
- Result B: **0.774**
- Result C: **0.864**

**Final Order**:
```
1. Result A: post, 0.913 ✅ (Highest hybrid score - AI winner)
2. Result C: post, 0.864
3. Result B: page, 0.774 (AI demoted despite high TF-IDF)
```
**Lesson**: AI's semantic understanding can override TF-IDF keyword matching!

---

## Example 3: Priority as Tie-Breaker

**Query**: "sustainability consulting services"

**TF-IDF Results**:
```
A: post, 0.92, "Sustainability Consulting"
B: page, 0.92, "Sustainable Solutions"
C: post, 0.90, "Environmental Consulting"
```

**AI Scores** (all similar semantic relevance):
- Result A: AI=90
- Result B: AI=90
- Result C: AI=88

**Hybrid Scores** (all very close):
- Result A: **0.906**
- Result B: **0.906**
- Result C: **0.894**

**Final Order**:
```
1. Result A: post, 0.906, priority=0 ✅
2. Result B: page, 0.906, priority=1 (Same score, but post wins!)
3. Result C: post, 0.894
```
**Key**: When hybrid scores are identical, priority breaks the tie!

---

## Example 4: AI Finds Better Semantic Match

**Query**: "how to prevent air pollution"

**Initial TF-IDF** (picks up keywords):
```
A: post, 0.85, "Air Quality Standards"
B: page, 0.88, "Air Pollution Prevention Methods"  ← keyword-heavy
C: post, 0.80, "Preventing Industrial Air Emissions"
```

**AI Scores** (understands intent):
- Result A: AI=75 (just standards, no prevention methods)
- Result B: AI=95 (exactly what user wants - how-to guide!)
- Result C: AI=92 (specific industrial prevention)

**Hybrid Scores**:
- Result B: **0.926** ✅ (AI found the best match!)
- Result C: **0.874**
- Result A: **0.810**

**Final Order**:
```
1. Result B: page, 0.926 (AI winner despite being page)
2. Result C: post, 0.874
3. Result A: post, 0.810
```
**Lesson**: AI's semantic understanding can override post type priority when there's a clear quality difference!

---

## Example 5: Similar Scores, Priority Decides

**Query**: "environmental due diligence"

**TF-IDF**:
```
A: post, 0.91
B: page, 0.91
C: post, 0.89
```

**AI Scores** (very similar quality):
- Result A: AI=90
- Result B: AI=90
- Result C: AI=88

**Hybrid Scores** (nearly identical):
- Result A: **0.903**
- Result B: **0.903**
- Result C: **0.887**

**Final Order**:
```
1. Result A: post, 0.903, priority=0 ✅
2. Result B: page, 0.903, priority=1
3. Result C: post, 0.887
```
**Key**: When AI scores are identical, priority guarantees post appears first!

---

## Example 6: Custom Instructions Working

**Query**: "regulatory compliance"
**Custom Instructions**: "Prioritize recent compliance documents"

**TF-IDF**:
```
A: post, 0.90, date="2024-01-15" - "Recent Compliance Updates"
B: post, 0.92, date="2021-05-10" - "Regulatory Compliance Overview"
C: page, 0.88, date="2024-03-20" - "Compliance Requirements"
```

**AI Scores** (following custom instructions):
- Result A: AI=96 (recent + compliance!)
- Result C: AI=94 (recent + compliance!)
- Result B: AI=85 (older document, penalized per instructions)

**Hybrid Scores**:
- Result A: **0.918** ✅
- Result C: **0.920** ✅
- Result B: **0.871**

**Final Order**:
```
1. Result C: page, 0.920 (Most recent compliance!)
2. Result A: post, 0.918 (Recent compliance)
3. Result B: post, 0.871 (Older, penalized)
```
**Key**: Custom instructions can influence AI to prioritize specific criteria!

---

## Example 7: Multi-Type Search with Priority

**Query**: "water quality testing"

**Mixed Post Types**:
```
A: post,        0.89, "Water Quality Testing Protocols"
B: page,        0.89, "Water Quality Standards"
C: scs-professional, 0.87, "Water Quality Expert Profile"
D: post,        0.85, "Testing Water Samples"
```

**Priority Order**: `['post', 'page', 'scs-professional']`

**AI Scores**:
- Result A: AI=93
- Result B: AI=91
- Result C: AI=89
- Result D: AI=88

**Hybrid Scores**:
- Result A: **0.902** (post)
- Result B: **0.896** (page)
- Result C: **0.880** (scs-professional)
- Result D: **0.871** (post)

**Final Order**:
```
1. Result A: post, 0.902 ✅
2. Result B: page, 0.896 ✅
3. Result C: scs-professional, 0.880
4. Result D: post, 0.871
```
**Key**: Priority order is maintained across different post types!

---

## Example 8: AI Overrules Poor TF-IDF Match

**Query**: "sustainable waste management"

**TF-IDF** (misses semantic nuance):
```
A: post,  0.95, "Waste Management" (generic)
B: page,  0.93, "Management Services" (vague)
C: post,  0.85, "Circular Economy Solutions" (semantic match!)
```

**AI Scores** (understands user's intent):
- Result C: AI=96 (perfect semantic match - sustainability focus!)
- Result A: AI=80 (too generic)
- Result B: AI=70 (vague)

**Hybrid Scores**:
- Result C: **0.901** ✅
- Result A: **0.835**
- Result B: **0.781**

**Final Order**:
```
1. Result C: post, 0.901 (AI found the better match!)
2. Result A: post, 0.835
3. Result B: page, 0.781
```
**Lesson**: AI's semantic understanding elevates relevant but keyword-poor documents!

---

## Example 9: Close Scores with Priority Breaking Ties

**Query**: "environmental site assessment"

**TF-IDF**:
```
A: post, 0.90
B: page, 0.90
C: post, 0.89
D: page, 0.89
```

**AI Scores** (all similar quality):
- Result A: AI=89
- Result B: AI=89
- Result C: AI=88
- Result D: AI=88

**Hybrid Scores**:
- Result A: **0.897**
- Result B: **0.897**
- Result C: **0.887**
- Result D: **0.887**

**Final Order**:
```
1. Result A: post, 0.897, priority=0 ✅
2. Result B: page, 0.897, priority=1
3. Result C: post, 0.887, priority=0 ✅
4. Result D: page, 0.887, priority=1
```
**Key**: Priority consistently breaks ties between results with same hybrid score!

---

## Example 10: Complex Multi-Factor Scenario

**Query**: "PFAS contamination testing"
**Priority**: `['post', 'page', 'scs-press-release']`

**Results**:
```
A: post,              0.92, "PFAS Testing Protocols"
B: page,              0.90, "PFAS Detection Methods"
C: scs-press-release, 0.88, "PFAS Breakthrough at SCS Lab"
D: post,              0.86, "Contamination Assessment"
```

**AI Scores** (considering custom instructions for recent compliance):
- Result A: AI=94 (comprehensive testing)
- Result B: AI=92 (good detection methods)
- Result C: AI=98 (recent breakthrough! custom instruction match)
- Result D: AI=89 (related but general)

**Hybrid Scores**:
- Result A: **0.924** (post)
- Result B: **0.914** (page)
- Result C: **0.926** (scs-press-release - custom instruction boost!)
- Result D: **0.875** (post)

**Final Order**:
```
1. Result C: scs-press-release, 0.926 (Highest score wins!)
2. Result A: post, 0.924 (High score + priority)
3. Result B: page, 0.914
4. Result D: post, 0.875
```
**Key**: Custom instructions can override normal priority when there's a score difference!

---

## Summary of Rules

1. **Hybrid Score is Primary**: Results sorted by `hybrid_score` (descending)
2. **Priority is Tie-Breaker**: When scores are identical, priority decides
3. **AI Has More Weight**: 70% AI influence (can override poor TF-IDF)
4. **Custom Instructions Work**: AI prioritizes criteria from instructions
5. **Priority Visible Within Same Score Tiers**: Post always beats page at same hybrid_score

**The Formula**:
```python
hybrid_score = (tfidf_score × 0.3) + (ai_score × 0.7)
final_sort = sorted(results, key=(hybrid_score DESC, priority ASC))
```

