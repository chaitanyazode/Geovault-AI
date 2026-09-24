"""
GeoVault AI - Deterministic Query Router
Classifies natural language queries into operational execution routes:
- SQL: Structured single-point facts and registered metrics
- ANALYTICS: Multi-mine comparisons, totals, averages, and trend trajectories
- RAG: Qualitative geological, safety, inspection, and memo narratives
- HYBRID: Multi-source causality and explanation (Structured Facts + Document Evidence)
- TOPIC: Automated topic modeling and keyword terminology
- REPORT: Formal executive/operational report generation
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel


class RoutedQuery(BaseModel):
    query: str
    route: str  # SQL, RAG, HYBRID, ANALYTICS, TOPIC, REPORT
    target_mine: Optional[str] = None
    compared_mines: List[str] = []
    target_year: Optional[int] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    domain: Optional[str] = None
    confidence: float = 1.0
    rationale: str = ""


class DeterministicQueryRouter:
    """
    Deterministic rule-based query router.
    Enforces deterministic routing first according to AGENTS.md.
    """

    MINE_ALIASES = {
        # Canonical 5 Mines (Authoritative Dataset)
        "gevra": "GEVRA",
        "gevra ocp": "GEVRA",
        "gv001": "GEVRA",
        "kusmunda": "KUSMUNDA",
        "kusmunda ocp": "KUSMUNDA",
        "gv002": "KUSMUNDA",
        "dipka": "DIPKA",
        "dipka ocp": "DIPKA",
        "gv003": "DIPKA",
        "nigahi": "NIGAHI",
        "nigahi ocp": "NIGAHI",
        "gv004": "NIGAHI",
        "dudhichua": "DUDHICHUA",
        "dudhichua ocp": "DUDHICHUA",
        "gv005": "DUDHICHUA",
        # Legacy Demo Mines
        "deom-01": "DEOM-01",
        "deom01": "DEOM-01",
        "dharani east": "DEOM-01",
        "dharani": "DEOM-01",
        "knug-02": "KNUG-02",
        "knug02": "KNUG-02",
        "koyna north": "KNUG-02",
        "koyna": "KNUG-02",
        "ssop-03": "SSOP-03",
        "ssop03": "SSOP-03",
        "sona shila": "SSOP-03",
        "sonashila": "SSOP-03",
    }

    DOMAIN_KEYWORDS = {
        "production_annual": ["production", "output", "target", "achievement", "variance"],
        "equipment_fleet": ["equipment", "fleet", "dumper", "shovel", "dragline", "availability", "operating hours", "breakdown", "hemm"],
        "safety_records": ["safety", "incident", "accident", "dgms", "injury", "fatality", "ltifr", "statutory notice"],
        "environmental_records": ["environment", "environmental", "pm10", "pm2.5", "air quality", "water treatment", "plantation", "reclamation"],
        "coal_seams": ["coal seam", "seam", "thickness", "seams present"],
        "boreholes_master": ["borehole", "drill hole", "stratigraphy", "lithology", "interval"],
        "geotechnical_zones": ["geotechnical", "risk zone", "slope stability", "bench"],
        "dispatch_summary": ["dispatch", "transport", "logistics", "rake", "wagon", "rail backlog"],
        "coal_quality": ["coal quality", "ash", "gcv", "moisture", "grade", "calorific"],
        "geological_units": ["geology", "geological", "strata", "fault", "rqd", "overburden", "formation"],
        "mining_issue_log": ["issue", "breakdown", "downtime", "haul road", "congestion", "problem"],
        "inspection_register": ["inspection", "statutory", "violation", "safety notice", "audit"],
    }

    @classmethod
    def extract_mines(cls, text: str) -> List[str]:
        """Extracts canonical mine codes from text."""
        lowered = text.lower()
        found = []
        for alias, code in cls.MINE_ALIASES.items():
            # Check whole word / token match
            if re.search(r"\b" + re.escape(alias) + r"\b", lowered):
                if code not in found:
                    found.append(code)
        return found

    @classmethod
    def extract_years(cls, text: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Extracts single year or year range (target_year, start_year, end_year)."""
        # Range patterns like 2021-2025 or between 2023 and 2024
        range_match = re.search(r"\b(202[0-9])\s*(?:-|to|and)\s*(202[0-9])\b", text, re.IGNORECASE)
        if range_match:
            sy = int(range_match.group(1))
            ey = int(range_match.group(2))
            return None, min(sy, ey), max(sy, ey)

        # FY patterns like FY2024-25 or FY2024 or FY24
        fy_split = re.search(r"\bfy\s*(202[0-9])-(?:2[0-9]|[0-9]{2})\b", text, re.IGNORECASE)
        if fy_split:
            return int(fy_split.group(1)), None, None

        fy_match = re.search(r"\bfy\s*(202[0-9])\b", text, re.IGNORECASE)
        if fy_match:
            return int(fy_match.group(1)), None, None

        # General 4 digit year
        years = [int(y) for y in re.findall(r"\b(202[0-9])\b", text)]
        if len(years) == 1:
            return years[0], None, None
        elif len(years) > 1:
            return None, min(years), max(years)

        # 5-year trend pattern
        if re.search(r"\b5\s*-?\s*year\b", text, re.IGNORECASE):
            return None, 2021, 2025

        return None, None, None

    @classmethod
    def route_query(cls, query: str) -> RoutedQuery:
        """
        Classifies query into SQL, ANALYTICS, RAG, SPATIAL, GEOLOGY, HYBRID, TOPIC, or REPORT.
        """
        text = query.strip()
        lowered = text.lower()

        # 1. Extract entities
        mines = cls.extract_mines(text)
        target_year, start_year, end_year = cls.extract_years(text)

        # Determine target mine
        target_mine = mines[0] if len(mines) == 1 else None
        compared_mines = mines if len(mines) > 1 else []

        # Detect domain hint
        domain_hint = None
        for d, kws in cls.DOMAIN_KEYWORDS.items():
            if any(kw in lowered for kw in kws):
                domain_hint = d
                break

        # 2. Rule: REPORT
        if re.search(r"\b(generate|prepare|create|export|download|produce|build)\b.*?\b(report|dossier|document)\b", lowered) or re.search(r"\b(annual|performance|operational|executive|comparison|geological|safety)\s+report\b", lowered):
            return RoutedQuery(
                query=query,
                route="REPORT",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                start_year=start_year,
                end_year=end_year,
                domain=domain_hint,
                confidence=0.95,
                rationale="Detected formal report generation intent.",
            )

        # 3. Rule: TOPIC / WORD CLOUD
        if re.search(r"\b(topic|topics|word\s*cloud|keywords?|themes?|recurring\s+terminology)\b", lowered):
            return RoutedQuery(
                query=query,
                route="TOPIC",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                domain=domain_hint,
                confidence=0.95,
                rationale="Detected topic modeling or keyword extraction request.",
            )

        # 4. Rule: SPATIAL (PostGIS proximity, distance, containment, intersection)
        if re.search(r"\b(within\s+\d+\s*(?:m|meter|meters|metre|metres|km)?|distance\b|nearest\b|closest\b|proximity\b|intersects?\b|intersection\b|contains?\b|contained\b|buffer\b|geospatial|spatial|coordinates|latitude|longitude|boundary|lease)\b", lowered):
            return RoutedQuery(
                query=query,
                route="SPATIAL",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                domain=domain_hint or "spatial_boreholes",
                confidence=0.95,
                rationale="Detected geospatial or proximity query requiring PostGIS spatial operations.",
            )

        # 5. Rule: HYBRID (causality, why did X happen, explain shortfall/variance, correlation)
        if (
            re.search(r"\b(why|explain|reason|reasons|cause|causes|caused|factor|factors|decline|declined|shortfall|drop|gap|backlog|impact|contribute|contributed)\b", lowered)
            and re.search(r"\b(production|dispatch|target|change|changed|variance|performance|output)\b", lowered)
        ):
            return RoutedQuery(
                query=query,
                route="HYBRID",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                start_year=start_year,
                end_year=end_year,
                domain=domain_hint or "production_annual",
                confidence=0.92,
                rationale="Detected causality question requiring structured production metrics and narrative document evidence.",
            )

        # 6. Rule: ANALYTICS (comparison, trends, aggregations across mines or multi-year)
        if (
            len(compared_mines) > 1
            or re.search(r"\b(compare|comparison|versus|\bvs\b|difference between)\b", lowered)
            or re.search(r"\b(trend|trajectory|average|mean|total|growth rate|achievement|yoy|year-over-year|ranking|highest producer|lowest producer)\b", lowered)
        ):
            return RoutedQuery(
                query=query,
                route="ANALYTICS",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                start_year=start_year or 2021,
                end_year=end_year or 2025,
                domain=domain_hint or "production_annual",
                confidence=0.92,
                rationale="Detected comparative or multi-period analytical request.",
            )

        # 7. Rule: GEOLOGY (structural facts: seams present, seam thickness, borehole inventory)
        if re.search(r"\b(coal\s+seams?|seams?\s+present|thickness\s+of\s+coal|boreholes?\s+intersect|geotechnical\s+zones?|stratigraph(?:y|ic))\b", lowered):
            return RoutedQuery(
                query=query,
                route="GEOLOGY",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                domain=domain_hint or "coal_seams",
                confidence=0.92,
                rationale="Detected structured geological inventory query (seams, boreholes, geotechnical zones).",
            )

        # 8. Rule: RAG (qualitative inquiries into observations, notes, reports, qualitative summaries)
        if (
            re.search(r"\b(observations?|reported|condition|conditions|memo|unstructured|statutory|finding|audit observation|summarize)\b", lowered)
            or (re.search(r"\bgeolog", lowered) and re.search(r"\b(observation|condition|report)", lowered))
        ):
            return RoutedQuery(
                query=query,
                route="RAG",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                domain=domain_hint,
                confidence=0.90,
                rationale="Detected qualitative inquiry requiring semantic document chunk retrieval via BGE-M3.",
            )

        # 9. Rule: Conflict detection request
        if re.search(r"\b(conflict|conflicts|discrepanc(?:y|ies)|disagree(?:ment)?)\b", lowered):
            return RoutedQuery(
                query=query,
                route="SQL",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                domain="conflict_check",
                confidence=0.90,
                rationale="Detected request to surface registered conflicts.",
            )

        # 10. Default fallback: Structured SQL for entity lookup or RAG for general text
        if target_mine or target_year or domain_hint in ["production_annual", "equipment_fleet", "safety_records", "environmental_records"]:
            return RoutedQuery(
                query=query,
                route="SQL",
                target_mine=target_mine,
                compared_mines=compared_mines,
                target_year=target_year,
                start_year=start_year,
                end_year=end_year,
                domain=domain_hint or "production_annual",
                confidence=0.85,
                rationale="Detected factual single-point operational metric lookup.",
            )

        # General text fallback
        return RoutedQuery(
            query=query,
            route="RAG",
            target_mine=target_mine,
            compared_mines=compared_mines,
            target_year=target_year,
            domain=domain_hint,
            confidence=0.75,
            rationale="Defaulting to permission-aware semantic RAG retrieval.",
        )
