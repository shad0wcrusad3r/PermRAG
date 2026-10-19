# PermRAG: Permission-Aware Multi-Tenant RAG System

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Vector%20DB-Qdrant-red.svg?logo=qdrant)](https://qdrant.tech/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**PermRAG** is a production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform with strict, cryptographic, permission-aware access control. It guarantees zero data leakage across tenant boundaries and role hierarchies by pushing access-control lists (ACLs) directly into vector search and retrieval filters.

---

## Key Features

- **Multi-Tenant Isolation**: Hard boundaries between tenants (e.g., Acme, Globex, Initech) with metadata-enforced filters.
- **Hierarchical Access Control (ACL)**: 5-level role-based hierarchy (`intern` < `employee` < `manager` < `hr_admin` < `exec`) and departmental boundaries (`engineering`, `hr`, `finance`, `all`).
- **Pre-Retrieval ACL Pushdown**: Vector search queries are mathematically constrained at the database index level — unauthorized chunks are never fetched or surfaced to the reranker/LLM.
- **Auditable & Provable Refusals**: If query results are withheld due to permissions, the system returns a standardized refusal message (`"I couldn't find that in the documents available to you."`) without leaking document metadata.
- **Multi-Provider LLM Integration**: Out-of-the-box support for Groq (fast free inference), GLM/Zhipu AI, OpenRouter, and local Ollama / custom endpoints.
- **Interactive Inspection Dashboard**: Full Streamlit-based UI featuring live retrieval visualization, side-by-side persona testing, audit logs, and 1-click test runners.

---

## Architecture Overview

```
                      +-----------------------------+
                      |       User / Client         |
                      +--------------+--------------+
                                     | JWT Token (tenant_id, role, dept)
                                     v
                      +-----------------------------+
                      |   FastAPI / Streamlit UI    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |      ACL Pre-Filter         |
                      | (tenant match & role check) |
                      +--------------+--------------+
                                     |
                                     v
                 +-------------------+-------------------+
                 |                                       |
                 v                                       v
    +------------------------+              +------------------------+
    |   Qdrant Vector DB     |              |     SQLite Database    |
    | (Dense Embeddings +    |              | (Users, Tenants, Roles,|
    |  Pre-filtered Payloads)|              |  Tamper-Evident Audit) |
    +------------+-----------+              +------------------------+
                 |
                 v Top-K Authorized Chunks
    +------------------------+
    | Cross-Encoder Reranker |
    +------------+-----------+
                 |
                 v Top Context Chunks
    +------------------------+
    | LLM Generation Engine  | ---> Strict Grounded Answer + Citations [S1]
    | (Groq / GLM / Ollama)  |      or Standardized Zero-Leakage Refusal
    +------------------------+
```

---

## Prerequisites

Before setting up PermRAG, ensure you have:

1. **Python 3.11+** installed ([Download Python](https://www.python.org/downloads/)).
2. **Docker Desktop** installed and running ([Download Docker](https://www.docker.com/products/docker-desktop/)).
3. **An LLM API Key**:
   - **Groq** *(Recommended & default, free tier)*: [console.groq.com](https://console.groq.com)
   - Alternatively: Zhipu AI / GLM ([open.bigmodel.cn](https://open.bigmodel.cn)) or OpenRouter ([openrouter.ai](https://openrouter.ai)).

---

## Step-by-Step Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/shad0wcrusad3r/PermRAG.git
cd PermRAG
```

### 2. Set Up a Python Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
> *Tip: If PowerShell prevents script execution, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`*

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Install the project and development dependencies in editable mode:

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Configure Environment Variables

Copy the provided example environment template to create your `.env` file:

#### On Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### On macOS / Linux:
```bash
cp .env.example .env
```

Open `.env` and add your **Groq API Key**:
```env
# LLM Provider Configuration
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
```

*(Optional: Set `JWT_SECRET` to any custom 32+ character random string)*.

### 5. Launch the Vector Database (Qdrant)

PermRAG uses Qdrant running in Docker. Start the preconfigured service:

```bash
docker compose up -d qdrant
```

Verify that the Qdrant container is up:
```bash
docker ps
```
Qdrant will be accessible at `http://localhost:16333` (REST) and mapped to internal port `6333`.

### 6. Initialize SQLite Database & Migrations

Run database migrations using Alembic to create the schema (tenants, users, audit logs):

```bash
alembic upgrade head
```

### 7. Seed Test Personas & Users

Populate the database with 15 test personas across three organizations (Acme, Globex, Initech):

```bash
python -m app.cli seed-users
```

### 8. Ingest Multi-Tenant Sample Documents

Ingest the sample corpus into Qdrant with tenant, role, and department metadata:

```bash
python -m app.cli ingest --sample
```

*(Expected output: Ingests 10 documents, generating ~52 vector chunks).*

---

## Running the Application

### Option A: Interactive Web UI (Recommended)

Launch the Streamlit interactive dashboard:

```bash
streamlit run ui/streamlit_app.py --server.port 8080
```

Open **`http://localhost:8080`** in your browser. The dashboard provides:
- **System Health Diagnostics**: Live status indicators for Docker/Qdrant, SQLite, Seed Users, and LLM connectivity.
- **Interactive Query Engine**: Submit queries as different personas and observe live answers with citations.
- **Side-by-Side Persona Comparison**: Compare an Intern vs. an HR Admin querying restricted salary documents in real-time.
- **ACL Badge Inspector**: Inspect retrieved chunks with visible `ALLOWED` or `RESTRICTED` security badges.
- **Audit Log Explorer**: Live view of tamper-evident query access records.

---

### Option B: FastAPI Backend Server

Start the REST API backend:

```bash
uvicorn app.main:app --port 8001 --reload
```

- API Documentation: **`http://localhost:8001/docs`**
- Interactive Swagger UI: Test endpoints like `/auth/login` and `/query`.

---

### Option C: Quick CLI Queries

Run queries directly from the command line:

```bash
# Query as an Intern (Unauthorized for executive salary data)
python -m app.cli ask "What is the CFO's base salary?" --user acme_intern@acme.test

# Query as HR Admin (Authorized to view executive compensation)
python -m app.cli ask "What is the CFO's base salary?" --user acme_hr_admin@acme.test
```

---

## Test Personas & Credentials

All test users are seeded with the default password: **`demo1234`**

| Tenant | Email | Role Level | Department | Permission Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Acme Corp** | `acme_intern@acme.test` | `intern` (1) | Engineering | General onboarding docs only |
| **Acme Corp** | `acme_employee@acme.test` | `employee` (2) | Engineering | General & engineering guidelines |
| **Acme Corp** | `acme_manager@acme.test` | `manager` (3) | Engineering | Engineering team docs & policies |
| **Acme Corp** | `acme_hr_admin@acme.test` | `hr_admin` (4) | HR | HR policies, parental leave, exec compensation |
| **Acme Corp** | `acme_exec@acme.test` | `exec` (5) | Executive | Full tenant access across all departments |
| **Globex Corp** | `globex_employee@globex.test`| `employee` (2) | General | Globex company documents (Strict Acme isolation) |
| **Initech** | `initech_employee@initech.test`| `employee` (2) | General | Initech documents (Strict Acme isolation) |

---

## Running Automated Tests & Evals

### Run Unit Tests
Test ACL truth tables, role inheritance, and parser validations:
```bash
pytest tests/unit -q -p no:warnings
```

### Run Retrieval Evaluations
Measure Recall@K on multi-tenant access boundaries:
```bash
python -m evals.run --retrieval-only --dataset sample
```
*(Benchmark expectation: `Recall@6 = 1.000` for authorized documents with 0 cross-tenant leakages).*

---

## Project Structure

```text
PermRAG/
├── app/
│   ├── api/             # FastAPI routes (auth, query endpoints)
│   ├── db/              # SQLAlchemy models, sessions, audit logging
│   ├── ingest/          # Document chunking, cleaning, manifest loader
│   ├── prompts/         # Grounded generation prompt templates
│   ├── rag/             # Vector store client, retriever, reranker, LLM caller
│   ├── security/        # JWT auth, password hashing, ACL permission evaluator
│   ├── cli.py           # Typer CLI commands (seed, ingest, ask)
│   ├── config.py        # Settings management with pydantic-settings
│   └── main.py          # FastAPI application entrypoint
├── data/
│   └── sample/          # Sample multi-tenant markdown corpus and manifest.jsonl
├── evals/               # Retrieval & QA evaluation benchmarks
├── tests/
│   └── unit/            # Pytest test suites (ACL logic, schema validation)
├── ui/
│   ├── quickstart_services.py  # Health check and background service helpers
│   └── streamlit_app.py        # Streamlit interactive evaluation dashboard
├── docker-compose.yml   # Qdrant service configuration
├── pyproject.toml       # Package dependencies and project metadata
├── .env.example         # Environment template (safe for git)
├── .gitignore           # Ignores .env, caches, local database files
└── README.md            # Project documentation and setup guide
```

---

## Troubleshooting

- **Qdrant Connection Error (`ConnectionRefusedError`)**:
  Ensure Docker Desktop is running and execute:
  ```bash
  docker compose up -d qdrant
  ```
- **Windows PowerShell Script Execution Policy**:
  If PowerShell blocks activating the virtual environment, run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```
- **Untrusted SSL / Proxy Certificate Errors on Windows**:
  In `.env`, keep `SSL_VERIFY=false` if corporate proxies or local firewalls intercept HTTPS requests to LLM APIs.

---

## License

This project is licensed under the [MIT License](LICENSE).
