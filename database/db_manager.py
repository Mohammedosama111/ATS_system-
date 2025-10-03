from sqlalchemy import create_engine
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

# Compatibility for imports
Engine = None
SessionLocal = _Session
