"""The 'Save Design' button and the Saved Designs list on the profile page."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import SavedDesign, User
from app.schemas.common import Message
from app.schemas.designs import SavedDesignCreate, SavedDesignOut

router = APIRouter(prefix="/designs", tags=["Saved Designs"])


@router.post("", response_model=SavedDesignOut, status_code=201)
def save_design(
    data: SavedDesignCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    design = SavedDesign(
        user_id=user.id,
        title=data.title,
        prompt=data.prompt,
        space_type=data.space_type,
        requirements=data.requirements.model_dump(),
        image_url=data.image_url,
        design_image_id=data.design_image_id,
    )
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


@router.get("/mine", response_model=list[SavedDesignOut])
def my_designs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SavedDesign).filter(SavedDesign.user_id == user.id).order_by(SavedDesign.id.desc()).all()


@router.delete("/{design_id}", response_model=Message)
def delete_design(
    design_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    design = db.query(SavedDesign).filter(SavedDesign.id == design_id, SavedDesign.user_id == user.id).first()
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")
    db.delete(design)
    db.commit()
    return {"message": "Design deleted"}
