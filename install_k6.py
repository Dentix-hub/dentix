import urllib.request
import zipfile
import os

url = "https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-windows-amd64.zip"
zip_path = "k6.zip"
extract_folder = "k6_tool"

print(f"Downloading k6 from {url}...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_folder)

# Find the exe
k6_exe_path = os.path.join(os.getcwd(), extract_folder, "k6-v0.47.0-windows-amd64", "k6.exe")
target_path = os.path.join(os.getcwd(), "k6.exe")

if os.path.exists(k6_exe_path):
    os.rename(k6_exe_path, target_path)
    print(f"✅ k6.exe ready at {target_path}")
else:
    print("❌ Could not find k6.exe after extraction")
