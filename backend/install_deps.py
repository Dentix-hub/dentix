import sys
import subprocess

def install():
    print(f"Installing cloudinary to {sys.executable}")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cloudinary'])
    print("Installation complete.")

if __name__ == "__main__":
    install()
