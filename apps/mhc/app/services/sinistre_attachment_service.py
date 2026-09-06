"""Helpers pièces jointes sinistre (certificat de décès hospitalier, etc.)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.sinistre_attachment import SinistreAttachment, ATTACHMENT_CERTIFICAT_DECES
from app.schemas.sinistre_attachment import SinistreAttachmentInfo


def attachment_to_info(attachment: SinistreAttachment) -> SinistreAttachmentInfo:
    uploaded_by_name = None
    if attachment.uploaded_by is not None:
        uploaded_by_name = (
            attachment.uploaded_by.full_name
            or attachment.uploaded_by.username
            or attachment.uploaded_by.email
        )
    return SinistreAttachmentInfo(
        id=attachment.id,
        attachment_type=attachment.attachment_type,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        file_size=attachment.file_size,
        uploaded_by_id=attachment.uploaded_by_id,
        uploaded_by_name=uploaded_by_name,
        created_at=attachment.created_at,
    )


def get_certificat_deces_attachment(db: Session, sinistre_id: int) -> Optional[SinistreAttachment]:
    return (
        db.query(SinistreAttachment)
        .options(joinedload(SinistreAttachment.uploaded_by))
        .filter(
            SinistreAttachment.sinistre_id == sinistre_id,
            SinistreAttachment.attachment_type == ATTACHMENT_CERTIFICAT_DECES,
        )
        .first()
    )
