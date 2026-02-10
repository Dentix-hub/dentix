from sqlalchemy.orm import Session
from backend import models, schemas

from sqlalchemy import or_


def get_procedures(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Procedure)
        .filter(
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id == None,
            )
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_procedure(db: Session, procedure: schemas.ProcedureCreate, tenant_id: int):
    db_procedure = models.Procedure(**procedure.dict(), tenant_id=tenant_id)
    db.add(db_procedure)
    db.commit()
    db.refresh(db_procedure)
    return db_procedure


def update_procedure(
    db: Session, procedure_id: int, procedure: schemas.ProcedureCreate, tenant_id: int
):
    db_procedure = (
        db.query(models.Procedure)
        .filter(
            models.Procedure.id == procedure_id,
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id == None,
            ),
        )
        .first()
    )
    if db_procedure:
        # If updating a global procedure, we might want to "fork" it (Copy on Write)
        # But for now, let's allow direct modification as per user request to "fix" the list.
        for key, value in procedure.dict().items():
            setattr(db_procedure, key, value)
        db.commit()
        db.refresh(db_procedure)
    return db_procedure


def delete_procedure(db: Session, procedure_id: int, tenant_id: int):
    db_procedure = (
        db.query(models.Procedure)
        .filter(
            models.Procedure.id == procedure_id,
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id == None,
            ),
        )
        .first()
    )
    if db_procedure:
        # Cascade Delete Step 1: Remove from all price lists
        db.query(models.PriceListItem).filter(
            models.PriceListItem.procedure_id == procedure_id
        ).delete(synchronize_session=False)

        # Cascade Delete Step 2: Remove from inventory weights (Smart Inventory)
        db.query(models.ProcedureMaterialWeight).filter(
            models.ProcedureMaterialWeight.procedure_id == procedure_id
        ).delete(synchronize_session=False)

        db.delete(db_procedure)
        db.commit()
    return db_procedure
