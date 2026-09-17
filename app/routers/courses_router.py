from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=schemas.CoursesOut)
def list_courses(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    courses = db.query(models.Course).order_by(models.Course.order).all()
    return schemas.CoursesOut(courses=[
        schemas.CourseOut(title=c.title, durationMin=c.duration_min, metaLabel=c.meta_label, premium=c.premium)
        for c in courses
    ])
