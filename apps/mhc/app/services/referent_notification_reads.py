"""Marquer comme lues les notifications liées à une entité une fois le dossier traité."""
from typing import Collection

from sqlalchemy.orm import Session

from app.models.notification import Notification


def mark_notifications_read_for_relation(
    db: Session,
    *,
    types: Collection[str],
    lien_relation_type: str,
    lien_relation_id: int,
) -> None:
    """
    Met is_read=True pour tous les destinataires (référent, autre référent, reviewer, etc.).
    """
    if not types or not lien_relation_id:
        return
    db.query(Notification).filter(
        Notification.is_read == False,  # noqa: E712
        Notification.type_notification.in_(list(types)),
        Notification.lien_relation_type == lien_relation_type,
        Notification.lien_relation_id == lien_relation_id,
    ).update({"is_read": True}, synchronize_session=False)
