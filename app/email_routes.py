from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
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

@router.get("/process-emails")
def process_emails_route(request: Request, session: Session = Depends(get_session)):
    user = request.session.get("user")
    token_data = request.session.get("token")
    if not user or not token_data:
        return RedirectResponse(url="/")

    user_categories = session.exec(
        select(Category).where(Category.user_email == user["email"])
    ).all()
    
    if not user_categories:
        return RedirectResponse(url="/categories")

    service = get_gmail_service(token_data)
    messages = list_messages(service, max_results=5) 

    category_map = {cat.name: cat for cat in user_categories}

    for msg_info in messages:
        msg_id = msg_info['id']
        
        existing_email = session.get(Email, msg_id)
        if existing_email:
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
            print(f"IA retornou categoria desconhecida: {chosen_category_name}")
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

    return RedirectResponse(url="/dashboard", status_code=303)