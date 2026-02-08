from backend.database import engine
from sqlalchemy import text

def fix_missing_column():
    print("Checking for missing columns...")
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(materials)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'standard_price' not in columns:
                print("Adding missing column 'standard_price' to 'materials'...")
                conn.execute(text("ALTER TABLE materials ADD COLUMN standard_price FLOAT DEFAULT 0.0"))
                conn.commit()
                print("✅ Column added successfully.")
            else:
                print("ℹ️ Column 'standard_price' already exists.")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_missing_column()
