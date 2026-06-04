import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user, require_compliance
from app.core.config import settings
from app.core.crypto import encrypt_bytes, decrypt_bytes
from app.models.user import User, UserRole
from app.models.client import ClientProfile
from app.models.document import Document, DocumentType, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentReview
from app.services.audit_service import log_pii_access
from app.services import monitoring_service as mon
from app.services.storage import get_storage

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: Request,
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
    stored_name = f"{uuid.uuid4()}.{ext}.enc"
    # Encrypt the file contents at rest (GDPR Art.32), then store via the
    # configured backend (local disk or S3/MinIO).
    get_storage().put(stored_name, encrypt_bytes(content))

    doc = Document(
        client_id=profile.id,
        document_type=document_type,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_path=stored_name,
        file_size=len(content),
        mime_type=file.content_type,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    await mon.upsert_device(db, current_user.id, request)
    await mon.record_activity(
        db, user=current_user, action_type="DOCUMENT_UPLOADED",
        entity_type="document", entity_id=doc.id, request=request,
        details=f"Uploaded {document_type.value}",
    )
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
    request: Request,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    docs = await db.execute(select(Document).where(Document.client_id == client_id))
    documents = docs.scalars().all()
    await log_pii_access(
        db, user=current_user, resource_type="client_documents",
        resource_id=client_id,
        description=f"Viewed documents of client #{client_id}",
        request=request,
    )
    await db.commit()
    return documents


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a decrypted document. Allowed for the owning client or compliance/admin staff."""
    doc = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    profile = (
        await db.execute(select(ClientProfile).where(ClientProfile.id == doc.client_id))
    ).scalar_one_or_none()

    is_owner = profile is not None and profile.user_id == current_user.id
    is_staff = current_user.role in (UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN)
    if not (is_owner or is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")

    storage = get_storage()
    if not storage.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File missing from storage")

    plaintext = decrypt_bytes(storage.get(doc.file_path))

    # Record staff access to a client's personal document.
    if is_staff and not is_owner:
        await log_pii_access(
            db, user=current_user, resource_type="document", resource_id=doc.id,
            description=f"Downloaded document #{doc.id} of client #{doc.client_id}",
            request=request,
        )
        await db.commit()

    return Response(
        content=plaintext,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


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
