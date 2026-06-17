import sys
import os
import asyncio

# Add current directory to path
sys.path.append(os.getcwd())

from backend.database import AsyncSessionLocal
from backend import models, auth
from sqlalchemy import select


async def reset_passwords():
    async with AsyncSessionLocal() as db:
        try:
            print("Resetting admin passwords...")

            # 1. Reset Super Admin (Email)
            username_email = "smartdentalclinicapp@gmail.com"
            res = await db.execute(
                select(models.User).filter(models.User.username == username_email)
            )
            user = res.scalars().first()
            if user:
                new_hash = auth.get_password_hash("AdminPassword123!")
                user.hashed_password = new_hash
                await db.commit()
                print(f"Updated password for {username_email} (Hash: {new_hash[:10]}...)")
            else:
                print(f"User {username_email} not found.")

            # 2. Reset Default Admin (username)
            username_admin = "admin"
            res_admin = await db.execute(
                select(models.User).filter(models.User.username == username_admin)
            )
            user_admin = res_admin.scalars().first()
            if user_admin:
                new_hash_admin = auth.get_password_hash("admin1111")
                user_admin.hashed_password = new_hash_admin
                await db.commit()
                print(
                    f"Updated password for {username_admin} (Hash: {new_hash_admin[:10]}...)"
                )
            else:
                print(f"User {username_admin} not found.")

        except Exception as e:
            print(f"Error resetting passwords: {e}")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(reset_passwords())
