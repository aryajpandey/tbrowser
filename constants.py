import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


COMMANDS_JSON = BASE_DIR / "cmd_list" / "commands.json"

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history", "browser_history.json")