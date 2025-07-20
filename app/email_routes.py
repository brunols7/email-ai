from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
import json
import os

from app.db import engine
from app.gmail import get_gmail_service, list_messages, get_message_details, archive_email
from app.ai_utils import summarize_and_categorize_email
from app.models.category import Category
from app.models.email import Email
from app.models.linked_account import LinkedAccount

CRON_SECRET = os.getenv("CRON_SECRET")

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_session():
    with Session(engine) as session:
        yield session

def process_emails_task(owner_email: str, processing_user_info: dict, token_data: dict):
    print(f"Starting email processing for inbox {processing_user_info['email']} (owned by {owner_email})")
    
    with Session(engine) as session:
        user_categories = session.exec(select(Category).where(Category.user_email == owner_email)).all()
        
        if not user_categories:
            print(f"No categories found for owner {owner_email}. Task ending.")
            return
        
        service = get_gmail_service(token_data)
        messages = list_messages(service, max_results=10)
        category_map = {cat.name: cat for cat in user_categories}

        for msg_info in messages:
            msg_id = msg_info['id']
            existing_email = session.exec(select(Email).where(Email.id == msg_id, Email.user_email == owner_email)).first()
            if existing_email: continue
            
            details = get_message_details(service, msg_id)
            if not details: continue
            
            email_body_for_ai = details.get("body") or ""
            
            ai_result = summarize_and_categorize_email(email_body_for_ai, user_categories)
            if not ai_result: continue
            
            chosen_category_name = ai_result.get("category")
            summary = ai_result.get("summary")
            category_obj = category_map.get(chosen_category_name)
            if not category_obj: continue

            new_email = Email(
                id=details['id'],
                user_email=owner_email,
                summary=summary,
                category_id=category_obj.id,
                snippet=details['snippet'],
                sent_date=details['date'],
                from_address=details['from'],
                body=details.get("body") or ""
            )
            
            try:
                session.add(new_email)
                session.commit()
                archive_email(service, msg_id)
            except IntegrityError:
                print(f"Email {msg_id} was already processed. Skipping.")
                session.rollback()
                continue
    print(f"Email processing task for inbox {processing_user_info['email']} finished.")

@router.get("/process-emails")
def trigger_manual_process(request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    user = request.session.get("user")
    token_data = request.session.get("token")
    if not user or not token_data:
        return RedirectResponse(url="/")

    owner_email = user['email']

    print(f"Enfileirando processamento para a conta principal: {owner_email}")
    background_tasks.add_task(process_emails_task, owner_email, user, token_data)

    linked_accounts = session.exec(
        select(LinkedAccount).where(LinkedAccount.owner_email == owner_email)
    ).all()

    for acc in linked_accounts:
        print(f"Enfileirando processamento para a conta vinculada: {acc.linked_email}")
        
        linked_token_data = json.loads(acc.token_data)
        linked_user_info = {"email": acc.linked_email} 
        
        background_tasks.add_task(process_emails_task, owner_email, linked_user_info, linked_token_data)
    
    return RedirectResponse(url="/processing", status_code=303)

@router.get("/processing", response_class=HTMLResponse)
def processing_page(request: Request):
    user = request.session.get("user")
    if not user: return RedirectResponse(url="/")
    return templates.TemplateResponse("processing.html", {"request": request, "user": user})

@router.get("/emails/{email_id}", response_class=HTMLResponse)
def view_email(request: Request, email_id: str, session: Session = Depends(get_session)):
    user = request.session.get("user")
    if not user: return RedirectResponse(url="/")
    email = session.get(Email, email_id)
    if not email or email.user_email != user['email']:
        return RedirectResponse(url="/categories")
    return templates.TemplateResponse("email_detail.html", {"request": request, "email": email, "user": user})

router.post("/cron/sync-all/{secret}")
async def trigger_cron_sync_all(secret: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    if not CRON_SECRET or secret != CRON_SECRET:
        print("CRON JOB: Unauthorized attempt.")
        return {"detail": "Not authorized"}

    print("CRON JOB: Starting sync for all accounts.")
    
    all_accounts = session.exec(select(LinkedAccount)).all()
    
    if not all_accounts:
        print("CRON JOB: No accounts found in the database to sync.")
        return {"status": "No accounts to sync."}

    for account in all_accounts:
        owner_email = account.owner_email
        processing_email = account.linked_email
        
        print(f"CRON JOB: Queuing task for inbox {processing_email} (owned by {owner_email})")
        
        token_data = json.loads(account.token_data)
        processing_user_info = {"email": processing_email}
        
        background_tasks.add_task(process_emails_task, owner_email, processing_user_info, token_data)

    print(f"CRON JOB: Finished queuing {len(all_accounts)} tasks.")
    return {"status": f"Queued {len(all_accounts)} sync tasks."}