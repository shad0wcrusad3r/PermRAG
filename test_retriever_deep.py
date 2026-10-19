import inspect
import app.rag.retriever as R
from app.rag.store import get_qdrant_client, get_collection_name
from app.security.acl import build_acl_filter
import app.security.acl as A

# 1. Show retriever signatures
print("=== retriever.py ===")
for n, o in inspect.getmembers(R, inspect.isfunction):
    print(f"  {n}{inspect.signature(o)}")

# 2. Show ACL signatures
print("\n=== acl.py ===")
for n, o in inspect.getmembers(A, inspect.isfunction):
    print(f"  {n}{inspect.signature(o)}")
for n, o in inspect.getmembers(A, inspect.isclass):
    if not n.startswith("_"):
        print(f"  class {n}: {inspect.signature(o)}")

# 3. Build ACL filter and dump it
class FakeUser:
    user_id = "ff77d6d8-2754-442e-a286-260cd4290527"
    tenant_id = "acme"
    department = "hr"
    role_level = 4

u = FakeUser()
flt = build_acl_filter(u)
print("\n=== ACL filter object ===")
print(flt)
print("\nrepr:", repr(flt))

# 4. Scroll with that exact filter
client = get_qdrant_client()
name = get_collection_name("chunks")
pts, _ = client.scroll(collection_name=name, scroll_filter=flt, limit=50, with_payload=True)
print(f"\nScroll with ACL filter: {len(pts)} chunks")

# 5. Now run each chunk through the post-filter (if it exists)
post_filter_fn = None
for cand in ["is_chunk_allowed", "chunk_allowed", "user_can_access", "check_chunk_access", "allowed"]:
    if hasattr(A, cand):
        post_filter_fn = getattr(A, cand)
        print(f"\nFound post-filter: {cand}")
        break

if post_filter_fn:
    kept = []
    for p in pts:
        chunk = p.payload
        try:
            ok = post_filter_fn(chunk, u)
        except TypeError:
            ok = post_filter_fn(u, chunk)   # try reversed order
        if ok:
            kept.append(p)
    print(f"After post-filter: {len(kept)} chunks (dropped {len(pts) - len(kept)})")
    for p in kept[:3]:
        print("  KEPT:", p.payload.get("text","")[:60].replace("\n"," "))
