"""
GeoVault AI - Clearance & Classification Hierarchy (ABAC)
Defines classification ranks and comparison logic for Attribute-Based Access Control.
"""

from enum import Enum
from typing import Union


class ClearanceLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


# Monotonic numeric rank hierarchy
CLEARANCE_RANKS = {
    ClearanceLevel.PUBLIC: 0,
    ClearanceLevel.INTERNAL: 1,
    ClearanceLevel.RESTRICTED: 2,
    ClearanceLevel.CONFIDENTIAL: 3,
}


def get_clearance_rank(level: Union[ClearanceLevel, str, None]) -> int:
    """Returns the integer rank of a clearance/classification level."""
    if level is None:
        return 0
    clean_level = str(level).strip().upper()
    try:
        return CLEARANCE_RANKS[ClearanceLevel(clean_level)]
    except (ValueError, KeyError):
        # Default unknown or unclassified items to lowest rank
        return 0


def is_clearance_sufficient(user_clearance: Union[ClearanceLevel, str], resource_classification: Union[ClearanceLevel, str, None]) -> bool:
    """
    Evaluates whether a user's clearance level is sufficient to access a resource
    with the given classification level.
    e.g., user with RESTRICTED (rank 2) can access PUBLIC (0), INTERNAL (1), RESTRICTED (2),
    but cannot access CONFIDENTIAL (3).
    """
    u_rank = get_clearance_rank(user_clearance)
    r_rank = get_clearance_rank(resource_classification)
    return u_rank >= r_rank
