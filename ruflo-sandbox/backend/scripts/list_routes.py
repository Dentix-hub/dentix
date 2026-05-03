def list_routes():
    from backend.main import app
    print(f"{'PATH':<50} | {'METHODS':<20} | {'NAME'}")
    print("-" * 90)
    for route in app.routes:
        methods = ", ".join(getattr(route, 'methods', ['MOUNT']))
        print(f"{route.path:<50} | {methods:<20} | {route.name}")

if __name__ == "__main__":
    list_routes()
