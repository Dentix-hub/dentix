import base64
import os

# Definition paths
frontend_assets = os.path.join("frontend", "src", "assets")
avatar_png_path = os.path.join(frontend_assets, "dental_ai_avatar.png")
avatar_js_path = os.path.join(frontend_assets, "dentalAiAvatarBase64.js")


def process_avatar():
    print("--- Processing Avatar (No PIL) ---")
    if not os.path.exists(avatar_png_path):
        print(f"Warning: {avatar_png_path} not found. Skipping.")
        return

    with open(avatar_png_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    js_content = f'export const dentalAiAvatarBase64 = "data:image/png;base64,{encoded_string}";\n'

    with open(avatar_js_path, "w", encoding="utf-8") as js_file:
        js_file.write(js_content)

    print(f"Avatar JS created at {avatar_js_path}")


if __name__ == "__main__":
    try:
        process_avatar()
        print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}")
