"""
Heuristic-based query analysis utilities shared across search components.
Can optionally use AI (LLM) for enhanced query analysis.
"""
from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set

try:
    from config import settings
except Exception:  # pragma: no cover - fallback when config unavailable
    settings = None

logger = logging.getLogger(__name__)

# Core keyword sets
SERVICE_KEYWORDS: Set[str] = {
    "service",
    "services",
    "solution",
    "solutions",
    "consulting",
    "consultant",
    "consultants",
    "management",
    "assessment",
    "monitoring",
    "remediation",
    "compliance",
    "engineering",
    "audit",
    "design",
    "implementation",
    "support",
    "analysis",
    "planning",
}

ROLE_KEYWORDS: Set[str] = {
    "ceo",
    "chief",
    "president",
    "principal",
    "director",
    "chair",
    "founder",
    "lead",
    "officer",
    "manager",
    "executive",
    "partner",
    "vice",
}

TRANSACTIONAL_KEYWORDS: Set[str] = {
    "buy",
    "purchase",
    "order",
    "request",
    "quote",
    "apply",
    "register",
    "subscribe",
    "download",
    "hire",
    "schedule",
    "book",
}

NAVIGATIONAL_KEYWORDS: Set[str] = {
    "contact",
    "about",
    "team",
    "careers",
    "location",
    "locations",
    "office",
    "offices",
    "login",
    "account",
    "portal",
    "map",
    "directions",
    "phone",
    "email",
}

QUESTION_WORDS: Set[str] = {
    "who",
    "what",
    "where",
    "when",
    "why",
    "how",
    "can",
    "should",
    "will",
    "do",
    "does",
    "is",
    "are",
}

SECTOR_KEYWORDS: Set[str] = {
    "environmental",
    "waste",
    "remediation",
    "sustainability",
    "industrial",
    "manufacturing",
    "energy",
    "infrastructure",
    "water",
    "air",
    "landfill",
    "recycling",
    "compliance",
    "construction",
    "geotechnical",
    "pfas",
    "permitting",
    "geology",
}

SERVICE_PHRASES: Set[str] = {
    "waste management",
    "air quality",
    "environmental compliance",
    "sustainability consulting",
    "hazardous waste",
    "landfill gas",
    "remediation services",
    "brownfield redevelopment",
    "leachate management",
    "pfas treatment",
    "renewable energy",
}

SECTOR_PHRASES: Set[str] = {
    "solid waste",
    "municipal waste",
    "industrial waste",
    "environmental engineering",
    "waste to energy",
    "biogas",
    "circular economy",
    "climate resilience",
}

LOCAL_MODIFIERS: Set[str] = {
    "near me",
    "nearby",
    "in my area",
    "close to me",
    "local",
}

CASE_STUDY_KEYWORDS: Set[str] = {
    "case study",
    "case studies",
    "project",
    "projects",
    "portfolio",
}

REGULATORY_KEYWORDS: Set[str] = {
    "regulation",
    "regulations",
    "rule",
    "rules",
    "policy",
    "laws",
    "epa",
    "osha",
    "compliance",
    "permitting",
}

if settings:
    SERVICE_KEYWORDS |= {kw.lower() for kw in settings.intent_service_keywords if kw}
    SECTOR_KEYWORDS |= {kw.lower() for kw in settings.intent_sector_keywords if kw}
    NAVIGATIONAL_KEYWORDS |= {kw.lower() for kw in settings.intent_navigational_keywords if kw}
    TRANSACTIONAL_KEYWORDS |= {kw.lower() for kw in settings.intent_transactional_keywords if kw}
    custom_service_phrases = {
        kw.lower() for kw in settings.intent_service_keywords if kw and " " in kw
    }
    SERVICE_PHRASES |= custom_service_phrases
    custom_sector_phrases = {
        kw.lower() for kw in settings.intent_sector_keywords if kw and " " in kw
    }
    SECTOR_PHRASES |= custom_sector_phrases

US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
}

US_STATE_ABBREVIATIONS = {
    "al",
    "ak",
    "az",
    "ar",
    "ca",
    "co",
    "ct",
    "de",
    "fl",
    "ga",
    "hi",
    "id",
    "il",
    "in",
    "ia",
    "ks",
    "ky",
    "la",
    "me",
    "md",
    "ma",
    "mi",
    "mn",
    "ms",
    "mo",
    "mt",
    "ne",
    "nv",
    "nh",
    "nj",
    "nm",
    "ny",
    "nc",
    "nd",
    "oh",
    "ok",
    "or",
    "pa",
    "ri",
    "sc",
    "sd",
    "tn",
    "tx",
    "ut",
    "vt",
    "va",
    "wa",
    "wv",
    "wi",
    "wy",
}

ORGANIZATION_SUFFIXES = {
    "inc",
    "llc",
    "ltd",
    "corp",
    "co",
    "company",
    "associates",
    "partners",
    "group",
    "department",
    "agency",
    "university",
    "college",
    "authority",
    "board",
    "bureau",
    "commission",
    "council",
}


@dataclass
class QueryAnalysis:
    intent: str
    confidence: float
    entities: Dict[str, List[str]]
    signals: Dict[str, Any]
    normalized_query: str
    keywords: List[str]
    primary_entities: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": round(float(self.confidence), 3),
            "entities": self.entities,
            "signals": self.signals,
            "normalized_query": self.normalized_query,
            "keywords": self.keywords,
            "primary_entities": self.primary_entities,
        }


def get_recommended_post_types(query_analysis: Dict[str, Any], default_priority: Optional[List[str]] = None) -> List[str]:
    """
    Determine recommended post type priority based on query context (intent + entities).
    
    This function intelligently maps query context to post types:
    - Person queries → prioritize scs-professionals
    - Service queries → prioritize scs-services, page
    - How-to queries → prioritize post (articles)
    - Case study queries → prioritize post
    - Navigational queries → prioritize page
    - Entity-based adjustments (e.g., if people entities exist, boost scs-professionals)
    
    Args:
        query_analysis: Dictionary from analyze_query() containing intent, entities, etc.
        default_priority: Optional default priority list to merge with recommendations
    
    Returns:
        List of post types in recommended priority order
    """
    intent = query_analysis.get('intent', 'general')
    entities = query_analysis.get('entities', {})
    confidence = query_analysis.get('confidence', 0.0)
    primary_entities = query_analysis.get('primary_entities', [])
    
    # Base post types (all available types)
    all_post_types = ['scs-professionals', 'scs-services', 'page', 'post', 'attachment']
    
    # Start with default priority if provided, otherwise use all types
    recommended = default_priority.copy() if default_priority else all_post_types.copy()
    
    # Entity-based adjustments (highest priority - entities are strong signals)
    people_entities = entities.get('people', [])
    roles_entities = entities.get('roles', [])
    services_entities = entities.get('services', [])
    
    # If people or roles are detected, prioritize professionals
    if (people_entities or roles_entities) and confidence > 0.6:
        if 'scs-professionals' not in recommended:
            recommended.insert(0, 'scs-professionals')
        else:
            # Move to front if already present
            recommended.remove('scs-professionals')
            recommended.insert(0, 'scs-professionals')
        logger.info(f"Entity-based adjustment: People/roles detected, prioritizing scs-professionals")
    
    # If services are detected, prioritize service pages
    if services_entities and confidence > 0.6:
        if 'scs-services' not in recommended:
            recommended.insert(0, 'scs-services')
        else:
            # Move to front if already present
            recommended.remove('scs-services')
            recommended.insert(0, 'scs-services')
        logger.info(f"Entity-based adjustment: Services detected, prioritizing scs-services")
    
    # Intent-based recommendations (applied after entity adjustments)
    intent_priority_map = {
        'person_name': ['scs-professionals', 'page', 'post', 'scs-services', 'attachment'],
        'executive_role': ['scs-professionals', 'page', 'post', 'scs-services', 'attachment'],
        'service': ['scs-services', 'page', 'post', 'scs-professionals', 'attachment'],
        'local_service': ['scs-services', 'page', 'post', 'scs-professionals', 'attachment'],
        'howto': ['post', 'page', 'scs-professionals', 'scs-services', 'attachment'],
        'case_study': ['post', 'page', 'scs-services', 'scs-professionals', 'attachment'],
        'sector': ['page', 'post', 'scs-services', 'scs-professionals', 'attachment'],
        'regulatory': ['post', 'page', 'scs-services', 'scs-professionals', 'attachment'],
        'navigational': ['page', 'post', 'scs-services', 'scs-professionals', 'attachment'],
        'transactional': ['page', 'post', 'scs-services', 'scs-professionals', 'attachment'],
        'informational': ['post', 'page', 'scs-services', 'scs-professionals', 'attachment'],
        'general': recommended  # Use current recommendation for general
    }
    
    # Get intent-based priority if available and confidence is sufficient
    if intent in intent_priority_map and confidence > 0.5:
        intent_priority = intent_priority_map[intent]
        
        # Merge with current recommendations, giving priority to entity-based adjustments
        # Keep entity-prioritized types at front, then add intent-based order
        merged = []
        seen = set()
        
        # First, add entity-prioritized types (if any were moved to front)
        for pt in recommended[:2]:  # Check first 2 positions for entity adjustments
            if pt in ['scs-professionals', 'scs-services'] and pt not in seen:
                merged.append(pt)
                seen.add(pt)
        
        # Then add intent-based priority, skipping already added types
        for pt in intent_priority:
            if pt not in seen:
                merged.append(pt)
                seen.add(pt)
        
        # Add any remaining types from all_post_types
        for pt in all_post_types:
            if pt not in seen:
                merged.append(pt)
        
        recommended = merged
        logger.info(f"Intent-based adjustment: {intent} → {recommended[:3]}...")
    
    # Ensure all post types are included (no filtering, just reordering)
    for pt in all_post_types:
        if pt not in recommended:
            recommended.append(pt)
    
    return recommended


def _extract_capitalized_phrases(query: str) -> List[str]:
    """
    Extract candidate proper nouns/person names.
    Improved to filter out common service/system phrases.
    """
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b"
    matches = re.findall(pattern, query)
    
    # Common service/system words that shouldn't be treated as person names
    service_words = {
        'management', 'system', 'systems', 'service', 'services', 'solution', 'solutions',
        'chain', 'supply', 'compliance', 'consulting', 'engineering', 'remediation',
        'treatment', 'monitoring', 'assessment', 'audit', 'planning', 'design',
        'implementation', 'support', 'analysis', 'operations', 'technology', 'technologies',
        'environmental', 'waste', 'hazardous', 'solid', 'municipal', 'industrial',
        'renewable', 'energy', 'sustainability', 'infrastructure', 'geotechnical'
    }
    
    # Filter out words that are clearly not names
    cleaned = []
    for match in matches:
        words = match.split()
        # All words must be properly capitalized (first letter uppercase, rest lowercase)
        if all(word[0].isupper() and word[1:].islower() for word in words):
            # Check if any word in the phrase is a known service word
            match_lower = match.lower()
            is_service_phrase = any(service_word in match_lower for service_word in service_words)
            
            # Only include if it's not clearly a service phrase
            # Allow if it's 2-3 words and doesn't contain service words
            if not is_service_phrase or (len(words) <= 3 and not any(word.lower() in service_words for word in words)):
                cleaned.append(match.strip())
    
    return cleaned


def _extract_services(query_lower: str) -> List[str]:
    """
    Extract service-related terms from query.
    Enhanced to catch more service patterns and context.
    """
    matches = {kw for kw in SERVICE_KEYWORDS if kw in query_lower}
    for phrase in SERVICE_PHRASES:
        if phrase in query_lower:
            matches.add(phrase)
    
    # Additional service patterns (multi-word services)
    service_patterns = [
        r'\b\w+\s+management\b',  # "waste management", "supply chain management"
        r'\b\w+\s+systems?\b',     # "management systems", "compliance systems"
        r'\b\w+\s+services?\b',    # "consulting services", "engineering services"
        r'\b\w+\s+solutions?\b',   # "waste solutions", "compliance solutions"
        r'\b\w+\s+consulting\b',   # "environmental consulting"
        r'\b\w+\s+engineering\b',  # "environmental engineering"
        r'\b\w+\s+remediation\b',  # "environmental remediation"
        r'\b\w+\s+compliance\b',   # "regulatory compliance"
    ]
    
    for pattern in service_patterns:
        found = re.findall(pattern, query_lower)
        for match in found:
            if match.strip() and len(match.strip().split()) <= 3:  # Limit to reasonable length
                matches.add(match.strip())
    
    return sorted(matches)


def _extract_roles(query_lower: str) -> List[str]:
    roles = set()
    for kw in ROLE_KEYWORDS:
        if kw in query_lower:
            roles.add(kw)
    return sorted(roles)


def _extract_locations(query: str, query_lower: str) -> List[str]:
    locations: Set[str] = set()
    # Match state names
    for state in US_STATE_NAMES:
        if state in query_lower:
            locations.add(state.title())
    # Match abbreviations (two letters uppercase)
    tokens = re.findall(r"\b[A-Za-z]{2}\b", query)
    for token in tokens:
        lower = token.lower()
        if lower in US_STATE_ABBREVIATIONS:
            locations.add(token.upper())
    # Common city terms (basic)
    city_pattern = r"\b(?:city of |county of )?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    for match in re.findall(city_pattern, query):
        if match.lower() not in US_STATE_NAMES and len(match) > 3:
            locations.add(match.strip())
    return sorted(locations)


def _extract_organizations(query: str, query_lower: str) -> List[str]:
    organizations: Set[str] = set()
    pattern = r"\b[A-Z][A-Za-z&]+(?:\s+[A-Z][A-Za-z&]+)*\b"
    for match in re.findall(pattern, query):
        lower = match.lower()
        if lower in US_STATE_NAMES:
            continue
        if any(lower.endswith(suffix) for suffix in ORGANIZATION_SUFFIXES):
            organizations.add(match.strip())
    # Specific uppercase acronyms (EPA, OSHA, etc.)
    for token in re.findall(r"\b[A-Z]{2,}\b", query):
        if len(token) >= 3:
            organizations.add(token)
    return sorted(organizations)


def _tokenize_keywords(query_lower: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", query_lower)
    return tokens[:20]


def _determine_intent(
    query: str,
    query_lower: str,
    people: List[str],
    roles: List[str],
    services: List[str],
    locations: List[str],
    organizations: List[str],
) -> (str, float, Dict[str, Any]):
    signals: Dict[str, Any] = {
        "is_question": False,
        "question_word": None,
        "has_role_keyword": bool(roles),
        "has_service_keyword": bool(services),
        "has_location": bool(locations),
        "has_organization": bool(organizations),
        "has_person_candidate": bool(people),
        "has_local_modifier": False,
        "has_zip_code": False,
        "has_case_study_signal": False,
        "has_regulatory_signal": False,
    }

    words = query.strip().split()
    if words:
        first_word = words[0].lower()
        if first_word in QUESTION_WORDS:
            signals["is_question"] = True
            signals["question_word"] = first_word

    lowered = query_lower
    if any(modifier in lowered for modifier in LOCAL_MODIFIERS):
        signals["has_local_modifier"] = True

    if re.search(r"\b\d{5}(?:-\d{4})?\b", lowered):
        signals["has_zip_code"] = True

    if any(keyword in lowered for keyword in CASE_STUDY_KEYWORDS):
        signals["has_case_study_signal"] = True

    if any(keyword in lowered for keyword in REGULATORY_KEYWORDS):
        signals["has_regulatory_signal"] = True

    # Person / executive detection with improved context understanding
    if people:
        # Check if the detected "person" is actually a service/system phrase or organization
        # Service phrases typically contain words like "management", "system", "service", etc.
        service_indicators = ['management', 'system', 'systems', 'service', 'services', 
                             'solution', 'solutions', 'chain', 'supply', 'compliance',
                             'consulting', 'engineering', 'remediation', 'treatment',
                             'monitoring', 'assessment', 'audit', 'planning', 'design',
                             'implementation', 'support', 'analysis', 'operations']
        
        # Organization/business indicators
        organization_indicators = ['company', 'corporation', 'corp', 'inc', 'llc', 'ltd',
                                  'associates', 'partners', 'group', 'enterprises', 'industries',
                                  'systems', 'technologies', 'solutions', 'services']
        
        query_lower_words = query_lower.split()
        
        # Check if query contains service indicators
        is_service_phrase = any(indicator in query_lower_words for indicator in service_indicators)
        
        # Check if query contains organization indicators
        is_organization = any(indicator in query_lower_words for indicator in organization_indicators)
        
        # Check if the capitalized phrase itself contains service/org words
        people_phrase = ' '.join(people).lower()
        is_people_phrase_service = any(indicator in people_phrase for indicator in service_indicators + organization_indicators)
        
        # Additional check: if query has 4+ words and contains service terms, it's likely a service
        is_long_service_query = len(words) >= 4 and is_service_phrase
        
        # If the query contains service/organization indicators, it's likely not a person name
        if is_service_phrase or is_organization or is_people_phrase_service or is_long_service_query:
            # Don't classify as person - let it fall through to service detection
            pass
        elif not is_service_phrase and len(people) == 1 and len(words) <= 4:
            # Strong signal if query is primarily a name (2-4 words, no service indicators)
            # Additional validation: person names typically don't have service keywords
            if not any(word in query_lower for word in service_indicators + organization_indicators):
                return "person_name", 0.9, signals
        
        # Executive role detection
        if roles or signals["question_word"] == "who":
            return "executive_role", 0.85, signals

    if roles and "who" in query_lower:
        return "executive_role", 0.8, signals

    # Navigational vs transactional vs informational
    if any(keyword in query_lower for keyword in NAVIGATIONAL_KEYWORDS):
        return "navigational", 0.75, signals

    if any(keyword in query_lower for keyword in TRANSACTIONAL_KEYWORDS):
        return "transactional", 0.7, signals

    # Local service detection (service + location)
    if services and (signals["has_local_modifier"] or signals["has_location"] or signals["has_zip_code"]):
        return "local_service", 0.82, signals

    # Service detection - check for service keywords or service-like patterns
    # Also check if query contains service-related words even if not in SERVICE_KEYWORDS
    service_like_patterns = [
        r'\b\w+\s+management\b',
        r'\b\w+\s+systems?\b',
        r'\b\w+\s+services?\b',
        r'\b\w+\s+solutions?\b',
        r'\b\w+\s+consulting\b',
        r'\b\w+\s+engineering\b',
    ]
    has_service_pattern = any(re.search(pattern, query_lower) for pattern in service_like_patterns)
    
    if services or has_service_pattern:
        return "service", 0.8, signals

    # Sector detection
    if any(keyword in query_lower for keyword in SECTOR_KEYWORDS) or any(phrase in query_lower for phrase in SECTOR_PHRASES):
        return "sector", 0.65, signals

    # Case study detection
    if signals["has_case_study_signal"]:
        return "case_study", 0.6, signals

    # Regulatory detection
    if signals["has_regulatory_signal"]:
        return "regulatory", 0.6, signals

    # Question-based intent detection with better context
    if signals["is_question"]:
        question_word = signals.get("question_word", "")
        if question_word in {"how", "what", "why"}:
            return "howto", 0.65, signals
        elif question_word == "who":
            # "Who" questions might be about people or roles
            if roles:
                return "executive_role", 0.75, signals
            return "informational", 0.6, signals
        return "informational", 0.6, signals

    # Default to general if no specific intent detected
    return "general", 0.4, signals


def _analyze_query_with_ai(query: str, llm_client) -> Optional[Dict[str, Any]]:
    """
    Use AI to analyze query intent and extract entities.
    
    Args:
        query: The search query to analyze
        llm_client: CerebrasLLM client instance (optional)
    
    Returns:
        Dictionary with AI analysis or None if AI analysis fails
    """
    if not llm_client:
        return None
    
    try:
        prompt = f"""You are an expert at analyzing search queries for an environmental consulting firm (SCS Engineers). 
Analyze the following query and identify its intent, entities, and context.

Query: "{query}"

CONTEXT UNDERSTANDING RULES:

1. **Service vs Person Name Detection**:
   - Service phrases: "Supply Chain Management Systems", "Waste Management Solutions", "Environmental Compliance Services"
   - Person names: "John Smith", "James Walsh", "Mary Johnson" (typically 2-3 capitalized words, no service keywords)
   - If query contains words like "management", "system", "service", "solution", "chain", "supply", "compliance" → it's a SERVICE
   - If query is just a name (2-3 words, all capitalized, no service terms) → it's a PERSON_NAME

2. **Intent Types**:
   - **service**: Queries about services, solutions, capabilities (e.g., "hazardous waste management", "environmental consulting")
   - **person_name**: Looking for a specific person (e.g., "James Walsh", "John Smith")
   - **executive_role**: Looking for leadership (e.g., "who is the CEO", "president of company")
   - **sector**: Industry/domain queries (e.g., "environmental sector", "waste industry")
   - **navigational**: Looking for specific pages (e.g., "contact", "about us", "careers")
   - **transactional**: Action-oriented (e.g., "request quote", "apply for job", "download report")
   - **howto**: How-to questions (e.g., "how to comply", "how does remediation work")
   - **case_study**: Project/case study queries (e.g., "landfill project", "remediation case study")
   - **regulatory**: Compliance/regulation queries (e.g., "EPA regulations", "compliance requirements")
   - **general**: General informational queries

3. **Entity Extraction**:
   - **people**: Actual person names (not service names that look like names)
   - **roles**: Job titles (CEO, director, manager, etc.)
   - **services**: Service offerings, solutions, capabilities
   - **sectors**: Industries, domains, fields
   - **locations**: Cities, states, regions, geographic areas
   - **organizations**: Company names, agencies, institutions
   - **regulatory**: Regulatory terms, compliance-related keywords

4. **Context Clues**:
   - Question words (who, what, where, how) indicate informational intent
   - Action words (request, apply, download) indicate transactional intent
   - Service keywords (management, system, solution) indicate service intent
   - Location words (near me, in California) indicate local_service intent

EXAMPLES:
- "Supply Chain Management Systems" → intent: "service", entities: {{"services": ["supply chain management systems"]}}
- "James Walsh" → intent: "person_name", entities: {{"people": ["James Walsh"]}}
- "Who is the CEO?" → intent: "executive_role", entities: {{"roles": ["CEO"]}}
- "Waste management services in California" → intent: "local_service", entities: {{"services": ["waste management"], "locations": ["California"]}}
- "How to comply with EPA regulations" → intent: "howto", entities: {{"regulatory": ["EPA", "regulations"]}}
- "Environmental remediation case study" → intent: "case_study", entities: {{"services": ["environmental remediation"]}}
- "Hazardous Waste Management" → intent: "service", entities: {{"services": ["hazardous waste management"]}}
- "Environmental Compliance Solutions" → intent: "service", entities: {{"services": ["environmental compliance solutions"]}}
- "Landfill Gas Collection Systems" → intent: "service", entities: {{"services": ["landfill gas collection systems"]}}
- "PFAS Treatment Technologies" → intent: "service", entities: {{"services": ["PFAS treatment technologies"]}}
- "Contact us" → intent: "navigational", entities: {{}}
- "Request a quote" → intent: "transactional", entities: {{}}
- "Environmental sector trends" → intent: "sector", entities: {{"sectors": ["environmental"]}}

Return ONLY a JSON object with this structure:
{{
    "intent": "service",
    "confidence": 0.85,
    "entities": {{
        "people": [],
        "roles": [],
        "services": ["waste management"],
        "sectors": ["environmental"],
        "locations": [],
        "organizations": [],
        "regulatory": []
    }},
    "signals": {{
        "is_question": false,
        "has_service_keyword": true,
        "has_location": false,
        "has_role_keyword": false,
        "has_organization": false
    }},
    "keywords": ["waste", "management"]
}}

CRITICAL: Return ONLY valid JSON, no explanatory text before or after."""

        # Use synchronous client for query analysis
        response = llm_client.client.chat.completions.create(
            model=llm_client.model,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing search queries for intent and entities. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks and extra text)
        ai_analysis = None
        
        # Try direct parsing first
        try:
            ai_analysis = json.loads(result_text)
        except json.JSONDecodeError:
            # Try extracting from markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Try parsing again after extracting from code blocks
            try:
                ai_analysis = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to find JSON object with balanced braces
                brace_count = 0
                start_idx = -1
                for i, char in enumerate(result_text):
                    if char == '{':
                        if start_idx == -1:
                            start_idx = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_idx != -1:
                            json_str = result_text[start_idx:i+1]
                            try:
                                ai_analysis = json.loads(json_str)
                                break
                            except json.JSONDecodeError:
                                start_idx = -1
                                brace_count = 0
                                continue
                
                if ai_analysis is None:
                    # If we get here, no valid JSON found
                    raise ValueError("Could not extract JSON from AI response")
        
        # Validate structure
        if not isinstance(ai_analysis, dict):
            return None
        
        # Ensure required fields exist
        ai_analysis.setdefault("intent", "general")
        ai_analysis.setdefault("confidence", 0.5)
        ai_analysis.setdefault("entities", {})
        ai_analysis.setdefault("signals", {})
        ai_analysis.setdefault("keywords", [])
        
        logger.info(f"AI query analysis: intent={ai_analysis.get('intent')}, confidence={ai_analysis.get('confidence')}")
        return ai_analysis
        
    except Exception as e:
        logger.warning(f"AI query analysis failed: {e}, falling back to heuristic analysis")
        return None


def analyze_query(query: str, llm_client=None, use_ai: bool = True) -> Dict[str, Any]:
    """
    Perform analysis of a query, identifying intent and entities.
    Can use AI (LLM) for enhanced analysis, with heuristic fallback.

    Args:
        query: The search query to analyze
        llm_client: Optional CerebrasLLM client for AI analysis
        use_ai: Whether to attempt AI analysis (default: True)

    Returns:
        Dictionary suitable for JSON serialization with intent, entities, etc.
    """
    original_query = query or ""
    query = original_query.strip()
    query_lower = query.lower()

    # Try AI analysis first if available
    ai_analysis = None
    if use_ai and llm_client:
        ai_analysis = _analyze_query_with_ai(query, llm_client)
    
    # Always perform heuristic analysis as fallback/validation
    people = _extract_capitalized_phrases(query)
    roles = _extract_roles(query_lower)
    services = _extract_services(query_lower)
    locations = _extract_locations(query, query_lower)
    organizations = _extract_organizations(query, query_lower)

    intent, confidence, signals = _determine_intent(
        query,
        query_lower,
        people,
        roles,
        services,
        locations,
        organizations,
    )

    keywords = _tokenize_keywords(query_lower)

    sector_matches = {kw for kw in SECTOR_KEYWORDS if kw in query_lower}
    sector_matches.update({phrase for phrase in SECTOR_PHRASES if phrase in query_lower})

    regulatory_matches = [kw for kw in REGULATORY_KEYWORDS if kw in query_lower]

    entities = {
        "people": people,
        "roles": roles,
        "services": services,
        "sectors": sorted(sector_matches),
        "locations": locations,
        "organizations": organizations,
        "regulatory": regulatory_matches,
        "local_modifiers": [modifier for modifier in LOCAL_MODIFIERS if modifier in query_lower],
    }

    # Merge AI analysis if available (AI takes precedence for intent/confidence)
    if ai_analysis:
        # Use AI intent and confidence if available
        ai_intent = ai_analysis.get("intent")
        ai_confidence = ai_analysis.get("confidence", 0.0)
        
        if ai_intent and ai_confidence > 0.5:
            intent = ai_intent
            confidence = float(ai_confidence)
            logger.info(f"Using AI-detected intent: {intent} (confidence: {confidence})")
        
        # Merge entities (combine AI and heuristic)
        ai_entities = ai_analysis.get("entities", {})
        for entity_type in ["people", "roles", "services", "sectors", "locations", "organizations", "regulatory"]:
            ai_values = ai_entities.get(entity_type, [])
            if isinstance(ai_values, list) and ai_values:
                # Combine and deduplicate
                combined = list(set(entities.get(entity_type, []) + ai_values))
                entities[entity_type] = sorted(combined) if entity_type != "people" else combined
        
        # Merge signals
        ai_signals = ai_analysis.get("signals", {})
        signals.update(ai_signals)
        
        # Merge keywords
        ai_keywords = ai_analysis.get("keywords", [])
        if ai_keywords:
            combined_keywords = list(set(keywords + [kw.lower() for kw in ai_keywords if isinstance(kw, str)]))
            keywords = combined_keywords[:20]  # Limit to 20 keywords

    primary_entities: List[str] = []
    if people or entities.get("people"):
        primary_entities.append("people")
    if services or entities.get("services"):
        primary_entities.append("services")
    if entities["sectors"]:
        primary_entities.append("sectors")
    if locations or entities.get("locations"):
        primary_entities.append("locations")
    if organizations or entities.get("organizations"):
        primary_entities.append("organizations")
    if regulatory_matches or entities.get("regulatory"):
        primary_entities.append("regulatory")

    analysis = QueryAnalysis(
        intent=intent,
        confidence=confidence,
        entities=entities,
        signals=signals,
        normalized_query=query_lower,
        keywords=keywords,
        primary_entities=primary_entities,
    )

    result = analysis.to_dict()
    result["original_query"] = original_query
    result["analysis_method"] = "ai_enhanced" if ai_analysis else "heuristic"
    return result

