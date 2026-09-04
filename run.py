"""
run.py — Development server entry point.

    python seed.py     # create the database with sample data (run once)
    python run.py       # start the app at http://127.0.0.1:5000
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
