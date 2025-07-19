from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from starlette.config import Config
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select

from app.db import engine
from app.models.category import Category
from app.email_routes import process_emails_task

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

def get_session():
    with Session(engine) as session:
        yield session

DEFAULT_CATEGORIES = [
    {
        "name": "Job Opportunities",
        "description": "Any email about job opportunities, alerts from LinkedIn, Gupy, etc., or contact from recruiters."
    },
    {
        "name": "Invoices & Bills",
        "description": "Receipts, invoices, payment confirmations, and service charges."
    },
    {
        "name": "Promotions",
        "description": "Marketing emails, offers, store newsletters, and promotions."
    },
    {
        "name": "Social",
        "description": "Notifications from social networks like Facebook, Instagram, etc."
    },
    {
        "name": "Other",
        "description": "Any email that does not clearly fit into the other categories."
    }
]

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    try:
        token = await oauth.google.authorize_access_token(request)

        user_info = token.get("userinfo")
        if not user_info:
            user_info = await oauth.google.parse_id_token(request, token)

        user_email = user_info.get("email")
        
        user_session_data = {
            "email": user_email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }
        token_session_data = {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_at": token.get("expires_at"),
            "client_id": config("GOOGLE_CLIENT_ID"),
            "client_secret": config("GOOGLE_CLIENT_SECRET")
        }

        request.session["user"] = user_session_data
        request.session["token"] = token_session_data

        existing_categories = session.exec(
            select(Category).where(Category.user_email == user_email)
        ).first()

        if not existing_categories:
            for cat_data in DEFAULT_CATEGORIES:
                new_cat = Category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    user_email=user_email
                )
                session.add(new_cat)
            session.commit()
            
            background_tasks.add_task(process_emails_task, user_session_data, token_session_data)

        return RedirectResponse(url="/dashboard")

    except Exception as e:
        print("AUTH ERROR:", e)
        return RedirectResponse(url="/")

@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")
