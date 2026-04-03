from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.notification import Notification
from .users import get_current_user

router = APIRouter()


@router.get("/")
def get_notifications(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Return all notifications for the current user, newest first."""
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.notification_id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "swap_id": n.swap_id,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.put("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if notif:
        notif.read = True
        db.commit()
    return {"ok": True}


@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.read == False,
    ).update({"read": True})
    db.commit()
    return {"ok": True}
