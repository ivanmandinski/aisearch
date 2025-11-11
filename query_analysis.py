"""
Heuristic-based query analysis utilities shared across search components.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set

try:
    from config import settings
except Exception:  # pragma: no cover - fallback when config unavailable
    settings = None

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


def _extract_capitalized_phrases(query: str) -> List[str]:
    """Extract candidate proper nouns/person names."""
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b"
    matches = re.findall(pattern, query)
    # Filter out words that are clearly not names (e.g., All Caps)
    cleaned = []
    for match in matches:
        words = match.split()
        if all(word[0].isupper() and word[1:].islower() for word in words):
            cleaned.append(match.strip())
    return cleaned


def _extract_services(query_lower: str) -> List[str]:
    matches = {kw for kw in SERVICE_KEYWORDS if kw in query_lower}
    for phrase in SERVICE_PHRASES:
        if phrase in query_lower:
            matches.add(phrase)
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

    # Person / executive detection
    if people:
        if len(people) == 1 and len(words) <= 4:
            # Strong signal if query is primarily a name
            return "person_name", 0.9, signals
        if roles or signals["question_word"] == "who":
            return "executive_role", 0.85, signals

    if roles and "who" in query_lower:
        return "executive_role", 0.8, signals

    # Navigational vs transactional vs informational
    if any(keyword in query_lower for keyword in NAVIGATIONAL_KEYWORDS):
        return "navigational", 0.75, signals

    if any(keyword in query_lower for keyword in TRANSACTIONAL_KEYWORDS):
        return "transactional", 0.7, signals

    if services and (signals["has_local_modifier"] or signals["has_location"] or signals["has_zip_code"]):
        return "local_service", 0.82, signals

    if services:
        return "service", 0.8, signals

    if any(keyword in query_lower for keyword in SECTOR_KEYWORDS) or any(phrase in query_lower for phrase in SECTOR_PHRASES):
        return "sector", 0.65, signals

    if signals["has_case_study_signal"]:
        return "case_study", 0.6, signals

    if signals["has_regulatory_signal"]:
        return "regulatory", 0.6, signals

    if signals["is_question"]:
        if signals["question_word"] in {"how", "what", "why"}:
            return "howto", 0.65, signals
        return "informational", 0.6, signals

    return "general", 0.4, signals


def analyze_query(query: str) -> Dict[str, Any]:
    """
    Perform heuristic analysis of a query, identifying intent and entities.

    Returns a dictionary suitable for JSON serialization.
    """
    original_query = query or ""
    query = original_query.strip()
    query_lower = query.lower()

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

    primary_entities: List[str] = []
    if people:
        primary_entities.append("people")
    if services:
        primary_entities.append("services")
    if entities["sectors"]:
        primary_entities.append("sectors")
    if locations:
        primary_entities.append("locations")
    if organizations:
        primary_entities.append("organizations")
    if regulatory_matches:
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
    return result

