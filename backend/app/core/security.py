from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.models import Customer


def require_customer_auth() -> Customer:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Customer authentication is not configured.",
        headers={"WWW-Authenticate": "Bearer"},
    )


CustomerAuth = Annotated[Customer, Depends(require_customer_auth)]
