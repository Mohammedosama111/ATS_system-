from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from config.settings import settings

_engine = None
_Session = None

def init_db():
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(settings.database_url, echo=False, future=True)
        _Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _Session

def migrate_schema(engine):
    """Ensure new columns exist (lightweight auto-migration for SQLite)."""
    try:
        insp = inspect(engine)
        if not insp.has_table('decisions'):
            return
        cols = {c['name'] for c in insp.get_columns('decisions')}
        with engine.begin() as conn:
            if 'category' not in cols:
                conn.execute(text('ALTER TABLE decisions ADD COLUMN category VARCHAR(1)'))
            if 'match_score' not in cols:
                conn.execute(text('ALTER TABLE decisions ADD COLUMN match_score INTEGER'))
            # Usage table creation removed (token tracking disabled)
    except Exception as e:
        # Silent log fallback; in a larger app we would log properly
        print(f"[migrate_schema] Warning: {e}")

# Compatibility for imports
Engine = None
SessionLocal = _Session
