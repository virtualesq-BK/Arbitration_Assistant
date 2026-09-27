from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.deps import get_case_for_user, get_current_user, get_document_for_user, parse_uuid
from core.security import TokenError, verify_download_token
from models.document import (
    ConfidentialityLevel,
    Document,
    DocumentType,
    PrivilegeStatus,
    ProcessingStatus,
)
from models.document_chunk import DocumentChunk
from models.user import User
from schemas.document import DocumentDetail, DocumentResponse, DocumentUpdate
from services.audit_service import audit
from services.ingest_service import extract_text, index_document
from services.storage_service import StorageError, get_storage, safe_filename

router = APIRouter(tags=["documents"])


@router.post("/cases/{case_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    author: str | None = Form(None),
    recipient: str | None = Form(None),
    doc_date: date | None = Form(None),
    language: str | None = Form("en"),
    confidentiality_level: ConfidentialityLevel = Form(ConfidentialityLevel.CONFIDENTIAL),
    privilege_status: PrivilegeStatus = Form(PrivilegeStatus.UNREVIEWED),
    evidence_number: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    case = await get_case_for_user(case_id, user, db)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB")

    filename = safe_filename(file.filename or "upload")
    storage = get_storage()
    key, digest = await storage.save(case.org_id, case.id, filename, data)

    text = await extract_text(data, file.content_type, filename)
    doc = Document(
        id=uuid.uuid4(),
        case_id=case.id,
        org_id=case.org_id,
        filename=filename,
        s3_key=key,
        file_size=len(data),
        mime_type=file.content_type,
        document_type=document_type,
        author=author,
        recipient=recipient,
        doc_date=doc_date,
        language=language,
        confidentiality_level=confidentiality_level,
        privilege_status=privilege_status,
        evidence_number=evidence_number,
        file_hash=digest,
        ocr_text=text or None,
        ocr_status=ProcessingStatus.COMPLETED if text else ProcessingStatus.PENDING,
        classification_status=ProcessingStatus.PENDING,
        metadata_json={"original_filename": file.filename},
    )
    db.add(doc)
    await db.flush()
    chunks = await index_document(db, doc) if text else 0
    doc.metadata_json = {**(doc.metadata_json or {}), "chunks": chunks}
    audit(db, user=user, action="document.upload", resource_type="document", resource_id=doc.id,
          details={"case_id": str(case.id), "filename": filename, "sha256": digest}, request=request)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/cases/{case_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    case_id: str,
    document_type: DocumentType | None = None,
    q: str | None = Query(None, description="Filename / author contains"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Document]:
    case = await get_case_for_user(case_id, user, db)
    stmt = select(Document).where(Document.case_id == case.id, Document.org_id == user.org_id)
    if document_type is not None:
        stmt = stmt.where(Document.document_type == document_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Document.filename.ilike(like) | Document.author.ilike(like))
    stmt = stmt.order_by(Document.doc_date.asc().nulls_last(), Document.filename)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DocumentDetail:
    doc = await get_document_for_user(document_id, user, db)
    chunk_count = (
        await db.execute(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    ).scalar_one()
    url: str | None = None
    expires: int | None = None
    if doc.s3_key:
        url, expires = get_storage().presigned_url(doc.id, doc.org_id)
    audit(db, user=user, action="document.view", resource_type="document", resource_id=doc.id, request=request)
    await db.commit()
    return DocumentDetail(
        **DocumentResponse.model_validate(doc).model_dump(),
        ocr_text=doc.ocr_text,
        download_url=url,
        download_url_expires_in=expires,
        chunk_count=chunk_count,
    )


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    body: DocumentUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    doc = await get_document_for_user(document_id, user, db)
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(doc, key, value)
    audit(db, user=user, action="document.update", resource_type="document", resource_id=doc.id, details={"fields": list(changes)}, request=request)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/documents/{document_id}/download")
async def download_document(document_id: str, token: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Pre-signed download: authorised by the short-lived signed token, not the bearer header."""
    try:
        payload = verify_download_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=403, detail="Invalid or expired download link") from exc
    did = parse_uuid(document_id, "document id")
    if payload.get("sub") != str(did):
        raise HTTPException(status_code=403, detail="Token does not match document")
    doc = (
        await db.execute(select(Document).where(Document.id == did, Document.org_id == uuid.UUID(payload["org"])))
    ).scalar_one_or_none()
    if doc is None or not doc.s3_key:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data = await get_storage().read(doc.s3_key)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=data,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )
