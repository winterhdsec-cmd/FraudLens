"""Database transaction control for FraudLens."""
from contextlib import contextmanager
from database import db


@contextmanager
def transactional():
    """Wrap database operations in a transaction with auto rollback on error."""
    try:
        yield
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise