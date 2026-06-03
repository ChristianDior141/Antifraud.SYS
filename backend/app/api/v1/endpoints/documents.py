import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user, require_compliance
from app.core.config import settings
from app.models.user import User
from app.models.client import ClientProfile
from app.models.document import Document, DocumentType, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentReview

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Client profile not found")

    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    stored_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        client_id=profile.id,
        document_type=document_type,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/my", response_model=List[DocumentResponse])
async def get_my_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    docs = await db.execute(select(Document).where(Document.client_id == profile.id))
    return docs.scalars().all()


@router.get("/client/{client_id}", response_model=List[DocumentResponse])
async def get_client_documents(
    client_id: int,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    docs = await db.execute(select(Document).where(Document.client_id == client_id))
    return docs.scalars().all()


@router.put("/{document_id}/review", response_model=DocumentResponse)
async def review_document(
    document_id: int,
    review: DocumentReview,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from datetime import datetime
    doc.status = review.status
    doc.rejection_reason = review.rejection_reason
    doc.reviewer_notes = review.reviewer_notes
    doc.is_authentic = review.is_authentic
    doc.authenticity_score = review.authenticity_score
    doc.reviewed_by = current_user.id
    doc.reviewed_at = datetime.utcnow()
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc
