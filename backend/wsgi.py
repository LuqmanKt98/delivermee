# WSGI entry point for Vercel deployment
# Updated: 2026-05-02 - Debug Flask routing
import sys
print("=" * 50, file=sys.stderr)
print("WSGI: Starting Flask app initialization", file=sys.stderr)

from app import app

print(f"WSGI: App created: {app}", file=sys.stderr)
print(f"WSGI: App name: {app.name}", file=sys.stderr)
print(f"WSGI: Registered blueprints: {list(app.blueprints.keys())}", file=sys.stderr)
print(f"WSGI: URL map: {app.url_map}", file=sys.stderr)
print("=" * 50, file=sys.stderr)

# Vercel requires the app to be exposed at module level
application = app

if __name__ == "__main__":
    app.run()
