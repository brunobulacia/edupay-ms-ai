from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Literal

from app.database import get_db
from app.repositories.document_repository import DocumentRepository

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_TYPES = {"CI_ALUMNO", "CI_TUTOR", "CERT_NACIMIENTO", "CONTRATO", "COMPROBANTE", "OTRO"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "application/pdf"}


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    family_id: str = Form(...),
    uploaded_by: str = Form(...),
    doc_type: str = Form(...),
    student_id: str = Form(None),
):
    if doc_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type must be one of {ALLOWED_TYPES}")
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and PDF files are allowed")

    content = await file.read()
    now = datetime.now(timezone.utc)
    s3_key = f"families/{family_id}/{doc_type.lower()}/{now.strftime('%Y%m%d%H%M%S')}_{file.filename}"

    doc = {
        "familyId": family_id,
        "studentId": student_id,
        "type": doc_type,
        "originalName": file.filename,
        "s3Key": s3_key,
        "s3Bucket": "edupay-scz-docs",
        "mimeType": file.content_type,
        "sizeBytes": len(content),
        "status": "PENDING",
        "rejectionReason": None,
        "uploadedBy": uploaded_by,
        "reviewedBy": None,
        "reviewedAt": None,
        "uploadedAt": now,
        "aiValidation": None,
    }

    doc_id = await DocumentRepository(get_db()).save(doc)

    return {
        "documentId": doc_id,
        "s3Key": s3_key,
        "status": "PENDING",
        "message": "Document uploaded successfully. Pending review.",
    }


@router.get("/family/{family_id}")
async def list_family_documents(family_id: str):
    docs = await DocumentRepository(get_db()).find_by_family(family_id)
    return {"familyId": family_id, "documents": docs}


@router.get("/pending")
async def list_pending_documents():
    docs = await DocumentRepository(get_db()).find_pending()
    return {"count": len(docs), "documents": docs}


@router.patch("/{document_id}/status")
async def update_document_status(
    document_id: str,
    status: Literal["APPROVED", "REJECTED"],
    reviewed_by: str,
    rejection_reason: str | None = None,
):
    if status == "REJECTED" and not rejection_reason:
        raise HTTPException(status_code=400, detail="rejection_reason required when rejecting")
    await DocumentRepository(get_db()).update_status(document_id, status, reviewed_by, rejection_reason)
    return {"documentId": document_id, "status": status}
