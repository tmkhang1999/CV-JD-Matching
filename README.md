# CV-JD Matching System

An intelligent AI-powered system for matching CVs/Resumes to Job Descriptions using advanced natural language processing and semantic similarity. The system automatically extracts structured information from documents and provides accurate matching with customizable weights and filtering options.

## Features

- **Document Processing**: Upload and extract text from PDF/DOCX files
- **AI-Powered Extraction**: Structured information extraction using GPT-4o-mini
- **Semantic Embeddings**: Multi-dimensional vector embeddings with OpenAI text-embedding-3-small
- **Smart Matching**: Weighted similarity scoring with customizable parameters
- **Advanced Filtering**: Filter by experience, skills, location, and more
- **LLM Reranking**: Optional AI-powered result refinement with explanations
- **REST API**: Complete RESTful API with comprehensive endpoints
- **Web Interface**: Static React single-file UI
- **Production Ready**: Docker support with PostgreSQL + pgvector backend

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key

### 1. Environment Setup
```bash
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY="your-openai-api-key"
export POSTGRES_PASSWORD="your-postgres-password"
export POSTGRES_USER="postgres"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="cv_jd_matcher"
```

### 2. Database Setup
```bash
# Start PostgreSQL with Docker
docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your-password \
  -e POSTGRES_DB=cv_jd_matcher \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Initialize database tables
python scripts/create_tables.py
```

### 3. Start API Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 4. Launch Frontend
```bash
cd frontend
python -m http.server 4173
# open http://localhost:4173
```

### 5. Docker Deployment
```bash
docker-compose up --build
```

## Working Flow

1. **Upload Documents**: Users upload CVs and JDs via the web interface or API.
2. **Extraction**: The system extracts structured data using GPT models.
3. **Normalization**: Data is cleaned and standardized.
4. **Embedding Generation**: Semantic embeddings are created for matching.
5. **Matching**: CVs and JDs are matched based on configurable scoring rubrics.
6. **Reranking**: Results can be refined using LLM-based reranking.

## API Overview

### Document Management
- `POST /api/v1/cv/` - Upload CV
- `GET /api/v1/cv/` - List all CVs
- `GET /api/v1/cv/{id}` - Get CV details
- `GET /api/v1/cv/{id}/file` - Download original CV file
- `POST /api/v1/jd/` - Upload JD
- `GET /api/v1/jd/` - List all JDs
- `GET /api/v1/jd/{id}` - Get JD details
- `GET /api/v1/jd/{id}/file` - Download original JD file

### Matching & Search
- `POST /api/v1/match/cv/{id}/jds` - Find JDs for CV
- `POST /api/v1/match/jd/{id}/cvs` - Find CVs for JD
- `POST /api/v1/match/cv/{id}/jds/rerank` - LLM reranking of JD matches
- `POST /api/v1/match/jd/{id}/cvs/rerank` - LLM reranking of CV matches

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Pydantic
- **AI Models**: OpenAI GPT-4o-mini, text-embedding-3-small
- **Frontend**: React (static single-file)
- **Deployment**: Docker, Docker Compose

## Project Layout

- `backend/`: FastAPI service
- `frontend/`: Static React UI
- `docker-compose.yml`: Runs the entire stack

## Additional Notes

This system is designed for scalability and ease of use, with a focus on accurate and explainable AI-driven matching.
