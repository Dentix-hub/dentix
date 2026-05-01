import hashlib

def generate_license_key(machine_id):
    """Generate a license key based on the machine ID."""
    hash_obj = hashlib.sha256((machine_id.strip() + "DENTIX_SECRET_KEY").encode())
    hash_hex = hash_obj.hexdigest().upper()
    return f"{hash_hex[:4]}-{hash_hex[4:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}"

if __name__ == "__main__":
    print("=======================================")
    print("DENTIX License Key Generator (Admin)")
    print("=======================================")
    client_hwid = input("Enter the Machine ID (HWID) from the client: ").strip()
    
    if client_hwid:
        key = generate_license_key(client_hwid)
        print("\n---------------------------------------")
        print(f"HWID: {client_hwid}")
        print(f"Activation Key: {key}")
        print("---------------------------------------")
        print("Send this Activation Key to the client.")
    else:
        print("No HWID entered.")

    print("\n=======================================")
    input("Press ENTER to exit...")
