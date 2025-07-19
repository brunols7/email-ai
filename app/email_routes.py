from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.db import engine
from app.gmail import get_gmail_service, list_messages, get_message_details, archive_email
from app.ai_utils import summarize_and_categorize_email
from app.models.category import Category
from app.models.email import Email

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_session():
    with Session(engine) as session:
        yield session

def process_emails_task(user: dict, token_data: dict):
    with Session(engine) as session:
        user_categories = session.exec(
            select(Category).where(Category.user_email == user["email"])
        ).all()
        
        if not user_categories:
            print(f"No category found for {user['email']}. The task will be terminated.")
            return

        service = get_gmail_service(token_data)
        messages = list_messages(service, max_results=10)

        category_map = {cat.name: cat for cat in user_categories}

        for msg_info in messages:
            msg_id = msg_info['id']
            
            if session.get(Email, msg_id):
                continue

            details = get_message_details(service, msg_id)
            if not details or not details['body']:
                continue
            
            ai_result = summarize_and_categorize_email(details['body'], user_categories)
            if not ai_result:
                continue
            
            chosen_category_name = ai_result.get("category")
            summary = ai_result.get("summary")
            
            category_obj = category_map.get(chosen_category_name)
            if not category_obj:
                continue

            new_email = Email(
                id=details['id'],
                user_email=user['email'],
                summary=summary,
                category_id=category_obj.id,
                snippet=details['snippet'],
                sent_date=details['date'],
                from_address=details['from']
            )
            
            try:
                session.add(new_email)
                session.commit()
                archive_email(service, msg_id)
            except IntegrityError:
                session.rollback()
                continue


@router.get("/process-emails")
def trigger_manual_process(
    request: Request,
    background_tasks: BackgroundTasks
):
    user = request.session.get("user")
    token_data = request.session.get("token")
    if not user or not token_data:
        return RedirectResponse(url="/")

    background_tasks.add_task(process_emails_task, user, token_data)
    
    return RedirectResponse(url="/processing", status_code=303)

@router.get("/processing", response_class=HTMLResponse)
def processing_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("processing.html", {"request": request, "user": user})

    