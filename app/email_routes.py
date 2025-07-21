from fastapi import APIRouter, Request, Depends, BackgroundTasks, JSONResponse
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
import json
import os

from app.db import engine
from app.models.email import Email
from app.models.linked_account import LinkedAccount
from app.models.sync_status import SyncStatus
from app.tasks import process_emails_task_wrapper, set_sync_status # <-- ALTERAÇÃO IMPORTANTE

CRON_SECRET = os.getenv("CRON_SECRET")

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/process-emails")
def trigger_manual_process(request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    user = request.session.get("user")
    token_data = request.session.get("token")
    if not user or not token_data:
        return RedirectResponse(url="/")

    owner_email = user['email']
    set_sync_status(owner_email, 'processing', session)

    background_tasks.add_task(process_emails_task_wrapper, owner_email, user, token_data)

    linked_accounts = session.exec(
        select(LinkedAccount).where(LinkedAccount.owner_email == owner_email, LinkedAccount.is_primary == False)
    ).all()
    for acc in linked_accounts:
        linked_token_data = json.loads(acc.token_data)
        linked_user_info = {"email": acc.linked_email} 
        background_tasks.add_task(process_emails_task_wrapper, owner_email, linked_user_info, linked_token_data)
    
    return RedirectResponse(url="/processing", status_code=303)

@router.get("/processing", response_class=HTMLResponse)
def processing_page(request: Request):
    user = request.session.get("user")
    if not user: return RedirectResponse(url="/")
    return templates.TemplateResponse("processing.html", {"request": request, "user": user})

@router.get("/sync-status")
def get_sync_status(request: Request, session: Session = Depends(get_session)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    owner_email = user['email']
    status_obj = session.get(SyncStatus, owner_email)
    
    if status_obj:
        return JSONResponse({"status": status_obj.status})
    
    return JSONResponse({"status": "idle"})

@router.get("/emails/{email_id}", response_class=HTMLResponse)
def view_email(request: Request, email_id: str, session: Session = Depends(get_session)):
    user = request.session.get("user")
    if not user: return RedirectResponse(url="/")
    email = session.get(Email, email_id)
    if not email or email.user_email != user['email']:
        return RedirectResponse(url="/categories")
    return templates.TemplateResponse("email_detail.html", {"request": request, "email": email, "user": user})

@router.post("/cron/sync-all/{secret}")
async def trigger_cron_sync_all(secret: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    if not CRON_SECRET or secret != CRON_SECRET:
        return {"detail": "Not authorized"}

    all_accounts = session.exec(select(LinkedAccount)).all()
    for account in all_accounts:
        owner_email = account.owner_email
        set_sync_status(owner_email, 'processing', session)
        
        processing_email = account.linked_email
        token_data = json.loads(account.token_data)
        processing_user_info = {"email": processing_email}
        
        background_tasks.add_task(process_emails_task_wrapper, owner_email, processing_user_info, token_data)

    return {"status": f"Queued {len(all_accounts)} sync tasks."}