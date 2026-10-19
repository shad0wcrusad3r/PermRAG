"""Access control logic."""
from typing import Dict, Any
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range


class User:
    """User identity from JWT."""

    def __init__(self, user_id: str, tenant_id: str, department: str, role_level: int):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.department = department
        self.role_level = role_level


def build_filter(user: User) -> Filter:
    """Build Qdrant filter for user's permissions.

    Access rule:
    - Same tenant
    - min_role_level <= user.role_level
    - If role_level < 4: (department == "all" OR department == user.department)
    """
    must = [
        FieldCondition(key="tenant_id", match=MatchValue(value=user.tenant_id)),
        FieldCondition(key="min_role_level", range=Range(lte=user.role_level)),
    ]

    # Role level 4 (hr_admin) can see all departments
    if user.role_level < 4:
        must.append(
            Filter(
                should=[
                    FieldCondition(key="department", match=MatchValue(value="all")),
                    FieldCondition(key="department", match=MatchValue(value=user.department)),
                ]
            )
        )

    return Filter(must=must)


def is_allowed(user: User, chunk: Dict[str, Any]) -> bool:
    """Check if user is allowed to access a chunk (Python-side check for testing)."""
    # Tenant check
    if chunk["tenant_id"] != user.tenant_id:
        return False

    # Role level check
    if chunk["min_role_level"] > user.role_level:
        return False

    # Department check (only if not hr_admin)
    if user.role_level < 4:
        if chunk["department"] != "all" and chunk["department"] != user.department:
            return False

    return True


def permission_signature(user: User) -> str:
    """Generate permission signature for cache keying."""
    dept = user.department if user.role_level < 4 else "*"
    return f"{user.tenant_id}|{dept}|{user.role_level}"
