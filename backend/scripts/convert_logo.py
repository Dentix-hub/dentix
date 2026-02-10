import base64
import os

# Define paths relative to project root
input_path = os.path.join("frontend", "src", "assets", "logo.png")
output_path = os.path.join("frontend", "src", "assets", "logoBase64.js")

print(f"Reading from: {os.path.abspath(input_path)}")

if not os.path.exists(input_path):
    print(f"Error: {input_path} not found")
    exit(1)

with open(input_path, "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

# Create JS file with export
js_content = (
    f"""export const logoBase64 = "data:image/png;base64,{encoded_string}";\n"""
)

with open(output_path, "w") as js_file:
    js_file.write(js_content)

print(
    f"Successfully created {output_path} with Base64 string length: {len(encoded_string)}"
)
