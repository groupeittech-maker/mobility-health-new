"""
Script pour supprimer toutes les notifications de type "attestation_definitive_ready"
"""
import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.notification import Notification

def delete_attestation_notifications():
    """Supprime toutes les notifications de type 'attestation_definitive_ready'"""
    db: Session = SessionLocal()
    try:
        # Trouver toutes les notifications de type "attestation_definitive_ready"
        notifications = db.query(Notification).filter(
            Notification.type_notification == "attestation_definitive_ready"
        ).all()
        
        count = len(notifications)
        
        if count == 0:
            print("Aucune notification de type 'attestation_definitive_ready' trouvée.")
            return
        
        print(f"Trouvé {count} notification(s) de type 'attestation_definitive_ready'.")
        
        # Supprimer toutes les notifications
        for notification in notifications:
            print(f"  - Suppression de la notification ID {notification.id} pour l'utilisateur {notification.user_id}")
            db.delete(notification)
        
        db.commit()
        print(f"\n✅ {count} notification(s) supprimée(s) avec succès.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la suppression des notifications: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Suppression des notifications 'attestation_definitive_ready'...")
    delete_attestation_notifications()

