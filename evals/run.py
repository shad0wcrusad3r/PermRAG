"""Evaluation runner."""
import json
import typer
from pathlib import Path
from typing import List, Dict, Any

from app.db.session import get_session_factory
from app.db.models import User as UserModel
from app.security.acl import User
from app.rag.retriever import retrieve
from evals.metrics.retrieval import recall_at_k, hit_rate_at_k, mrr_at_k

app = typer.Typer()


@app.command()
def run(
    retrieval_only: bool = False,
    dataset: str = "sample",
):
    """Run evaluation."""
    if dataset == "sample":
        dataset_path = Path("evals/datasets/qa_sample.jsonl")
    else:
        dataset_path = Path(f"evals/datasets/{dataset}.jsonl")

    if not dataset_path.exists():
        typer.echo(f"Error: Dataset not found at {dataset_path}")
        raise typer.Exit(1)

    # Load dataset
    queries = []
    with open(dataset_path, "r") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    typer.echo(f"Loaded {len(queries)} queries from {dataset_path}")

    if retrieval_only:
        typer.echo("\nRunning retrieval evaluation...\n")
        run_retrieval_eval(queries)
    else:
        typer.echo("Full evaluation not yet implemented (requires LLM)")


def compute_retrieval_results(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute per-query retrieval metrics (shared by the CLI and the Streamlit UI)."""
    SessionLocal = get_session_factory()
    db = SessionLocal()

    results = []

    try:
        for q in queries:
            # Get user
            db_user = db.query(UserModel).filter_by(email=q["persona"]).first()
            if not db_user:
                typer.echo(f"Warning: User {q['persona']} not found, skipping")
                continue

            user_obj = User(
                user_id=db_user.id,
                tenant_id=db_user.tenant_id,
                department=db_user.department,
                role_level=db_user.role_level,
            )

            # Retrieve
            chunks = retrieve(user_obj, q["question"], top_k=20)
            # Dedupe doc IDs while preserving rank order (set() would scramble it)
            retrieved_doc_ids = list(dict.fromkeys(c["doc_id"] for c in chunks))

            # Compute metrics
            recall_6 = recall_at_k(retrieved_doc_ids, q["gold_doc_ids"], k=6)
            hit_6 = hit_rate_at_k(retrieved_doc_ids, q["gold_doc_ids"], k=6)
            mrr_6 = mrr_at_k(retrieved_doc_ids, q["gold_doc_ids"], k=6)
            recall_20 = recall_at_k(retrieved_doc_ids, q["gold_doc_ids"], k=20)

            results.append({
                "id": q["id"],
                "persona": q["persona"],
                "question": q["question"],
                "recall@6": recall_6,
                "hit@6": hit_6,
                "mrr@6": mrr_6,
                "recall@20": recall_20,
            })

    finally:
        db.close()

    return results


def run_retrieval_eval(queries: List[Dict[str, Any]]):
    """Run retrieval-only evaluation and print a table."""
    results = compute_retrieval_results(queries)

    # Aggregate
    if results:
        avg_recall_6 = sum(r["recall@6"] for r in results) / len(results)
        avg_hit_6 = sum(r["hit@6"] for r in results) / len(results)
        avg_mrr_6 = sum(r["mrr@6"] for r in results) / len(results)
        avg_recall_20 = sum(r["recall@20"] for r in results) / len(results)

        typer.echo(f"{'id':<10} {'persona':<36} {'R@6':>5} {'Hit@6':>6} {'MRR@6':>6} {'R@20':>5}")
        typer.echo("-" * 72)
        for r in results:
            typer.echo(
                f"{r['id']:<10} {r['persona']:<36} {r['recall@6']:>5.2f} "
                f"{r['hit@6']:>6.2f} {r['mrr@6']:>6.2f} {r['recall@20']:>5.2f}"
            )
        typer.echo("")

        typer.echo("=" * 60)
        typer.echo("RETRIEVAL METRICS")
        typer.echo("=" * 60)
        typer.echo(f"Recall@6:     {avg_recall_6:.3f}")
        typer.echo(f"Hit Rate@6:   {avg_hit_6:.3f}")
        typer.echo(f"MRR@6:        {avg_mrr_6:.3f}")
        typer.echo(f"Recall@20:    {avg_recall_20:.3f}")
        typer.echo("=" * 60)
    else:
        typer.echo("No results")


if __name__ == "__main__":
    app()
