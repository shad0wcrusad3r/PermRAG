"""Database models."""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    department = Column(String, nullable=False)
    role_level = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("role_level >= 1 AND role_level <= 4", name="check_role_level"),
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)  # doc_id
    tenant_id = Column(String, nullable=False)
    department = Column(String, nullable=False)
    min_role_level = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    format = Column(String, nullable=False)
    kind = Column(String, nullable=False, default="normal")
    content_hash = Column(String, nullable=False)
    n_chunks = Column(Integer, nullable=False)
    ingested_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)  # chunk_id
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    heading_path = Column(String)
    page = Column(Integer)
    n_tokens = Column(Integer, nullable=False)
    content_hash = Column(String, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, nullable=False, unique=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False)
    role_level = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    access_mode = Column(String, nullable=False)
    cache_mode = Column(String, nullable=False)
    cache_hit = Column(Integer, nullable=False)  # 0 or 1 (SQLite boolean)
    retrieved_chunk_ids = Column(Text, nullable=False)  # JSON array
    cited_chunk_ids = Column(Text, nullable=False)  # JSON array
    refused = Column(Integer, nullable=False)  # 0 or 1
    answer_hash = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    model = Column(String)
