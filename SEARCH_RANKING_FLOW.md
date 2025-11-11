# Hybrid Search Ranking Flow

```mermaid
flowchart TD
    subgraph WordPress Plugin
        UI[Search UI<br/>filters, CTA, JS] --> AJAX
        Settings[Admin Settings<br/>CTR window, AI toggles] --> APIClient
        AJAX[AJAXManager<br/>SearchAPI] --> APIClient
        Analytics[AnalyticsService & CTRService<br/>track clicks/queries] --> CTRData[(CTR DB)]
        CTRData --> Settings
    end

    APIClient -->|query, filters,<br/>behavioral signals| FastAPI[(FastAPI /main.py)]

    subgraph FastAPI Backend
        FastAPI -->|normalize request| SearchSystem
        FastAPI -->|metadata| Response
        FastAPI -->|optional| LLMClient[Cerebras LLM client]
    end

    subgraph Search Core
        SearchSystem[SimpleHybridSearch<br/>Python] -->|intent & entity analysis| QueryAnalysis[query_analysis.py]
        SearchSystem -->|TF-IDF| TFIDF[TF-IDF matrix]
        SearchSystem -->|vector search| Qdrant[Qdrant Manager]
        TFIDF --> Fusion[RRF + weighted Borda fusion]
        Qdrant --> Fusion
        QueryAnalysis --> FieldBoosts[Field & entity boosts<br/>titles, meta, services]
        CTRSignals[CTR behavioral map] --> BehavioralBoosts
        Fusion -->|top candidates| LLMRerank[LLM reranker]
        BehavioralBoosts[behavioral boost] --> Fusion
        LLMRerank --> RankedResults
        Fusion --> RankedResults
    end

    CTRData -->|top clicked| CTRSignals
    RankedResults --> FastAPI
    Response --> WordPress Plugin
    WordPress Plugin --> UI
    UI -->|click events| Analytics
```

**Legend**

- **WordPress Plugin:** submits search requests (with filters and CTR signals) and displays the ranked results and AI answers. Admin settings control CTR boosting and AI behaviour.
- **FastAPI Backend:** validates requests, forwards behavioural signals, and aggregates metadata for the response.
- **Search Core:** combines intent-aware TF‑IDF and vector results, applies behavioural boosts, and (optionally) reranks via the Cerebras LLM using weighted Borda fusion.
- **Analytics loop:** click events feed CTR statistics; the next search includes those signals to reinforce high-performing results.

