"""
run.py — Development server entry point.

    python seed.py     # create the database with sample data (run once)
    python run.py       # start the app at http://127.0.0.1:5000

Reads the PORT environment variable (falling back to 5000) instead of
hardcoding the port, so a dev-tooling launcher can assign a free port
when 5000 is already taken by something else.
"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
