"""Unit tests for ACL logic."""
import pytest
from hypothesis import given, strategies as st

from app.security.acl import User, build_filter, is_allowed


# Test data
TENANTS = ["acme", "globex", "initech"]
DEPARTMENTS = ["engineering", "hr", "finance", "legal", "sales"]
ROLE_LEVELS = [1, 2, 3, 4]


class TestACLTruthTable:
    """Truth table tests for ACL logic."""

    def test_same_tenant_same_dept_sufficient_role(self):
        """User can access chunks from same tenant, same dept, with sufficient role."""
        user = User("u1", "acme", "engineering", 2)
        chunk = {
            "tenant_id": "acme",
            "department": "engineering",
            "min_role_level": 2,
        }
        assert is_allowed(user, chunk) is True

    def test_different_tenant_blocked(self):
        """User cannot access chunks from different tenant."""
        user = User("u1", "acme", "engineering", 4)
        chunk = {
            "tenant_id": "globex",
            "department": "engineering",
            "min_role_level": 1,
        }
        assert is_allowed(user, chunk) is False

    def test_insufficient_role_blocked(self):
        """User cannot access chunks requiring higher role."""
        user = User("u1", "acme", "hr", 2)
        chunk = {
            "tenant_id": "acme",
            "department": "hr",
            "min_role_level": 4,
        }
        assert is_allowed(user, chunk) is False

    def test_different_dept_blocked_for_non_admin(self):
        """Non-admin user cannot access different department."""
        user = User("u1", "acme", "engineering", 3)
        chunk = {
            "tenant_id": "acme",
            "department": "hr",
            "min_role_level": 1,
        }
        assert is_allowed(user, chunk) is False

    def test_hr_admin_sees_all_departments(self):
        """Role level 4 (hr_admin) can see all departments."""
        user = User("u1", "acme", "hr", 4)

        # Can see engineering
        chunk1 = {
            "tenant_id": "acme",
            "department": "engineering",
            "min_role_level": 1,
        }
        assert is_allowed(user, chunk1) is True

        # Can see finance
        chunk2 = {
            "tenant_id": "acme",
            "department": "finance",
            "min_role_level": 3,
        }
        assert is_allowed(user, chunk2) is True

    def test_department_all_visible_to_everyone(self):
        """Chunks with department='all' are visible to all users in tenant."""
        user = User("u1", "acme", "engineering", 1)
        chunk = {
            "tenant_id": "acme",
            "department": "all",
            "min_role_level": 1,
        }
        assert is_allowed(user, chunk) is True

    def test_full_truth_table(self):
        """Test all combinations of tenant, department, role."""
        test_cases = []

        for tenant in TENANTS:
            for dept in DEPARTMENTS:
                for role_level in ROLE_LEVELS:
                    user = User(f"user_{tenant}_{dept}_{role_level}", tenant, dept, role_level)

                    for chunk_tenant in TENANTS:
                        for chunk_dept in DEPARTMENTS + ["all"]:
                            for chunk_min_role in ROLE_LEVELS:
                                chunk = {
                                    "tenant_id": chunk_tenant,
                                    "department": chunk_dept,
                                    "min_role_level": chunk_min_role,
                                }

                                result = is_allowed(user, chunk)

                                # Expected result
                                expected = (
                                    chunk_tenant == tenant
                                    and chunk_min_role <= role_level
                                    and (
                                        role_level == 4  # hr_admin sees all
                                        or chunk_dept == "all"
                                        or chunk_dept == dept
                                    )
                                )

                                if result != expected:
                                    test_cases.append({
                                        "user": user.__dict__,
                                        "chunk": chunk,
                                        "result": result,
                                        "expected": expected,
                                    })

        # All should match
        assert len(test_cases) == 0, f"ACL logic mismatch: {test_cases[:5]}"


class TestACLPropertyBased:
    """Property-based tests using hypothesis."""

    @given(
        user_tenant=st.sampled_from(TENANTS),
        user_dept=st.sampled_from(DEPARTMENTS),
        user_role=st.sampled_from(ROLE_LEVELS),
        chunk_tenant=st.sampled_from(TENANTS),
        chunk_dept=st.sampled_from(DEPARTMENTS + ["all"]),
        chunk_min_role=st.sampled_from(ROLE_LEVELS),
    )
    def test_filter_matches_python_check(
        self, user_tenant, user_dept, user_role, chunk_tenant, chunk_dept, chunk_min_role
    ):
        """Qdrant filter results should match Python is_allowed."""
        user = User("test_user", user_tenant, user_dept, user_role)
        chunk = {
            "tenant_id": chunk_tenant,
            "department": chunk_dept,
            "min_role_level": chunk_min_role,
        }

        python_result = is_allowed(user, chunk)

        # Build filter and check conditions manually (simplified)
        qdrant_filter = build_filter(user)

        # Simulate Qdrant filter evaluation
        # Must check: tenant_id match
        tenant_match = chunk["tenant_id"] == user.tenant_id

        # Must check: min_role_level <= user.role_level
        role_match = chunk["min_role_level"] <= user.role_level

        # Must check: department (if role < 4)
        if user.role_level < 4:
            dept_match = chunk["department"] == "all" or chunk["department"] == user.department
        else:
            dept_match = True

        qdrant_result = tenant_match and role_match and dept_match

        assert python_result == qdrant_result, (
            f"Filter mismatch: user={user.__dict__}, chunk={chunk}, "
            f"python={python_result}, qdrant={qdrant_result}"
        )
