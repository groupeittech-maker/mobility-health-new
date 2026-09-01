from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceHistory


def get_invoice_stage(invoice: Invoice) -> Optional[str]:
    status = invoice.statut
    if status == "pending_medical":
        return "medical"
    if status == "pending_sinistre":
        return "sinistre"
    if status == "pending_compta":
        return "compta"
    if status in {"validated", "paid"}:
        return "compta"
    if status == "rejected":
        return "rejected"
    return None


def record_invoice_history(
    db: Session,
    invoice: Invoice,
    action: str,
    actor_id: Optional[int] = None,
    notes: Optional[str] = None,
    previous_status: Optional[str] = None,
    previous_stage: Optional[str] = None,
) -> InvoiceHistory:
    entry = InvoiceHistory(
        invoice_id=invoice.id,
        action=action,
        previous_status=previous_status,
        new_status=invoice.statut,
        previous_stage=previous_stage,
        new_stage=get_invoice_stage(invoice),
        actor_id=actor_id,
        notes=notes,
    )
    db.add(entry)
    return entry


