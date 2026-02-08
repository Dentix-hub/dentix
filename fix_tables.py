from backend.database import engine
from backend.models.inventory import Base
print("Creating missing tables...")
Base.metadata.create_all(bind=engine)
print("Tables created.")
