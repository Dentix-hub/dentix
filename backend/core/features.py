from functools import wraps
import inspect
from typing import Any, Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.services.feature_service import FeatureFlagService


def require_feature(feature_key: str):
    """
    Restrict an endpoint based on the tenant feature flag state.

    The decorated endpoint must receive `current_user` and `db` as FastAPI
    dependency arguments.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user: User = kwargs.get("current_user")
            db: Session = kwargs.get("db")

            if not user or not db:
                raise ValueError(
                    "require_feature decorator requires current_user and db to be in kwargs"
                )

            if user.role == "super_admin":
                result = func(*args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

            if not FeatureFlagService.is_feature_enabled(db, feature_key, user.tenant_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tenant does not have access to feature '{feature_key}'.",
                )

            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        return wrapper

    return decorator
