-- Initialize database for CV-JD Matching System
-- This script runs automatically when the PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    type VARCHAR(10) NOT NULL CHECK (type IN ('cv', 'jd')),
    title VARCHAR(500),
    owner_name VARCHAR(255),
    raw_text TEXT,
    structured JSONB,
    file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for documents table
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_structured ON documents USING GIN(structured);

-- Create document_embeddings table
-- text-embedding-3-small produces 1536-dimensional vectors
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL CHECK (kind IN ('global', 'skills_tech', 'skills_language')),
    vector vector(1536),
    UNIQUE(document_id, kind)
);

-- Create indexes for document_embeddings
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON document_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_kind ON document_embeddings(kind);

-- Create vector similarity index using HNSW (Hierarchical Navigable Small World)
-- This dramatically speeds up similarity searches
-- HNSW supports up to 2000 dimensions, so it works perfectly with text-embedding-3-small (1536 dimensions)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw ON document_embeddings
USING hnsw (vector vector_cosine_ops);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cvjd_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cvjd_user;

-- Insert a test record to verify everything works (optional)
-- INSERT INTO documents (type, title, owner_name, raw_text, structured)
-- VALUES ('cv', 'Test CV', 'Test User', 'Sample text', '{"type": "cv"}'::jsonb);
