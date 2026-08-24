import os

HOST = "0.0.0.0"
PORT = 8080
DEBUG = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "server.db")

BEACON_TIMEOUT = 180
