import sys
import os

# Setup sys.path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import sessionmaker
from backend.database import async_engine
engine = async_engine.sync_engine
SyncSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
from backend.models import clinical as clinical_models
from backend.models import inventory as inv_models
from backend.services.inventory_learning_service import InventoryLearningService

def backfill():
    db = SyncSessionLocal()
    try:
        # Find all treatments
        treatments = db.query(clinical_models.Treatment).order_by(clinical_models.Treatment.date.asc()).all()
        print(f"Found {len(treatments)} treatments to analyze.")
        
        backfilled_count = 0
        non_divisible_count = 0
        divisible_count = 0
        
        for t in treatments:
            # Check if this treatment already has TreatmentMaterialUsage records
            existing_usage_count = db.query(inv_models.TreatmentMaterialUsage).filter(
                inv_models.TreatmentMaterialUsage.treatment_id == t.id
            ).count()
            if existing_usage_count > 0:
                # Already backfilled or saved
                continue
                
            # Find stock movements for this treatment
            # USAGE movements matching TREATMENT:id or TREATMENT_MATERIALS:id
            movements = db.query(inv_models.StockMovement).filter(
                inv_models.StockMovement.reference_id.in_([f"TREATMENT:{t.id}", f"TREATMENT_MATERIALS:{t.id}"])
            ).all()
            
            if not movements:
                continue
                
            print(f"Processing Treatment #{t.id} ({t.procedure or 'No Procedure'}) on {t.date} with {len(movements)} movements.")
            
            # Reconstruct TreatmentMaterialUsage from stock movements
            for move in movements:
                # Find stock item and batch
                stock_item = db.query(inv_models.StockItem).get(move.stock_item_id)
                if not stock_item:
                    continue
                batch = db.query(inv_models.Batch).get(stock_item.batch_id)
                if not batch:
                    continue
                mat = db.query(inv_models.Material).get(batch.material_id)
                if not mat:
                    continue
                
                # Check if it's NON_DIVISIBLE
                if mat.type == "NON_DIVISIBLE":
                    quantity_used = abs(move.change_amount)
                    cost_per_unit = batch.cost_per_unit or mat.standard_price or 0.0
                    cost_calculated = quantity_used * cost_per_unit
                    
                    usage = inv_models.TreatmentMaterialUsage(
                        treatment_id=t.id,
                        material_id=mat.id,
                        session_id=None,
                        weight_score=1.0,
                        quantity_used=quantity_used,
                        cost_calculated=cost_calculated,
                        is_manual_override=False,
                        tenant_id=t.tenant_id,
                        created_at=t.date
                    )
                    db.add(usage)
                    non_divisible_count += 1
                else:
                    # Divisible material: We need to find the session that was active when treatment occurred.
                    # We match opened_at <= treatment_date and (closed_at is null or closed_at >= treatment_date)
                    session = db.query(inv_models.MaterialSession).join(inv_models.StockItem).join(inv_models.Batch).filter(
                        inv_models.StockItem.tenant_id == t.tenant_id,
                        inv_models.Batch.material_id == mat.id,
                        inv_models.MaterialSession.opened_at <= t.date
                    ).filter(
                        (inv_models.MaterialSession.closed_at.is_(None)) | (inv_models.MaterialSession.closed_at >= t.date)
                    )
                    
                    # Try to filter by doctor if doctor_id is present
                    if t.doctor_id:
                        session_doc = session.filter(inv_models.MaterialSession.doctor_id == t.doctor_id).first()
                        if session_doc:
                            session = session_doc
                        else:
                            session = session.first()
                    else:
                        session = session.first()
                        
                    session_id = session.id if session else None
                    
                    usage = inv_models.TreatmentMaterialUsage(
                        treatment_id=t.id,
                        material_id=mat.id,
                        session_id=session_id,
                        weight_score=1.0,
                        quantity_used=None, # will be populated when session closes/re-learned
                        cost_calculated=None,
                        is_manual_override=False,
                        tenant_id=t.tenant_id,
                        created_at=t.date
                    )
                    db.add(usage)
                    divisible_count += 1
            
            backfilled_count += 1
            
        db.commit()
        print(f"Successfully backfilled {backfilled_count} treatments ({non_divisible_count} non-divisible, {divisible_count} divisible usage records created).")
        
        # Now trigger re-learning for all closed sessions to allocate divisible material quantities/costs
        closed_sessions = db.query(inv_models.MaterialSession).filter(
            inv_models.MaterialSession.status == "CLOSED",
            inv_models.MaterialSession.total_amount_consumed.isnot(None)
        ).all()
        
        print(f"Re-triggering learning algorithms for {len(closed_sessions)} closed sessions...")
        learning_service = InventoryLearningService(db)
        
        for sess in closed_sessions:
            try:
                # We can reset status to ACTIVE temporarily or just pass to close_session
                # But close_session has an idempotent check: if session.status == "CLOSED": return
                # So we temporarily set it to ACTIVE to re-run learning
                sess.status = "ACTIVE"
                db.commit()
                
                learning_service.close_session(
                    session_id=sess.id,
                    total_consumed=sess.total_amount_consumed,
                    user_id=sess.doctor_id or 1
                )
                print(f"Re-learned session #{sess.id} successfully.")
            except Exception as e:
                print(f"Error re-learning session #{sess.id}: {e}")
                db.rollback()
                
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
