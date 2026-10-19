"""Run an isolated SQLite demo without Docker; secrets remain in the ignored .env."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env")
(root / ".local").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + (root / ".local/demo.db").as_posix()
sys.path.insert(0, str(root / "backend"))
os.chdir(root / "backend")
from alembic.config import Config
from alembic import command
from app.db.seed import seed
import uvicorn

command.upgrade(Config("alembic.ini"), "head")
seed(demo=True)
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
