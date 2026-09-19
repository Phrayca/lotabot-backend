from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=schemas.CoursesOut)
def list_courses(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    courses = db.query(models.Course).order_by(models.Course.order).all()
    return schemas.CoursesOut(courses=[
        schemas.CourseOut(id=c.id, title=c.title, durationMin=c.duration_min, metaLabel=c.meta_label, premium=c.premium)
        for c in courses
    ])


@router.get("/{course_id}", response_model=schemas.CourseDetailOut)
def get_course(course_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    c = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    if c.premium:
        plan = user.subscription.plan if user.subscription else "classique"
        if plan != "premium":
            raise HTTPException(status_code=403, detail="Cette leçon est réservée aux abonnés Premium")
    return schemas.CourseDetailOut(
        id=c.id, title=c.title, durationMin=c.duration_min, metaLabel=c.meta_label,
        premium=c.premium, body=c.body or "",
    )
