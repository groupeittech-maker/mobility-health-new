"""Notifications pertinentes pour le médecin référent MH (push FCM + liste in-app)."""

from typing import FrozenSet

REFERENT_NOTIFICATION_TYPES: FrozenSet[str] = frozenset(
    {
        "sos_alert",
        "medical_report_submitted",
        "invoice_medical_review",
    }
)
