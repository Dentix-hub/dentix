import pytest
from backend.database import SessionLocal
from sqlalchemy import text

def test_index_usage(db):
    # Detect Dialect
    dialect = db.bind.dialect.name
    print(f"DEBUG: Testing Index on Dialect: {dialect}")
    
    if dialect == "sqlite":
        # SQLite uses EXPLAIN QUERY PLAN for high-level info
        result = db.execute(text("EXPLAIN QUERY PLAN SELECT * FROM patients WHERE tenant_id = 1")).fetchall()
        plan = str(result)
        # SQLite Plan Example: (..., 'SEARCH table patients USING INDEX idx_patients_tenant (tenant_id=?)')
        # We look for "USING INDEX"
        found_index = "USING INDEX" in plan
    else:
        # Postgres/Other
        result = db.execute(text("EXPLAIN SELECT * FROM patients WHERE tenant_id = 1")).fetchall()
        plan = str(result)
        found_index = False
        for row in result:
             line = str(row).lower()
             if "index" in line and "scan" in line:
                 found_index = True
                 break

    if not found_index and dialect != "sqlite":
         # Fallback check for Postgres text plan if returned as single string
         if "USING INDEX" in plan:
             found_index = True
    
    assert found_index, f"Query did NOT use the expected index! (Dialect: {dialect}) Plan: {plan}"
    print("SUCCESS: Query used index")

if __name__ == "__main__":
    test_index_usage()
