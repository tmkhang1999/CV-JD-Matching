# app/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Document(Base):
    """
    Represents both CVs and JDs.

    type: "cv" or "jd"
    structured: normalized JSON (GPT extraction output mapped to our schema)
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, index=True)  # "cv" or "jd"

    title = Column(String, nullable=True)       # CV: headline_title, JD: job_title
    owner_name = Column(String, nullable=True)  # CV: candidate name, JD: company

    raw_text = Column(String, nullable=True)
    structured = Column(JSONB, nullable=True)
    file_path = Column(String, nullable=True)  # Path to original uploaded file

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")


class DocumentEmbedding(Base):
    """
    Stores different embedding vectors for each document.

    kind examples:
      - "global"
      - "skills_tech"
      - "skills_language"
    """
    __tablename__ = "document_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String, index=True)
    vector = Column(Vector(1536))  # pgvector vector type with 1536 dimensions (text-embedding-3-small)

    document = relationship("Document", back_populates="embeddings")
