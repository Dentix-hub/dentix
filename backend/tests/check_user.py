from backend import database, models, schemas
from backend.auth import verify_password, get_password_hash

def check_admin_user():
    db = database.SessionLocal()
    try:
        email = "eslamemara1312@gmail.com"
        # Check user
        user = db.query(models.User).filter(models.User.username == email).first()
        
        if not user:
            print(f"[FAIL] User {email} NOT FOUND in database!")
            return False
            
        print(f"[OK] User found: ID={user.id}, Role={user.role}")
        
        # Verify Password
        # We know the seed sets it to "ESLAMomara11##"
        # Let's try to verify it
        target_pass = "ESLAMomara11##"
        if verify_password(target_pass, user.hashed_password):
            print("[OK] Password verification SUCCESS.")
        else:
            print("[FAIL] Password verification FAILED. Resetting...")
            user.hashed_password = get_password_hash(target_pass)
            db.commit()
            print("[FIX] Password reset to 'ESLAMomara11##'.")
            
        return True
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_user()
