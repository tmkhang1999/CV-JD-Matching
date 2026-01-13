from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import SessionLocal
from app.db import models
from app.services import matching, reranking
from app.schemas.match import (
    MatchRequest,
    MatchResponse,
    MatchResult,
    LLMRerankResponse
)

def get_type_specific_id(db: Session, doc_id: int, doc_type: str) -> str:
    """Get the type-specific ID (CV-1, JD-1, etc.) for a document"""
    docs = db.query(models.Document).filter(
        models.Document.type == doc_type
    ).order_by(models.Document.created_at).all()

    for index, doc in enumerate(docs, 1):
        if doc.id == doc_id:
            return f"{doc_type.upper()}-{index}"

    return f"{doc_type.upper()}-{doc_id}"  # Fallback

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/cv/{cv_id}/jds", response_model=MatchResponse)
def find_jds_for_cv(
    cv_id: int,
    request: MatchRequest = Body(default=MatchRequest()),
    db: Session = Depends(get_db)
):
    """
    Find the best matching JDs for a given CV.

    Supports optional filters and custom weights:
    - filters: min_years, required_skills, domains
    - weights: global, skills_tech, skills_language
    - top_k: number of results to return
    """
    # Check if CV exists
    cv_doc = db.query(models.Document).filter(
        models.Document.id == cv_id,
        models.Document.type == "cv",
    ).first()
    if not cv_doc:
        raise HTTPException(status_code=404, detail="CV not found")

    # Prepare filters and weights
    filters = request.filters.model_dump() if request.filters else None
    weights = request.weights.model_dump() if request.weights else None

    # Get matches
    results = matching.cv_to_jd_matches(
        db,
        cv_id=cv_id,
        filters=filters,
        weights=weights,
        limit=request.top_k
    )

    # Convert to response format - using correct field names from matching service
    match_results = [
        MatchResult(
            id=r["id"],
            title=r.get("title") or "Untitled",
            owner_name=r.get("owner_name") or "Unknown",
            score=r["final_score"],  # Fixed: using final_score instead of score
            base_score=r["base_score"],
            dist_global=r["dist_global"],
            dist_skills=r["dist_skills"],
            dist_lang=r["dist_lang"],
            structured=r["structured"],
            weights_used=r.get("weights_used")
        )
        for r in results
    ]

    return MatchResponse(
        source_id=cv_id,
        source_type="cv",
        results=match_results
    )


@router.post("/jd/{jd_id}/cvs", response_model=MatchResponse)
def find_cvs_for_jd(
    jd_id: int,
    request: MatchRequest = Body(default=MatchRequest()),
    db: Session = Depends(get_db)
):
    """
    Find the best matching CVs for a given JD.

    Supports optional filters and custom weights:
    - filters: min_years, required_skills, domains
    - weights: global, skills_tech, skills_language
    - top_k: number of results to return
    """
    # Check if JD exists
    jd_doc = db.query(models.Document).filter(
        models.Document.id == jd_id,
        models.Document.type == "jd",
    ).first()
    if not jd_doc:
        raise HTTPException(status_code=404, detail="JD not found")

    # Prepare filters and weights
    filters = request.filters.model_dump() if request.filters else None
    weights = request.weights.model_dump() if request.weights else None

    # Get matches
    results = matching.jd_to_cv_matches(
        db,
        jd_id=jd_id,
        filters=filters,
        weights=weights,
        limit=request.top_k
    )

    # Convert to response format - using correct field names from matching service
    match_results = [
        MatchResult(
            id=r["id"],
            title=r.get("title") or "Untitled",
            owner_name=r.get("owner_name") or "Unknown",
            score=r["final_score"],  # Fixed: using final_score instead of score
            base_score=r["base_score"],
            dist_global=r["dist_global"],
            dist_skills=r["dist_skills"],
            dist_lang=r["dist_lang"],
            structured=r["structured"],
            weights_used=r.get("weights_used")
        )
        for r in results
    ]

    return MatchResponse(
        source_id=jd_id,
        source_type="jd",
        results=match_results
    )


@router.post("/cv/{cv_id}/jds/rerank", response_model=LLMRerankResponse)
def rerank_jds_for_cv(
    cv_id: int,
    request: MatchRequest = Body(default=MatchRequest()),
    db: Session = Depends(get_db)
):
    """
    Find and rerank JDs for a CV using LLM analysis.

    First performs vector similarity search, then uses LLM to analyze each match
    and provide detailed explanations with scores from 0-100.
    """
    # Check if CV exists
    cv_doc = db.query(models.Document).filter(
        models.Document.id == cv_id,
        models.Document.type == "cv",
    ).first()
    if not cv_doc:
        raise HTTPException(status_code=404, detail="CV not found")

    # Prepare filters and weights
    filters = request.filters.model_dump() if request.filters else None
    weights = request.weights.model_dump() if request.weights else None

    # Get initial vector-based matches
    vector_matches = matching.cv_to_jd_matches(
        db,
        cv_id=cv_id,
        filters=filters,
        weights=weights,
        limit=request.top_k
    )

    if not vector_matches:
        return LLMRerankResponse(cv_id=cv_id, results=[])

    # Get CV structured data
    cv_data = cv_doc.structured

    # Rerank with LLM
    reranked_results = reranking.rerank_jds_for_cv(cv_data, vector_matches)

    return LLMRerankResponse(
        cv_id=cv_id,
        results=reranked_results
    )


@router.post("/jd/{jd_id}/cvs/rerank", response_model=LLMRerankResponse)
def rerank_cvs_for_jd(
    jd_id: int,
    request: MatchRequest = Body(default=MatchRequest()),
    db: Session = Depends(get_db)
):
    """
    Find and rerank CVs for a JD using LLM analysis.

    First performs vector similarity search, then uses LLM to analyze each match
    and provide detailed explanations with scores from 0-100.
    """
    # Check if JD exists
    jd_doc = db.query(models.Document).filter(
        models.Document.id == jd_id,
        models.Document.type == "jd",
    ).first()
    if not jd_doc:
        raise HTTPException(status_code=404, detail="JD not found")

    # Prepare filters and weights
    filters = request.filters.model_dump() if request.filters else None
    weights = request.weights.model_dump() if request.weights else None

    # Get initial vector-based matches
    vector_matches = matching.jd_to_cv_matches(
        db,
        jd_id=jd_id,
        filters=filters,
        weights=weights,
        limit=request.top_k
    )

    if not vector_matches:
        return LLMRerankResponse(jd_id=jd_id, results=[])

    # Get JD structured data
    jd_data = jd_doc.structured

    # Rerank with LLM
    reranked_results = reranking.rerank_cvs_for_jd(jd_data, vector_matches)

    return LLMRerankResponse(
        jd_id=jd_id,
        results=reranked_results
    )


@router.post("/cv/{cv_id}/rerank")
def rerank_jds_for_cv_simple(
    cv_id: int,
    candidates: list = Body(...),
    db: Session = Depends(get_db)
):
    """Rerank JDs for a CV using LLM analysis (simplified endpoint)"""
    cv_doc = db.query(models.Document).filter(
        models.Document.id == cv_id,
        models.Document.type == "cv",
    ).first()
    if not cv_doc:
        raise HTTPException(status_code=404, detail="CV not found")

    cv_data = cv_doc.structured
    reranked_results = reranking.rerank_jds_for_cv(cv_data, candidates)

    return {"reranked_results": reranked_results}


@router.post("/jd/{jd_id}/rerank")
def rerank_cvs_for_jd_simple(
    jd_id: int,
    candidates: list = Body(...),
    db: Session = Depends(get_db)
):
    """Rerank CVs for a JD using LLM analysis (simplified endpoint)"""
    jd_doc = db.query(models.Document).filter(
        models.Document.id == jd_id,
        models.Document.type == "jd",
    ).first()
    if not jd_doc:
        raise HTTPException(status_code=404, detail="JD not found")

    jd_data = jd_doc.structured
    reranked_results = reranking.rerank_cvs_for_jd(jd_data, candidates)

    return {"reranked_results": reranked_results}


@router.get("/embeddings/{doc_id}")
def check_embeddings(doc_id: int, db: Session = Depends(get_db)):
    """Debug endpoint to check if embeddings exist for a document."""
    from sqlalchemy import text

    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check embeddings
    embeddings = db.execute(text("""
        SELECT id, document_id, kind, 
               CASE WHEN vector IS NOT NULL THEN true ELSE false END as has_vector,
               CASE WHEN vector IS NOT NULL THEN array_length(vector::real[], 1) ELSE 0 END as vector_dim
        FROM document_embeddings 
        WHERE document_id = :doc_id
        ORDER BY kind
    """), {"doc_id": doc_id}).fetchall()

    embedding_status = []
    for e in embeddings:
        embedding_status.append({
            "id": e.id,
            "document_id": e.document_id,
            "kind": e.kind,
            "has_vector": e.has_vector,
            "vector_dim": e.vector_dim
        })

    expected_kinds = ["global", "skills_tech", "skills_language"]
    found_kinds = [e["kind"] for e in embedding_status]
    missing_kinds = [k for k in expected_kinds if k not in found_kinds]

    return {
        "document_id": doc_id,
        "document_type": doc.type,
        "document_title": doc.title,
        "embeddings": embedding_status,
        "expected_kinds": expected_kinds,
        "missing_kinds": missing_kinds,
        "is_complete": len(missing_kinds) == 0
    }

