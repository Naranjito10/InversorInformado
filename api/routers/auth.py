from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from api.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _get_user_by_email(email: str) -> dict | None:
    import httpx
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}&select=id,email,password_hash&limit=1"
    resp = httpx.get(url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    data = resp.json()
    if isinstance(data, list) and data:
        return data[0]
    return None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    email: str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = _get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    token = create_access_token(sub=user["email"])
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: str = Depends(get_current_user)):
    return MeResponse(email=current_user)
