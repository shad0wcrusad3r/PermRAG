#!/bin/bash
# Phase 1 Demo Setup Script

echo "=========================================="
echo "PermRAG Phase 1 Demo Setup"
echo "=========================================="
echo ""

# Check services
echo "1. Checking Docker/Qdrant..."
docker ps | grep qdrant || echo "⚠ Qdrant not running. Run: docker compose up -d qdrant"

echo ""
echo "2. Checking database..."
ls data/permrag.db > /dev/null 2>&1 && echo "✓ Database exists" || echo "⚠ Run: alembic upgrade head"

echo ""
echo "3. Checking ingested documents..."
source .venv/Scripts/activate
python -c "from app.rag.store import get_qdrant_client, get_collection_name; c=get_qdrant_client(); count=c.count(collection_name=get_collection_name('chunks')).count; print(f'✓ {count} chunks ingested' if count > 0 else '⚠ No chunks. Run: python -m app.cli ingest --sample')"

echo ""
echo "4. Checking users..."
python -c "from app.db.session import get_session_factory; from app.db.models import User; db=get_session_factory()(); count=db.query(User).count(); print(f'✓ {count} users seeded'); db.close()"

echo ""
echo "✓ Setup complete! Ready for demo."
