from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
from app.models.document import DocumentType, DocumentStatus


class DocumentResponse(BaseModel):
    id: int
    client_id: int
    document_type: DocumentType
    status: DocumentStatus
    original_filename: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    ocr_data: Optional[Dict[str, Any]] = None
    extracted_name: Optional[str] = None
    extracted_document_number: Optional[str] = None
    extracted_expiry: Optional[str] = None
    is_authentic: Optional[bool] = None
    authenticity_score: Optional[int] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentReview(BaseModel):
    status: DocumentStatus
    rejection_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None
    is_authentic: Optional[bool] = None
    authenticity_score: Optional[int] = None
