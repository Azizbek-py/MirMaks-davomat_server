from pathlib import Path
from tinydb import TinyDB, Query
from .config import DB_PATH

db_path = Path(DB_PATH)
db_path.parent.mkdir(parents=True, exist_ok=True)
_db = TinyDB(db_path)

employees_table = _db.table("employees")
attendance_table = _db.table("attendance")
settings_table = _db.table("settings")

Query = Query
