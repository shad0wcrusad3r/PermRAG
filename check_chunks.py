from app.rag.store import get_qdrant_client, get_collection_name

client = get_qdrant_client()
name = get_collection_name("chunks")
print("Chunks:", client.count(collection_name=name).count)
