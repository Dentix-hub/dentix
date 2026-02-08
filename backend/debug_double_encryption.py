
import os
import sys
from cryptography.fernet import Fernet

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.security import EncryptionManager

def test_double_encryption():
    print("--- Testing Double Encryption Scenario ---")

    # 1. Simulate data encrypted with an OLD key (now lost)
    old_key = Fernet.generate_key().decode()
    old_cipher = Fernet(old_key)
    original_phone = "0123456789"
    
    # This is what stored in DB currently
    encrypted_with_lost_key = old_cipher.encrypt(original_phone.encode()).decode()
    print(f"1. Data encrypted with LOST key: {encrypted_with_lost_key[:20]}...")

    # 2. Initialize Manager with CURRENT key
    current_key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = current_key
    manager = EncryptionManager(key=current_key)
    print(f"2. Current Key initialized: {current_key[:10]}...")

    # 3. Simulate READ (process_result_value)
    # This simulates fetching the patient. The decrypt should fail (keys mismatch).
    # The fallback should return the raw ciphertext.
    
    try:
        decrypted_view = manager.decrypt(encrypted_with_lost_key, allow_plaintext_fallback=True)
        print(f"3. Decrypt result (Fallback active?): {decrypted_view[:20]}...")
    except Exception as e:
        print(f"3. Decrypt CRASHED: {e}")
        return

    # Check if we got the ciphertext back
    if decrypted_view == encrypted_with_lost_key:
        print("   [CONFIRMED] Fallback returned raw ciphertext.")
    else:
        print("   [UNEXPECTED] Decrypt returned something else?")

    # 4. Simulate UPDATE (process_bind_param)
    # User sees the ciphertext in the input field (garbage), leaves it there, and saves.
    # The frontend sends 'decrypted_view' back to the API.
    
    new_input = decrypted_view # The garbage string
    re_encrypted = manager.encrypt(new_input)
    
    print(f"4. Re-encryption (Save): {re_encrypted[:20]}...")
    
    if len(re_encrypted) > len(encrypted_with_lost_key):
        print("   [CONFIRMED] Data grew in size (Double Encryption!).")
        
    # 5. Simulate NEXT READ
    # Now we try to read this new record with the CURRENT key.
    # It should decrypt to the... ciphertext from step 1.
    
    re_decrypted = manager.decrypt(re_encrypted)
    print(f"5. Read after update: {re_decrypted[:20]}...")
    
    if re_decrypted == encrypted_with_lost_key:
        print("   [RESULT] Success! We retrieved the 'garbage' ciphertext.")
        print("   This confirms the cycle: Lost Key -> Read Ciphertext -> Save -> Double Encrypt.")
    else:
        print("   [FAILED] Could not reproduce exact cycle.")

if __name__ == "__main__":
    test_double_encryption()
