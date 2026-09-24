"""
GeoVault AI - User Context & Authorized Scope Definitions
Encapsulates identity attributes and resolved retrieval boundaries.
"""

from typing import Optional, Set, List, Dict, Any
from pydantic import BaseModel, Field
from app.security.clearance import is_clearance_sufficient, ClearanceLevel


class ScopeRule(BaseModel):
    mine_code: Optional[str] = None
    department: Optional[str] = None
    max_classification: str = "INTERNAL"


class UserContext(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    department: str
    clearance_level: str
    assigned_mine_code: Optional[str] = None
    is_active: bool = True
    scopes: List[ScopeRule] = Field(default_factory=list)


class AuthorizedScope:
    """
    Resolved operational & retrieval boundary for a user request.
    Enforces authorization BEFORE any database retrieval occurs.
    """

    def __init__(
        self,
        user_id: str,
        role: str,
        allowed_mines: Optional[Set[str]],
        allowed_departments: Optional[Set[str]],
        max_clearance: str,
        can_access_macro: bool = True,
    ):
        self.user_id = user_id
        self.role = role
        # None means unrestricted (e.g. HQ Admin); empty set means no mines permitted; otherwise set of permitted mine codes
        self.allowed_mines = allowed_mines
        # None means unrestricted across departments; otherwise set of permitted departments
        self.allowed_departments = allowed_departments
        self.max_clearance = max_clearance
        self.can_access_macro = can_access_macro

    MINE_ALIAS_SETS: Dict[str, Set[str]] = {
        "GV001": {"GV001", "GEVRA", "M-GEVRA", "DEOM-01"},
        "GEVRA": {"GV001", "GEVRA", "M-GEVRA", "DEOM-01"},
        "DEOM-01": {"GV001", "GEVRA", "M-GEVRA", "DEOM-01"},
        "GV002": {"GV002", "KUSMUNDA", "M-KUSMUNDA", "KNUG-02"},
        "KUSMUNDA": {"GV002", "KUSMUNDA", "M-KUSMUNDA", "KNUG-02"},
        "KNUG-02": {"GV002", "KUSMUNDA", "M-KUSMUNDA", "KNUG-02"},
        "GV003": {"GV003", "DIPKA", "M-DIPKA"},
        "DIPKA": {"GV003", "DIPKA", "M-DIPKA"},
        "GV004": {"GV004", "NIGAHI", "M-NIGAHI"},
        "NIGAHI": {"GV004", "NIGAHI", "M-NIGAHI"},
        "GV005": {"GV005", "DUDHICHUA", "M-DUDHICHUA", "SSOP-03"},
        "DUDHICHUA": {"GV005", "DUDHICHUA", "M-DUDHICHUA", "SSOP-03"},
        "SSOP-03": {"GV005", "DUDHICHUA", "M-DUDHICHUA", "SSOP-03"},
    }

    def is_mine_permitted(self, mine_code: Optional[str]) -> bool:
        """Evaluates whether access to data for a specific mine is permitted."""
        if mine_code is None or mine_code == "" or mine_code.upper() in ["ALL", "NATIONAL", "NONE"]:
            return self.can_access_macro
        if self.allowed_mines is None:
            return True
        if mine_code in self.allowed_mines:
            return True
        aliases = self.MINE_ALIAS_SETS.get(mine_code.upper())
        if aliases and bool(aliases.intersection(self.allowed_mines)):
            return True
        return False

    def is_department_permitted(self, department: Optional[str]) -> bool:
        """Evaluates whether access to a department's records is permitted."""
        if department is None or department == "" or department.upper() in ["ALL", "GENERAL"]:
            return True
        if self.allowed_departments is None:
            return True
        return department in self.allowed_departments

    def is_classification_permitted(self, classification: Optional[str]) -> bool:
        """Evaluates whether resource classification is within maximum clearance rank."""
        return is_clearance_sufficient(self.max_clearance, classification)

    def is_resource_authorized(
        self,
        mine_code: Optional[str],
        department: Optional[str] = None,
        classification: Optional[str] = None,
    ) -> bool:
        """Combined RBAC + ABAC authorization check for a single resource."""
        if not self.is_mine_permitted(mine_code):
            return False
        if not self.is_department_permitted(department):
            return False
        if not self.is_classification_permitted(classification):
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "allowed_mines": list(self.allowed_mines) if self.allowed_mines is not None else "ALL",
            "allowed_departments": list(self.allowed_departments) if self.allowed_departments is not None else "ALL",
            "max_clearance": self.max_clearance,
            "can_access_macro": self.can_access_macro,
        }
