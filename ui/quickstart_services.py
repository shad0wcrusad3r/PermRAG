"""Backend helpers for the PermRAG QuickStart dashboard.

Pure Python (no Streamlit imports) so every QuickStart step can be executed
and inspected programmatically. Each function mirrors one terminal command
from QUICKSTART.md and returns structured data instead of printing.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import warnings
import xml.etree.ElementTree as ET
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

# Run from the project root so `.env`, relative SQLite paths and `app.*` imports
# behave exactly like the terminal workflow in QUICKSTART.md.
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore", message=".*Qdrant client version.*")

import requests  # noqa: E402

from app.config import settings  # noqa: E402

API_BASE = "http://localhost:8001"
DEFAULT_PASSWORD = "demo1234"
EXPECTED_USERS = 15
SERVER_LOG = ROOT / "data" / "api_server.log"


# --------------------------------------------------------------------------- #
# Step 1 - Environment
# --------------------------------------------------------------------------- #
def env_summary() -> dict[str, Any]:
    """Return the effective configuration (API key masked)."""
    return {
        "env_file": (ROOT / ".env").exists(),
        "venv_python": sys.executable,
        "in_project_venv": str(ROOT / ".venv").lower() in sys.executable.lower(),
        "groq_key_set": bool(settings.effective_api_key),
        "groq_model": settings.effective_model,
        "llm_provider": settings.llm_provider,
        "embed_model": settings.embed_model,
        "qdrant_url": settings.qdrant_url,
        "sqlite_url": settings.sqlite_url,
        "env": settings.env,
        "dense_top_k": settings.dense_top_k,
        "rerank_top_k": settings.rerank_top_k,
        "max_context_tokens": settings.max_context_tokens,
        "jwt_expire_minutes": settings.jwt_expire_minutes,
    }


def list_groq_models() -> list[str]:
    """List model IDs the configured LLM key can access."""
    from app.rag.generate import get_llm_client

    try:
        models = [m.id for m in get_llm_client().client.models.list().data]
        return sorted(models) if models else [settings.effective_model]
    except Exception as e:
        return [settings.effective_model]


# --------------------------------------------------------------------------- #
# Step 2 - Verify setup
# --------------------------------------------------------------------------- #
def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace", creationflags=flags,
    )


def docker_qdrant_status() -> dict[str, Any]:
    """Equivalent of `docker ps | Select-String qdrant`."""
    try:
        out = _run(["docker", "ps", "-a", "--filter", "name=permrag_qdrant",
                    "--format", "{{.Names}}|{{.Status}}|{{.Image}}"], timeout=20)
    except FileNotFoundError:
        return {"ok": False, "detail": "docker CLI not found on PATH"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "detail": "docker ps timed out - is Docker Desktop running?"}
    if out.returncode != 0:
        return {"ok": False, "detail": (out.stderr or "docker ps failed").strip()}
    lines = [ln for ln in out.stdout.strip().splitlines() if ln]
    if not lines:
        return {"ok": False, "detail": "Container permrag_qdrant not found"}
    name, status, image = (lines[0].split("|") + ["", "", ""])[:3]
    return {"ok": status.startswith("Up"), "name": name, "status": status,
            "image": image, "detail": f"{name} · {status} · {image}"}


def qdrant_reachable() -> dict[str, Any]:
    """Check that the Qdrant HTTP API answers."""
    try:
        r = requests.get(settings.qdrant_url.rstrip("/") + "/", timeout=3)
        version = r.json().get("version", "?") if r.ok else None
        return {"ok": r.ok, "version": version,
                "detail": f"Qdrant v{version} at {settings.qdrant_url}" if r.ok else f"HTTP {r.status_code}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "version": None, "detail": f"{type(e).__name__}: {e}"}


def start_qdrant() -> tuple[bool, str]:
    """Equivalent of `docker compose up -d qdrant`."""
    try:
        out = _run(["docker", "compose", "up", "-d", "qdrant"], timeout=240)
    except FileNotFoundError:
        return False, "docker CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "docker compose timed out"
    return out.returncode == 0, (out.stdout + out.stderr).strip()


def db_path() -> Path:
    raw = settings.sqlite_url.replace("sqlite:///", "", 1)
    p = Path(raw)
    return p if p.is_absolute() else (ROOT / p).resolve()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def list_users() -> list[dict[str, Any]]:
    with closing(_db()) as c:
        rows = c.execute(
            "SELECT email, tenant_id, department, role_level FROM users "
            "ORDER BY tenant_id, role_level, email"
        ).fetchall()
    return [dict(r) for r in rows]


def chunk_count() -> int:
    """Equivalent of `python check_chunks.py`."""
    from app.rag.store import get_collection_name, get_qdrant_client

    return get_qdrant_client().count(collection_name=get_collection_name("chunks")).count


def document_inventory() -> list[dict[str, Any]]:
    """Aggregate Qdrant chunks into one row per document with its ACL metadata."""
    from app.rag.store import get_collection_name, get_qdrant_client

    client = get_qdrant_client()
    docs: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = defaultdict(int)
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=get_collection_name("chunks"), limit=256, offset=offset,
            with_payload=["doc_id", "tenant_id", "department", "min_role_level", "title", "kind"],
            with_vectors=False,
        )
        for p in points:
            pl = p.payload
            counts[pl["doc_id"]] += 1
            docs.setdefault(pl["doc_id"], {
                "title": pl.get("title"), "tenant_id": pl.get("tenant_id"),
                "department": pl.get("department"), "min_role_level": pl.get("min_role_level"),
                "kind": pl.get("kind", "normal"), "doc_id": pl["doc_id"],
            })
        if offset is None:
            break
    rows = [{**d, "chunks": counts[k]} for k, d in docs.items()]
    return sorted(rows, key=lambda r: (r["tenant_id"], r["min_role_level"], r["title"]))


# --------------------------------------------------------------------------- #
# Step 3 - Retrieval (CLI `ask`) test
# --------------------------------------------------------------------------- #
def acl_user(email: str):
    """Load a user from SQLite and build the ACL identity object."""
    from app.security.acl import User

    with closing(_db()) as c:
        row = c.execute(
            "SELECT id, tenant_id, department, role_level FROM users WHERE email = ?", (email,)
        ).fetchone()
    if row is None:
        raise ValueError(f"User {email} not found")
    return User(user_id=row["id"], tenant_id=row["tenant_id"],
                department=row["department"], role_level=row["role_level"])


def retrieve_for(email: str, question: str, top_k: int = 6) -> list[dict[str, Any]]:
    """Equivalent of `python -m app.cli ask "<q>" --user <email>`.

    Each chunk is annotated with an independent `is_allowed` re-check so the UI
    can prove the in-database ACL filter matches the Python reference rule.
    """
    from app.rag.retriever import retrieve
    from app.security.acl import is_allowed

    user = acl_user(email)
    chunks = retrieve(user, question, top_k=top_k)
    for ch in chunks:
        ch["acl_ok"] = is_allowed(user, ch)
    return chunks


# --------------------------------------------------------------------------- #
# Step 4 - API test
# --------------------------------------------------------------------------- #
def api_health(base: str = API_BASE, timeout: float = 1.5) -> bool:
    try:
        return requests.get(f"{base}/health", timeout=timeout).ok
    except requests.RequestException:
        return False


def api_login(email: str, password: str = DEFAULT_PASSWORD, base: str = API_BASE) -> str:
    r = requests.post(f"{base}/auth/login", json={"email": email, "password": password}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def api_query(token: str, question: str, base: str = API_BASE) -> dict[str, Any]:
    r = requests.post(
        f"{base}/query", json={"question": question},
        headers={"Authorization": f"Bearer {token}"}, timeout=180,
    )
    r.raise_for_status()
    return r.json()


def decode_token(token: str) -> dict[str, Any]:
    """Decode JWT claims for display only (no signature verification)."""
    import jwt

    claims = jwt.decode(token, options={"verify_signature": False})
    if "exp" in claims:
        claims["exp_local"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(claims["exp"]))
    return claims


def direct_answer(email: str, question: str) -> dict[str, Any]:
    """Run the full RAG pipeline in-process (no HTTP server needed)."""
    from app.rag.pipeline import answer

    return answer(acl_user(email), question)


def start_api_server(port: int = 8001) -> subprocess.Popen:
    """Equivalent of `uvicorn app.main:app --port 8001`, logging to data/api_server.log."""
    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = open(SERVER_LOG, "ab")  # noqa: SIM115 - handle owned by the child process
    flags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
    )


def server_log_tail(lines: int = 60) -> str:
    if not SERVER_LOG.exists():
        return ""
    text = SERVER_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:])


# --------------------------------------------------------------------------- #
# Step 5 - Audit log
# --------------------------------------------------------------------------- #
def audit_count() -> int:
    with closing(_db()) as c:
        return c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]


def audit_rows(limit: int = 100) -> list[dict[str, Any]]:
    with closing(_db()) as c:
        rows = c.execute(
            """
            SELECT a.ts, a.request_id, COALESCE(u.email, a.user_id) AS user, a.tenant_id,
                   a.role_level, a.question, a.refused, a.cache_hit, a.latency_ms, a.model,
                   a.retrieved_chunk_ids, a.cited_chunk_ids, a.access_mode
            FROM audit_log a LEFT JOIN users u ON u.id = a.user_id
            ORDER BY a.ts DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for key in ("retrieved_chunk_ids", "cited_chunk_ids"):
            try:
                d[key.replace("_chunk_ids", "")] = len(json.loads(d.pop(key) or "[]"))
            except (TypeError, json.JSONDecodeError):
                d[key.replace("_chunk_ids", "")] = 0
        d["refused"] = bool(d["refused"])
        d["cache_hit"] = bool(d["cache_hit"])
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# Step 6 - Tests, evals, ingestion
# --------------------------------------------------------------------------- #
def run_unit_tests() -> dict[str, Any]:
    """Equivalent of `pytest tests/unit -q`, with per-test results via JUnit XML."""
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        xml_path = Path(td) / "report.xml"
        out = _run([sys.executable, "-m", "pytest", "tests/unit", "-q", "-p", "no:warnings",
                    "-p", "no:cacheprovider", f"--junitxml={xml_path}"], timeout=900)
        cases = []
        if xml_path.exists():
            for tc in ET.parse(xml_path).iter("testcase"):
                status, msg = "passed", ""
                for tag, label in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
                    el = tc.find(tag)
                    if el is not None:
                        status, msg = label, (el.get("message") or "")[:300]
                cases.append({
                    "module": (tc.get("classname") or "").replace("tests.unit.", ""),
                    "test": tc.get("name"), "status": status,
                    "time_s": round(float(tc.get("time", 0) or 0), 3), "message": msg,
                })
    return {"returncode": out.returncode, "cases": cases,
            "output": (out.stdout[-5000:] + "\n" + out.stderr[-2000:]).strip(),
            "duration_s": round(time.time() - t0, 1)}


def run_retrieval_eval(dataset: str = "sample") -> dict[str, Any]:
    """Equivalent of `python -m evals.run --retrieval-only --dataset sample`."""
    from evals.run import compute_retrieval_results

    path = ROOT / "evals" / "datasets" / ("qa_sample.jsonl" if dataset == "sample" else f"{dataset}.jsonl")
    queries = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = compute_retrieval_results(queries)
    n = len(rows) or 1
    summary = {m: sum(r[m] for r in rows) / n for m in ("recall@6", "hit@6", "mrr@6", "recall@20")}
    return {"rows": rows, "summary": summary, "n_queries": len(queries), "dataset": str(path.relative_to(ROOT))}


def run_ingest_sample() -> dict[str, int]:
    """Equivalent of `python -m app.cli ingest --sample`."""
    from app.ingest.pipeline import ingest_documents

    return ingest_documents(ROOT / "data" / "sample" / "manifest.jsonl", ROOT / "data" / "sample")


def migrate_and_seed() -> tuple[bool, str]:
    """Equivalent of `alembic upgrade head` followed by `python -m app.cli seed-users`."""
    logs = []
    for cmd in ([sys.executable, "-m", "alembic", "upgrade", "head"],
                [sys.executable, "-m", "app.cli", "seed-users"]):
        out = _run(cmd, timeout=180)
        logs.append(f"$ {' '.join(cmd[1:])}\n{(out.stdout + out.stderr).strip()}")
        if out.returncode != 0:
            return False, "\n\n".join(logs)
    return True, "\n\n".join(logs)
