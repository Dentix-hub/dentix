#!/usr/bin/env python3
"""
Check and apply migration for Material Consumption Tracking feature.
Run this on staging/production server to apply pending migrations.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime import migration
from sqlalchemy import create_engine
from backend.core.config import settings

def check_and_migrate():
    """Check migration status and apply if needed."""
    
    # Load alembic config
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "alembic.ini"))
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Check current revision
    with engine.connect() as conn:
        context = migration.MigrationContext.configure(conn)
        current_rev = context.get_current_revision()
        
        # Get head revision
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()
        
        print(f"📊 Database Migration Status:")
        print(f"   Current: {current_rev}")
        print(f"   Head:    {head_rev}")
        
        if current_rev == head_rev:
            print("✅ Database is up to date!")
            return 0
        
        print(f"\n⚠️  Migration needed: {current_rev} → {head_rev}")
        print("\n🔧 Applying migrations...")
        
        # Apply migrations
        command.upgrade(alembic_cfg, "head")
        
        print("✅ Migration completed successfully!")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(check_and_migrate())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
