import time
from sqlmodel import Session, select
from google.api_core.exceptions import ResourceExhausted
from sqlalchemy.exc import IntegrityError

from app.db import engine
from app.gmail import get_gmail_service, list_messages, get_message_details, archive_email
from app.ai_utils import summarize_and_categorize_email
from app.models.category import Category
from app.models.email import Email
from app.models.sync_status import SyncStatus

def set_sync_status(owner_email: str, status: str, db_session: Session):
    status_obj = db_session.get(SyncStatus, owner_email)
    if status_obj:
        status_obj.status = status
    else:
        status_obj = SyncStatus(owner_email=owner_email, status=status)
        db_session.add(status_obj)
    db_session.commit()

def process_emails_task_logic(owner_email: str, processing_user_info: dict, token_data: dict):
    with Session(engine) as session:
        user_categories = session.exec(select(Category).where(Category.user_email == owner_email)).all()
        if not user_categories:
            set_sync_status(owner_email, 'completed', session)
            return
        
        service = get_gmail_service(token_data)
        messages = list_messages(service, max_results=10)
        if not messages:
            set_sync_status(owner_email, 'completed', session)
            return

        category_map = {cat.name: cat for cat in user_categories}

        for msg_info in messages:
            msg_id = msg_info['id']
            existing_email = session.exec(select(Email).where(Email.id == msg_id, Email.user_email == owner_email)).first()
            if existing_email: continue
            
            details = get_message_details(service, msg_id)
            if not details: continue
            
            email_body_for_ai = details.get("body") or ""
            
            time.sleep(2)

            ai_result = summarize_and_categorize_email(email_body_for_ai, user_categories)
            if not ai_result: continue
            
            chosen_category_name = ai_result.get("category")
            summary = ai_result.get("summary")
            category_obj = category_map.get(chosen_category_name)
            if not category_obj: continue

            new_email = Email(
                id=details['id'], user_email=owner_email, summary=summary,
                category_id=category_obj.id, snippet=details['snippet'],
                sent_date=details['date'], from_address=details['from'],
                body=details.get("body") or ""
            )
            
            try:
                session.add(new_email)
                session.commit()
                archive_email(service, msg_id)
            except IntegrityError:
                session.rollback()
                continue

def process_emails_task_wrapper(owner_email: str, processing_user_info: dict, token_data: dict):
    with Session(engine) as session:
        try:
            process_emails_task_logic(owner_email, processing_user_info, token_data)
            set_sync_status(owner_email, 'completed', session)
        except ResourceExhausted:
            print(f"Stopping task for {owner_email} due to rate limit.")
            set_sync_status(owner_email, 'rate_limit_exceeded', session)
        except Exception as e:
            print(f"An unexpected error occurred in background task for {owner_email}: {e}")
            set_sync_status(owner_email, 'failed', session)