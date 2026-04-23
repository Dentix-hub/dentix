from backend.main import app
for route in app.routes:
    methods = getattr(route, 'methods', 'MOUNT')
    print(f"{route.path} | {methods} | {route.name}")
