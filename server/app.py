import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from flask import Flask
from flask_cors import CORS
import config
import db
from routes import beacon_bp, register_ui

def create_app():
    app = Flask(__name__)
    CORS(app)
    db.init_db()
    app.register_blueprint(beacon_bp)
    register_ui(app)
    return app


if __name__ == "__main__":
    app = create_app()

    print("=" * 60)
    print("  C2 SERVER")
    print(f"  Listening on http://{config.HOST}:{config.PORT}")
    print(f"  Database: {config.DB_PATH}")
    print("=" * 60)
    print("  Waiting for beacons...\n")

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
