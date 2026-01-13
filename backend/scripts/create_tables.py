"""
Database initialization script.
Run this to create tables if not using Docker.
"""
from app.db.models import Base
from app.db.session import engine
from sqlalchemy import text


def init_db():
    """Initialize database tables and extensions."""
    print("Initializing database...")

    # Create pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("✓ pgvector extension enabled")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")

    # Create vector index
    with engine.connect() as conn:
        # Check if index exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_embeddings_vector_hnsw'
            )
        """))
        if not result.scalar():
            conn.execute(text("""
                CREATE INDEX idx_embeddings_vector_hnsw 
                ON document_embeddings 
                USING hnsw (vector vector_cosine_ops)
            """))
            conn.commit()
            print("✓ Vector similarity index created")
        else:
            print("✓ Vector index already exists")

    print("\nDatabase initialization complete!")


if __name__ == "__main__":
    init_db()


