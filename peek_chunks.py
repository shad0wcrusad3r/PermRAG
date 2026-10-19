from app.rag.store import get_qdrant_client, get_collection_name

client = get_qdrant_client()
name = get_collection_name("chunks")
points, _ = client.scroll(collection_name=name, limit=60, with_payload=True, with_vectors=False)

print(f"Total returned: {len(points)}\n")
for p in points:
    pl = p.payload or {}
    text = (pl.get("text") or pl.get("content") or "")[:100].replace("\n", " ")
    print("=" * 70)
    print("id       :", p.id)
    print("keys     :", list(pl.keys()))
    print("doc_id   :", pl.get("document_id") or pl.get("doc_id"))
    print("tenant   :", pl.get("tenant_id") or pl.get("tenant"))
    print("dept     :", pl.get("department") or pl.get("dept"))
    print("roles    :", pl.get("allowed_roles") or pl.get("roles") or pl.get("role_levels"))
    print("min_role :", pl.get("min_role_level") or pl.get("role_level"))
    print("text     :", text)
