from sqlalchemy import create_engine, inspect, Column, Integer, Float, String, DateTime, Text, ForeignKey, MetaData, Table
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import sys

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, engine

def migrate_lab_payments():
    print("Migrating Lab Payments...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "lab_payments" not in existing_tables:
        print("Creating table 'lab_payments'...")
        # Define table using SQLAlchemy Core for direct creation
        metadata = MetaData()
        lab_payments = Table(
            'lab_payments', metadata,
            Column('id', Integer, primary_key=True, index=True),
            Column('laboratory_id', Integer, ForeignKey("laboratories.id"), index=True),
            Column('amount', Float),
            Column('date', DateTime, default=datetime.utcnow, index=True),
            Column('notes', Text, nullable=True),
            Column('method', String, default="Cash"),
            Column('tenant_id', Integer, ForeignKey("tenants.id"), nullable=True, index=True)
        )
        metadata.create_all(engine)
        print("Table 'lab_payments' created successfully.")
    else:
        print("Table 'lab_payments' already exists.")

if __name__ == "__main__":
    migrate_lab_payments()
