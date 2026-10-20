"""Start the current project's Flask app with the existing local DB setting."""
from pathlib import Path
import sys
from init_dev_bank import credentials

credentials()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'backend'))
from app import app

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
