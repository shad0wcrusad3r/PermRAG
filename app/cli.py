"""CLI commands for PermRAG."""
import typer
from pathlib import Path

from app.rag.store import ensure_collections
from app.ingest.pipeline import ingest_documents

app = typer.Typer()


@app.command()
def ingest(sample: bool = False):
    """Ingest documents from manifest."""
    if sample:
        manifest_path = Path("data/sample/manifest.jsonl")
        corpus_path = Path("data/sample")
    else:
        manifest_path = Path("data/corpus/manifest.jsonl")
        corpus_path = Path("data/corpus")

    if not manifest_path.exists():
        typer.echo(f"Error: Manifest not found at {manifest_path}")
        raise typer.Exit(1)

    typer.echo("Ensuring collections exist...")
    ensure_collections()

    typer.echo(f"Ingesting documents from {manifest_path}...")
    stats = ingest_documents(manifest_path, corpus_path)

    typer.echo(f"Ingestion complete:")
    typer.echo(f"  Added: {stats['added']}")
    typer.echo(f"  Updated: {stats['updated']}")
    typer.echo(f"  Deleted: {stats['deleted']}")
    typer.echo(f"  Skipped: {stats['skipped']}")


@app.command()
def seed_users():
    """Create seed users for testing."""
    from app.db.session import get_session_factory
    from app.db.models import Tenant, User
    from app.security.auth import hash_password
    import uuid

    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        # Create tenants
        tenants = [
            Tenant(id="acme", name="Acme Corp"),
            Tenant(id="globex", name="Globex Corporation"),
            Tenant(id="initech", name="Initech"),
        ]

        for tenant in tenants:
            existing = db.query(Tenant).filter_by(id=tenant.id).first()
            if not existing:
                db.add(tenant)

        db.commit()

        # Create users (5 per tenant)
        users_data = []
        for tenant_id in ["acme", "globex", "initech"]:
            users_data.extend([
                {
                    "email": f"{tenant_id}_intern@{tenant_id}.test",
                    "tenant_id": tenant_id,
                    "department": "engineering",
                    "role_level": 1,
                },
                {
                    "email": f"{tenant_id}_eng_employee@{tenant_id}.test",
                    "tenant_id": tenant_id,
                    "department": "engineering",
                    "role_level": 2,
                },
                {
                    "email": f"{tenant_id}_eng_manager@{tenant_id}.test",
                    "tenant_id": tenant_id,
                    "department": "engineering",
                    "role_level": 3,
                },
                {
                    "email": f"{tenant_id}_fin_employee@{tenant_id}.test",
                    "tenant_id": tenant_id,
                    "department": "finance",
                    "role_level": 2,
                },
                {
                    "email": f"{tenant_id}_hr_admin@{tenant_id}.test",
                    "tenant_id": tenant_id,
                    "department": "hr",
                    "role_level": 4,
                },
            ])

        password_hash = hash_password("demo1234")

        for user_data in users_data:
            existing = db.query(User).filter_by(email=user_data["email"]).first()
            if not existing:
                user = User(
                    id=str(uuid.uuid4()),
                    email=user_data["email"],
                    password_hash=password_hash,
                    tenant_id=user_data["tenant_id"],
                    department=user_data["department"],
                    role_level=user_data["role_level"],
                )
                db.add(user)

        db.commit()
        typer.echo(f"Created {len(users_data)} users across 3 tenants")
        typer.echo("All users have password: demo1234")

    finally:
        db.close()


@app.command()
def ask(question: str, user: str = "acme_intern@acme.test"):
    """Ask a question (testing retrieval only, no LLM)."""
    from app.db.session import get_session_factory
    from app.db.models import User as UserModel
    from app.security.acl import User
    from app.rag.retriever import retrieve

    typer.echo(f"User: {user}")
    typer.echo(f"Question: {question}\n")

    # Get user from DB
    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        db_user = db.query(UserModel).filter_by(email=user).first()
        if not db_user:
            typer.echo(f"Error: User {user} not found")
            raise typer.Exit(1)

        # Create User object
        user_obj = User(
            user_id=db_user.id,
            tenant_id=db_user.tenant_id,
            department=db_user.department,
            role_level=db_user.role_level,
        )

        # Retrieve chunks
        chunks = retrieve(user_obj, question, top_k=6)

        typer.echo(f"Retrieved {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks):
            typer.echo(f"[{i+1}] {chunk['title']} - {chunk['heading_path']}")
            typer.echo(f"    Role level: {chunk['min_role_level']}, Dept: {chunk['department']}")
            typer.echo(f"    Score: {chunk['score']:.3f}")
            typer.echo(f"    Text: {chunk['text'][:200]}...\n")

    finally:
        db.close()


if __name__ == "__main__":
    app()
