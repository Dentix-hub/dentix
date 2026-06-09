import functools
from typing import Callable, Any
from sqlalchemy.orm import Session

def transactional(func: Callable) -> Callable:
    """
    Decorator that wraps a service method in a database transaction.
    It expects the first or second argument (or a kwarg) to be a SQLAlchemy Session object named 'db'.
    If the function succeeds, the transaction is committed.
    If an exception occurs, the transaction is rolled back and the exception is re-raised.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        db: Session = kwargs.get('db')
        if not db:
            for arg in args:
                if isinstance(arg, Session):
                    db = arg
                    break
        
        if not db:
            raise ValueError("A database session ('db') is required to use the @transactional decorator.")
            
        try:
            # We don't call db.begin() explicitly here as SQLAlchemy autocommits/begins based on usage,
            # but we define the explicit boundaries.
            result = func(*args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            raise e
            
    return wrapper

def with_transaction(db: Session):
    """Context manager for explicit transaction boundaries within a block of code."""
    class TransactionContext:
        def __enter__(self):
            return db
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                db.rollback()
            else:
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
    return TransactionContext()
