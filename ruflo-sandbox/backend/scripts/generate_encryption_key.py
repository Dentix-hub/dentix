#!/usr/bin/env python3
"""
Encryption Key Generator for Smart Clinic.

Usage:
    python scripts/generate_encryption_key.py

Output:
    Generates a new Fernet encryption key and displays usage instructions.
"""

from cryptography.fernet import Fernet
import secrets


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()


def generate_secret_key() -> str:
    """Generate a secure SECRET_KEY for JWT tokens."""
    return secrets.token_urlsafe(32)


def validate_key(key: str) -> bool:
    """Validate a Fernet encryption key."""
    try:
        Fernet(key.encode())
        return True
    except Exception:
        return False


def main():
    print("=" * 60)
    print("🔐 Smart Clinic - Security Key Generator")
    print("=" * 60)
    print()

    # Generate ENCRYPTION_KEY
    enc_key = generate_encryption_key()
    print("📋 ENCRYPTION_KEY (for data encryption):")
    print(f"   {enc_key}")
    print()

    # Generate SECRET_KEY
    secret_key = generate_secret_key()
    print("📋 SECRET_KEY (for JWT tokens):")
    print(f"   {secret_key}")
    print()

    print("=" * 60)
    print("📝 Usage Instructions:")
    print("=" * 60)
    print(
        """
1. Copy these keys to your production environment:
   
   For local development (.env file):
   ----------------------------------------
   ENCRYPTION_KEY={enc_key}
   SECRET_KEY={secret_key}
   
2. For production (Hugging Face Spaces, Vercel, etc.):
   - Go to your hosting dashboard
   - Add these as environment variables
   - NEVER commit real keys to Git!

3. Key Rotation (when needed):
   - Generate new ENCRYPTION_KEY
   - Run migration script to re-encrypt data
   - Update production environment
   
⚠️  WARNING: 
   - Keep these keys SECRET and SECURE
   - Backup keys securely (losing them = losing encrypted data)
   - Different keys for development vs production
""".format(enc_key=enc_key, secret_key=secret_key)
    )

    # Validate the generated key
    if validate_key(enc_key):
        print("✅ Generated ENCRYPTION_KEY is valid")
    else:
        print("❌ ERROR: Generated key validation failed!")


if __name__ == "__main__":
    main()
