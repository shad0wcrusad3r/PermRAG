# PermRAG Phase 1 - Quick Start Guide

> All commands below are for **Windows PowerShell**, run from the project root
> (`C:\Antigravity\sem7\sdp`). Every block is copy-paste safe.

## Prerequisites
- Python 3.11+
- Docker Desktop running
- Groq API key (free at https://console.groq.com)

## Setup (5 minutes)

### 1. Activate the Virtual Environment
```powershell
cd C:\Antigravity\sem7\sdp
.venv\Scripts\Activate.ps1
```
> If PowerShell blocks the script, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. Configure `.env`
Make sure these lines are set in `.env`:
```
GROQ_API_KEY=your_actual_key_from_groq_console
GROQ_MODEL=openai/gpt-oss-120b
```
> Groq retires models periodically. To see which models your key can use:
> ```powershell
> python -c "from app.rag.generate import get_llm_client; print('\n'.join(sorted(m.id for m in get_llm_client().client.models.list().data)))"
> ```

### 3. Verify Setup
```powershell
# Qdrant is running
docker ps | Select-String qdrant

# Database exists
Test-Path data/permrag.db

# Chunks ingested
python -W ignore check_chunks.py

# Users seeded
python -c "from app.db.session import get_session_factory; from app.db.models import User; db=get_session_factory()(); print(f'Users: {db.query(User).count()}'); db.close()"
```

Expected output:
- `permrag_qdrant` container listed as `Up`
- `True`
- `Chunks: 52` (10 docs, 4-8 chunks each)
- `Users: 15`

## Test Phase 1 (2 minutes)

### Option A: Interactive Web Interface (Recommended)
You can run and inspect all QuickStart steps directly in the browser:
```powershell
streamlit run ui/streamlit_app.py --server.port 8080
```
Open **http://localhost:8080** in your browser. The dashboard includes:
- **Setup & Diagnostics:** Live status of Qdrant, SQLite, seed users, chunk counts, and Groq models.
- **Interactive Retrieval:** Test queries with any persona and inspect chunk ACL badges (`ALLOWED`/`RESTRICTED`).
- **End-to-End Query:** Submit queries with live LLM generation, citation extraction, and refusal detection.
- **Side-by-Side A/B Test:** Compare Intern vs HR Admin responses on restricted questions.
- **Automated Tests & Evals:** 1-click execution of `pytest` unit tests and retrieval evals (Recall@6 table).
- **Audit Log Explorer:** Live viewer with filtering by refusal status.

---

### Option B: Quick CLI Test
```powershell
# Intern asks a restricted question (should get NO exec-compensation chunks)
python -W ignore -m app.cli ask "What is the CFO's base salary?" --user acme_intern@acme.test

# HR admin asks the same question (should see 'Executive Compensation 2026' chunks)
python -W ignore -m app.cli ask "What is the CFO's base salary?" --user acme_hr_admin@acme.test
```

### Full API Test

**Terminal 1 - Start server** (activate the venv first):
```powershell
uvicorn app.main:app --port 8001
```

**Terminal 2 - Login + query** (activate the venv first). This logs in, grabs a
fresh token automatically, and asks the question as each user:
```powershell
$base = 'http://localhost:8001'
foreach ($u in 'acme_intern@acme.test', 'acme_hr_admin@acme.test') {
    $login = @{ email = $u; password = 'demo1234' } | ConvertTo-Json
    $token = (Invoke-RestMethod -Method Post "$base/auth/login" -ContentType 'application/json' -Body $login).access_token

    $body = @{ question = 'What is the CFO base salary?' } | ConvertTo-Json
    $r = Invoke-RestMethod -Method Post "$base/query" -ContentType 'application/json' `
         -Headers @{ Authorization = "Bearer $token" } -Body $body

    Write-Output "===== $u ====="
    $r | ConvertTo-Json -Depth 6
}
```

Expected:
- **Intern** -> `"refused": true`, answer is exactly
  `I couldn't find that in the documents available to you.`, empty `sources`.
- **HR admin** -> `"refused": false`, answer containing `$412,000 [S1]`, populated `sources`.

> Odd characters like `CFO�??s` in the console are just PowerShell rendering
> curly quotes / special spaces. The API response itself is correct.

### Check the Audit Log
```powershell
python -c "import sqlite3; c=sqlite3.connect('data/permrag.db'); print('audit rows:', c.execute('select count(*) from audit_log').fetchone()[0]); [print(r) for r in c.execute('select request_id, role_level, refused, latency_ms, model from audit_log order by ts desc limit 2')]"
```
Each `/query` call adds one row.

## Run Tests
```powershell
# ACL unit tests (truth table + property test)
pytest tests/unit -q -p no:warnings

# Retrieval evaluation (expect Recall@6 = 1.000)
python -W ignore -m evals.run --retrieval-only --dataset sample

# Idempotent re-ingestion (expect: Added 0, Updated 0, Skipped 10)
python -W ignore -m app.cli ingest --sample
```

## Demo for Reviewers

Follow the detailed script in `DEMO_SCRIPT.md`

## Troubleshooting

### Issue: "No chunks ingested"
```powershell
python -m app.cli ingest --sample
```

### Issue: "No users found"
```powershell
alembic upgrade head
python -m app.cli seed-users
```

### Issue: "Qdrant connection refused"
```powershell
docker compose up -d qdrant
Start-Sleep 5
docker ps | Select-String qdrant
```

### Issue: API returns 401
- JWT tokens expire after 60 minutes - just re-run the login + query block above.

### Issue: HR admin gets a refusal / LLM call fails
- Check the server terminal for `LLM generation failed` - it shows the real error.
- `model_not_found` (404): the model was retired - pick a new one with the
  model-list command in Setup step 2 and update `GROQ_MODEL` in `.env`.
- `401`/auth errors: verify `GROQ_API_KEY` in `.env`.
- Check Groq API status at https://console.groq.com

### Warning: "Qdrant client version ... incompatible with server version"
Harmless for Phase 1. The `-W ignore` flag hides it.

## What's Working

✅ **Core Feature**: Permission-aware retrieval with ACL filtering inside vector search  
✅ **Multi-tenant**: 3 tenants with complete isolation  
✅ **Role-based access**: 4 role levels (intern to hr_admin)  
✅ **Authentication**: JWT with bcrypt password hashing  
✅ **Audit logging**: Every query tracked  
✅ **Citation validation**: Invalid sources stripped  
✅ **API**: Login and query endpoints functional  
✅ **Idempotent ingestion**: Unchanged docs skipped; changed docs (incl. ACL changes) replaced  
✅ **Tests**: ACL unit tests with property-based verification  
✅ **Evals**: Retrieval metrics with per-query table (Recall@6 = 1.0 on sample)  

## Known Limitations (Phase 2 fixes)

- Docs removed from the manifest are not yet deleted from Qdrant
- Only dense search (no sparse/BM25 yet)
- No reranker (stub in place)
- No semantic cache
- No streaming
- Small eval corpus (10 docs; full 180-doc corpus in Phase 2)

## Phase 1 Complete!

**The walking skeleton is functional.** All core components work end-to-end:
- Documents ingested with ACLs
- Users authenticated with JWT
- Queries filtered by permissions at retrieval time
- LLM generates answers with citations
- Audit trail maintained

Phase 2 will add: sparse search, reranking, caching, baselines (S0-S4), attack suite, security metrics, and UI.

---

**Need help?** Check `DEMO_SCRIPT.md` for detailed walkthrough or `plan.md` for complete architecture.
