# SQLite 연결 코드 - data/app.db 파일을 SQLite DB로 사용

from pathlib import Path

from sqlmodel import create_engine


ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app.db"

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)