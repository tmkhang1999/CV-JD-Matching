from fastapi import APIRouter, UploadFile, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.db.session import SessionLocal
from app.db import models
from app.services import ingestion, extraction_gpt, normalization, embeddings
from app.schemas.jd import JDCreateResponse

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def list_jds(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """List all JDs with ID, job_title, company_name, and created_at"""
    jds = db.query(models.Document).filter(models.Document.type == "jd").order_by(models.Document.created_at).all()

    results = []
    for index, jd in enumerate(jds, 1):
        results.append({
            "id": jd.id,
            "jd_id": str(index),  # Sequential JD numbering (just the number)
            "job_title": jd.title,
            "company_name": jd.owner_name,
            "created_at": jd.created_at.isoformat() if jd.created_at else None
        })

    return results


@router.get("/{jd_id}")
def get_jd(jd_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get full JD document by ID including structured data and raw_text"""
    jd = db.query(models.Document).filter(
        models.Document.id == jd_id, models.Document.type == "jd"
    ).first()

    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")

    return {
        "id": jd.id,
        "type": jd.type,
        "title": jd.title,
        "owner_name": jd.owner_name,
        "raw_text": jd.raw_text,
        "structured": jd.structured,
        "file_path": jd.file_path,
        "created_at": jd.created_at.isoformat() if jd.created_at else None,
        "updated_at": jd.updated_at.isoformat() if jd.updated_at else None,
    }


@router.get("/{jd_id}/file")
def download_jd_file(jd_id: int, db: Session = Depends(get_db)):
    """Download the original JD file"""
    jd = db.query(models.Document).filter(
        models.Document.id == jd_id, models.Document.type == "jd"
    ).first()

    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")

    if not jd.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(jd.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    # Determine media type based on extension
    media_type = "application/pdf" if file_path.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"JD_{jd.id}_{jd.title}{file_path.suffix}"
    )


@router.post("/upload", response_model=JDCreateResponse)
async def upload_jd(
    file: UploadFile,
    extraction_model: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    path = ingestion.save_upload_file(file)
    raw_text = ingestion.extract_raw_text(path)

    # 1. GPT extraction with optional model override
    structured_raw = extraction_gpt.extract_jd_structured(raw_text, extraction_model)

    # 2. Normalize
    jd_struct = normalization.normalize_jd(structured_raw, raw_text)

    # 3. Store document
    doc = models.Document(
        type="jd",
        title=jd_struct.job_profile.title,
        owner_name=jd_struct.job_profile.client.name if jd_struct.job_profile.client else None,
        raw_text=raw_text,
        structured=jd_struct.model_dump(),
        file_path=str(path),  # Save file path
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.flush()  # Ensure document gets an ID before creating embeddings

    # 4. Generate embeddings with text-embedding-3-small
    embeddings.update_document_embeddings(db, doc, jd_struct.model_dump())

    # Commit both document and embeddings together
    db.commit()
    db.refresh(doc)

    # Get the JD-specific ID for the response
    jds = db.query(models.Document).filter(models.Document.type == "jd").order_by(models.Document.created_at).all()
    jd_sequence_id = None
    for index, jd in enumerate(jds, 1):
        if jd.id == doc.id:
            jd_sequence_id = f"JD-{index}"
            break

    return JDCreateResponse(
        id=doc.id,
        jd_id=jd_sequence_id,
        structured=jd_struct
    )


@router.delete("/{jd_id}")
def delete_jd(jd_id: int, db: Session = Depends(get_db)):
    """Delete a JD document by ID"""
    jd = db.query(models.Document).filter(
        models.Document.id == jd_id, models.Document.type == "jd"
    ).first()

    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")

    try:
        if jd.file_path:
            file_path = Path(jd.file_path)
            if file_path.exists():
                file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

    db.delete(jd)
    db.commit()
    return {"message": f"JD {jd_id} deleted successfully"}

