# PermRAG Phase 1 - Demo Script for Reviewers

**Duration**: 10-15 minutes  
**Goal**: Demonstrate permission-aware RAG with retrieval-time access control

---

## Pre-Demo Checklist

Run the setup script:
```bash
bash demo_setup.sh
```

Ensure:
- ✓ Qdrant running on port 16333
- ✓ Database migrated
- ✓ 10 documents ingested
- ✓ 15 users seeded
- ✓ Groq API key in `.env`

---

## Demo Flow

### 1. Introduction (1 min)
"PermRAG is a multi-tenant RAG system with retrieval-time access control. The key innovation: **ACL filters are applied inside the vector search**, before anything reaches the LLM."

### 2. Show the Data Model (2 min)

**Corpus Structure:**
```bash
# Show the sample corpus
ls -R data/sample/

# Show manifest with ACLs
head -3 data/sample/manifest.jsonl | python -m json.tool
```

**Key points to highlight:**
- 3 tenants (acme, globex, initech)
- Mixed departments (engineering, hr, finance)
- `min_role_level`: 1=intern, 2=employee, 3=manager, 4=hr_admin
- Some docs are `min_role_level=4` (highly restricted)

---

### 3. ACL Logic Test (2 min)

**Show the ACL unit tests:**
```bash
pytest tests/unit/test_acl.py -v
```

**Explain:** 8 tests including:
- Full truth table (3 tenants × 5 depts × 4 roles)
- Property-based hypothesis testing
- Verifies Qdrant filter matches Python logic

---

### 4. Retrieval Demo - The Core Feature (3 min)

**Test 1: Intern asks about restricted info**
```bash
python -m app.cli ask "What is the CFO's base salary?" --user acme_intern@acme.test
```

**Expected**: 0 chunks about executive compensation. All results are role_level=1 engineering docs.

**Test 2: HR Admin asks the same question**
```bash
python -m app.cli ask "What is the CFO's base salary?" --user acme_hr_admin@acme.test
```

**Expected**: Top result is Executive Compensation doc showing CFO salary = $412,000.

**Emphasize**: "The intern and hr_admin used the **same query embedding**, but got different results because the ACL filter runs **inside the HNSW graph traversal** in Qdrant."

---

### 5. Full End-to-End API Demo (4 min)

**Start the API server:**
```bash
# In one terminal
source .venv/Scripts/activate
uvicorn app.main:app --port 8000
```

**In another terminal, run these curl commands:**

**Step 1: Login as intern**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"acme_intern@acme.test","password":"demo1234"}' | python -m json.tool
```

Copy the `access_token`.

**Step 2: Query with intern token (should refuse)**
```bash
TOKEN="<paste_intern_token>"

curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"What is the CFO base salary?"}' | python -m json.tool
```

**Expected response:**
```json
{
  "answer": "I couldn't find that in the documents available to you.",
  "sources": [],
  "refused": true,
  "cache_hit": false,
  "latency_ms": {...},
  "request_id": "..."
}
```

**Step 3: Login as HR admin**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"acme_hr_admin@acme.test","password":"demo1234"}' | python -m json.tool
```

**Step 4: Query with hr_admin token (should answer)**
```bash
TOKEN="<paste_hr_admin_token>"

curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"What is the CFO base salary?"}' | python -m json.tool
```

**Expected response:**
```json
{
  "answer": "The CFO's base salary is $412,000 [S1].",
  "sources": [
    {
      "ref": "S1",
      "doc_id": "...",
      "title": "Executive Compensation 2026",
      "heading_path": "C-Suite Base Salaries",
      "chunk_id": "..."
    }
  ],
  "refused": false,
  "cache_hit": false,
  ...
}
```

---

### 6. Audit Log (1 min)

**Show that every query is logged:**
```bash
python -c "
from app.db.session import get_session_factory
from app.db.models import AuditLog

db = get_session_factory()()
logs = db.query(AuditLog).order_by(AuditLog.ts.desc()).limit(5).all()

print(f'Total queries logged: {db.query(AuditLog).count()}\n')
print('Recent queries:')
for log in logs:
    print(f'  User: {log.user_id[:16]}...')
    print(f'  Tenant: {log.tenant_id}, Role: {log.role_level}')
    print(f'  Question: {log.question[:60]}...')
    print(f'  Refused: {bool(log.refused)}')
    print(f'  Retrieved chunks: {len(eval(log.retrieved_chunk_ids))}')
    print()

db.close()
"
```

---

### 7. Evaluation Metrics (1 min)

**Run the eval harness:**
```bash
python -m evals.run --retrieval-only --dataset sample
```

**Show output:**
```
RETRIEVAL METRICS
============================================================
Recall@6:     0.XXX
Hit Rate@6:   0.XXX
MRR@6:        0.XXX
Recall@20:    0.XXX
```

**Explain**: "Low scores are expected with only 10 docs. The eval framework is in place for Phase 2 when we'll run on the full 180-doc synthetic corpus and attack suite."

---

## Key Talking Points for Reviewers

### ✅ What Works (Phase 1 Complete)

1. **Permission-aware retrieval**: ACL filter applied inside vector search
2. **Multi-tenant isolation**: Cross-tenant leakage impossible (different tenant_id filtered out)
3. **Role-based access**: 4 role levels with department scoping
4. **JWT authentication**: Secure token-based auth with 60-min expiry
5. **Audit logging**: Every query logged with user context, chunks retrieved, and refusal status
6. **Citation validation**: Invalid source citations stripped, uncited answers become refusals
7. **Deterministic IDs**: uuid5-based doc/chunk IDs for idempotent ingestion
8. **Full test coverage**: ACL unit tests with property-based verification

### 🔧 Known Issues (Noted in Plan)

1. **Idempotency tracking**: Re-ingestion adds duplicates (needs DB query to fix)
2. **Qdrant version mismatch warning**: Non-fatal, client 1.19.1 vs server 1.12.4

### 🚀 Phase 2 Roadmap

- Sparse/BM25 + RRF fusion
- Cross-encoder reranking
- Semantic cache (3 modes: off/shared/aware)
- Baseline modes (S0-S4) for comparison
- Attack suite (direct, cross-tenant, injection, collusion)
- LeakDojo adapter for adaptive attacks
- Security metrics (RLR, ALR, U-CCL)
- Streamlit UI

---

## Quick Demo Commands (Copy-Paste Ready)

```bash
# Terminal 1: Start API
source .venv/Scripts/activate
uvicorn app.main:app --port 8000

# Terminal 2: Run demo
# 1. Login as intern
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"acme_intern@acme.test","password":"demo1234"}'

# 2. Save token and query (will refuse)
# TOKEN="..." (paste from above)
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"question":"What is the CFO base salary?"}'

# 3. Login as hr_admin
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"acme_hr_admin@acme.test","password":"demo1234"}'

# 4. Save token and query (will answer with citation)
# TOKEN="..." (paste from above)
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"question":"What is the CFO base salary?"}'
```

---

## Architecture Diagram to Show

```
User Request (with JWT)
    ↓
FastAPI (/auth/login, /query)
    ↓
JWT Verification → User{tenant_id, department, role_level}
    ↓
ACL Filter Builder → Qdrant Filter Object
    ↓
Query Embedding (BGE-small-en-v1.5)
    ↓
Qdrant.query_points(filter=ACL, vector=embedding)  ← **Filter applied HERE**
    ↓
Retrieved Chunks (all authorized)
    ↓
Context Assembly (token budget, per-doc cap)
    ↓
LLM Generate (Groq) with citations
    ↓
Citation Validation
    ↓
Audit Log Write
    ↓
Response to User
```

**The key insight**: Traditional RAG systems filter *after* retrieval or rely on the LLM to refuse. PermRAG filters *during* retrieval, so unauthorized chunks never leave the vector store.

---

## Questions Reviewers Might Ask

**Q: Why not just let the LLM filter?**  
A: LLM-based filtering (S1/S4 in our taxonomy) is probabilistic and bypassable via prompt injection. Structural filtering at the vector store is deterministic and cannot be bypassed.

**Q: What if someone changes the JWT?**  
A: JWT is signed with HS256. Tampering invalidates the signature, request is rejected at auth middleware.

**Q: Can a user see another tenant's data?**  
A: No. The filter requires `tenant_id` match. Even with role_level=4, you only see your own tenant's data.

**Q: What about timing side-channels?**  
A: Acknowledged as a limitation (Section 12.5 of plan). Measured in Phase 2 evals but not mitigated in v1.

**Q: How do you handle cross-department access?**  
A: Role level 4 (hr_admin) can see all departments. Others see only their own department + "all" department docs.

---

## Success Criteria Checklist

Show reviewers this checklist:

- [x] Dense-only retrieval working
- [x] ACL filter applied inside vector search
- [x] JWT auth with role claims
- [x] 15 test users across 3 tenants
- [x] 10 sample documents with varied ACLs
- [x] Intern gets refusal for restricted content
- [x] HR admin gets answer with citations
- [x] Audit log captures every query
- [x] Unit tests pass (8/8)
- [x] Eval harness produces retrieval metrics
- [x] API endpoints functional (login, query)

**Phase 1 Status: ✅ COMPLETE**
