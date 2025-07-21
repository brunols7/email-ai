from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from starlette.config import Config
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select
import json

from app.db import engine
from app.models.category import Category
from app.models.linked_account import LinkedAccount
from app.tasks import process_emails_task_wrapper, set_sync_status

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
    { "name": "Job Opportunities", "description": "Any email about job opportunities, alerts from LinkedIn, Gupy, etc., or contact from recruiters." },
    { "name": "Invoices & Bills", "description": "Receipts, invoices, payment confirmations, and service charges." },
    { "name": "Promotions", "description": "Marketing emails, offers, store newsletters, and promotions." },
    { "name": "Social", "description": "Notifications from social networks like Facebook, Instagram, etc." },
    { "name": "Other", "description": "Any email that does not clearly fit into the other categories." }
]


@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri, access_type='offline', prompt='consent')

@router.get("/login/add-account")
async def add_account(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")
    
    redirect_uri = request.url_for("add_account_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri, access_type='offline', prompt='consent')

@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info: user_info = await oauth.google.parse_id_token(request, token)
        
        user_email = user_info.get("email")
        
        token_data_to_store = {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_at": token.get("expires_at"),
            "client_id": config("GOOGLE_CLIENT_ID"),
            "client_secret": config("GOOGLE_CLIENT_SECRET"),
            "token_uri": "https://oauth2.googleapis.com/token"
        }

        existing_account = session.exec(
            select(LinkedAccount).where(
                LinkedAccount.owner_email == user_email,
                LinkedAccount.is_primary == True
            )
        ).first()

        if existing_account:
            existing_account.token_data = json.dumps(token_data_to_store)
            print(f"Updated token for primary account: {user_email}")
        else:
            new_primary_account = LinkedAccount(
                owner_email=user_email,
                linked_email=user_email,
                token_data=json.dumps(token_data_to_store),
                is_primary=True
            )
            session.add(new_primary_account)
            print(f"Added new primary account to DB: {user_email}")
        
        user_session_data = { "email": user_email, "name": user_info.get("name"), "picture": user_info.get("picture"), }
        request.session["user"] = user_session_data
        request.session["token"] = token_data_to_store 

        existing_categories = session.exec(select(Category).where(Category.user_email == user_email)).first()
        if not existing_categories:
            print(f"New user detected: {user_email}. Creating default categories.")
            for cat_data in DEFAULT_CATEGORIES:
                new_cat = Category(name=cat_data["name"], description=cat_data["description"], user_email=user_email)
                session.add(new_cat)
            
            background_tasks.add_task(process_emails_task_wrapper, user_email, user_session_data, token_data_to_store)

        session.commit()
        return RedirectResponse(url="/dashboard")
    except Exception as e:
        print("AUTH ERROR:", e)
        return RedirectResponse(url="/")

@router.get("/auth/add-account-callback")
async def add_account_callback(request: Request, session: Session = Depends(get_session)):
    owner_user = request.session.get("user")
    if not owner_user:
        return RedirectResponse(url="/")

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info: user_info = await oauth.google.parse_id_token(request, token)
        
        linked_email = user_info.get("email")
        
        token_data_to_store = {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_at": token.get("expires_at"),
            "client_id": config("GOOGLE_CLIENT_ID"),
            "client_secret": config("GOOGLE_CLIENT_SECRET"),
            "token_uri": "https://oauth2.googleapis.com/token"
        }

        existing_account = session.exec(select(LinkedAccount).where(LinkedAccount.linked_email == linked_email)).first()
        if existing_account:
            existing_account.token_data = json.dumps(token_data_to_store)
            print(f"Updated token for linked account: {linked_email}")
        else:
            new_linked_account = LinkedAccount(
                owner_email=owner_user["email"],
                linked_email=linked_email,
                token_data=json.dumps(token_data_to_store)
            )
            session.add(new_linked_account)
            print(f"Added new linked account: {linked_email}")
        
        session.commit()
        return RedirectResponse(url="/dashboard")
    except Exception as e:
        print("ADD ACCOUNT ERROR:", e)
        return RedirectResponse(url="/dashboard")

@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    request.session.pop("token", None)
    return RedirectResponse(url="/")