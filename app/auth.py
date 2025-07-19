from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.config import Config
from authlib.integrations.starlette_client import OAuth
import os

config = Config(".env")
router = APIRouter()
oauth = OAuth(config)

oauth.register(
    name='google',
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify'
    }
)

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)

        user_info = token.get("userinfo")
        if not user_info:
            user_info = await oauth.google.parse_id_token(request, token)

        request.session["user"] = {
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }
        request.session["token"] = {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_at": token.get("expires_at"),
            "client_id": config("GOOGLE_CLIENT_ID"),
            "client_secret": config("GOOGLE_CLIENT_SECRET")
        }

        return RedirectResponse(url="/dashboard")

    except Exception as e:
        print("AUTH ERROR:", e)
        return RedirectResponse(url="/")

@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")