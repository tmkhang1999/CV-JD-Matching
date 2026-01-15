from fastapi import APIRouter, UploadFile, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.db.session import SessionLocal
from app.db import models
from app.services import ingestion, extraction_gpt, normalization, embeddings
from app.schemas.cv import CVCreateResponse

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def list_cvs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """List all CVs with ID, name, title, and created_at"""
    cvs = db.query(models.Document).filter(models.Document.type == "cv").order_by(models.Document.created_at).all()

    results = []
    for index, cv in enumerate(cvs, 1):
        results.append({
            "id": cv.id,
            "cv_id": str(index),  # Sequential CV numbering (just the number)
            "name": cv.owner_name,
            "title": cv.title,
            "created_at": cv.created_at.isoformat() if cv.created_at else None
        })

    return results


@router.get("/{cv_id}")
def get_cv(cv_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get full CV document by ID including structured data and raw_text"""
    cv = db.query(models.Document).filter(
        models.Document.id == cv_id, models.Document.type == "cv"
    ).first()

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    return {
        "id": cv.id,
        "type": cv.type,
        "title": cv.title,
        "owner_name": cv.owner_name,
        "raw_text": cv.raw_text,
        "structured": cv.structured,
        "file_path": cv.file_path,
        "created_at": cv.created_at.isoformat() if cv.created_at else None,
        "updated_at": cv.updated_at.isoformat() if cv.updated_at else None,
    }


@router.get("/{cv_id}/file")
def download_cv_file(cv_id: int, db: Session = Depends(get_db)):
    """Download the original CV file"""
    cv = db.query(models.Document).filter(
        models.Document.id == cv_id, models.Document.type == "cv"
    ).first()

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    if not cv.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(cv.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    # Determine media type based on extension
    media_type = "application/pdf" if file_path.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"CV_{cv.id}_{cv.owner_name}{file_path.suffix}"
    )


@router.post("/upload", response_model=CVCreateResponse)
async def upload_cv(
    file: UploadFile, 
    extraction_model: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    path = ingestion.save_upload_file(file)
    raw_text = ingestion.extract_raw_text(path)

    # 1. GPT extraction with optional model override
    structured_raw = extraction_gpt.extract_cv_structured(raw_text, extraction_model)

    # 2. Normalize
    cv_struct = normalization.normalize_cv(structured_raw, raw_text)

    # 3. Store document
    doc = models.Document(
        type="cv",
        title=cv_struct.candidate_profile.headline.current_position if cv_struct.candidate_profile.headline else None,
        owner_name=cv_struct.candidate_profile.identity.full_name,
        raw_text=raw_text,
        structured=cv_struct.model_dump(),
        file_path=str(path),  # Save file path
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.flush()  # Ensure document gets an ID before creating embeddings

    # 4. Generate embeddings with text-embedding-3-small
    embeddings.update_document_embeddings(db, doc, cv_struct.model_dump())

    # Commit both document and embeddings together
    db.commit()
    db.refresh(doc)

    # Get the CV-specific ID for the response
    cvs = db.query(models.Document).filter(models.Document.type == "cv").order_by(models.Document.created_at).all()
    cv_sequence_id = None
    for index, cv in enumerate(cvs, 1):
        if cv.id == doc.id:
            cv_sequence_id = str(index)  # Just the number
            break

    return CVCreateResponse(
        id=doc.id,
        cv_id=cv_sequence_id,
        structured=cv_struct
    )


@router.delete("/{cv_id}")
def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    """Delete a CV document by ID"""
    cv = db.query(models.Document).filter(
        models.Document.id == cv_id, models.Document.type == "cv"
    ).first()

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    try:
        if cv.file_path:
            file_path = Path(cv.file_path)
            if file_path.exists():
                file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

    db.delete(cv)
    db.commit()
    return {"message": f"CV {cv_id} deleted successfully"}
