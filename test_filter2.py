from app.rag.store import get_qdrant_client, get_collection_name
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

client = get_qdrant_client()
name = get_collection_name("chunks")

flt = Filter(must=[
    FieldCondition(key="tenant_id", match=MatchValue(value="acme")),
    FieldCondition(key="min_role_level", range=Range(lte=4)),
])

# Try both filtered and unfiltered search
pts, _ = client.scroll(collection_name=name, scroll_filter=flt, limit=50, with_payload=True)
print(f"Filtered scroll: {len(pts)} chunks")
for p in pts[:5]:
    print("  ", p.payload.get("min_role_level"), p.payload.get("department"), p.payload.get("text","")[:50].replace("\n"," "))
