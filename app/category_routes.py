from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import List
import asyncio

from app.models.category import Category
from app.models.email import Email
from app.db import engine
from app.email_routes import process_emails_task
from app.gmail import get_gmail_service, batch_delete_emails
from app.gmail import get_gmail_service, batch_delete_emails
from app.ai_utils import find_unsubscribe_link
from app.ai_utils import find_unsubscribe_link, agent_unsubscribe_from_link


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/categories")
def list_categories(
    request: Request,
    session: Session = Depends(get_session)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")

    categories = session.exec(
        select(Category).where(Category.user_email == user["email"])
    ).all()

    return templates.TemplateResponse("categories.html", {
        "request": request, "categories": categories, "user": user
    })

@router.post("/categories")
def create_category(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    description: str = Form(""),
    session: Session = Depends(get_session)
):
    user = request.session.get("user")
    token_data = request.session.get("token")
    if not user:
        return RedirectResponse(url="/")

    new_cat = Category(name=name, description=description, user_email=user["email"])
    session.add(new_cat)
    session.commit()

    background_tasks.add_task(process_emails_task, user, token_data)

    return RedirectResponse(url="/processing", status_code=303)

@router.get("/categories/{category_id}")
def get_category_details(request: Request, category_id: str, session: Session = Depends(get_session)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")

    category = session.get(Category, category_id)
    if not category or category.user_email != user['email']:
        return RedirectResponse(url="/categories")

    return templates.TemplateResponse("category_detail.html", {
        "request": request, "category": category, "user": user
    })

@router.post("/categories/{category_id}/batch-action")
async def handle_batch_action(
    request: Request,
    category_id: str,
    action: str = Form(...),
    email_ids: List[str] = Form(...),
    session: Session = Depends(get_session)
):
    user = request.session.get("user")
    token_data = request.session.get("token")
    if not user or not token_data:
        return RedirectResponse(url="/")

    if action == "delete":
        service = get_gmail_service(token_data)
        batch_delete_emails(service, email_ids)

        for email_id in email_ids:
            email_to_delete = session.get(Email, email_id)
            if email_to_delete and email_to_delete.user_email == user['email']:
                session.delete(email_to_delete)
        
        session.commit()
        print(f"{len(email_ids)} emails successfully deleted.")
        return RedirectResponse(url=f"/categories/{category_id}", status_code=303)

    elif action == "unsubscribe":
        unsubscribe_tasks = []
        for email_id in email_ids:
            email = session.get(Email, email_id)
            if email and email.user_email == user['email']:
                link = find_unsubscribe_link(email.body) 
                if link and link != "None":
                    unsubscribe_tasks.append(agent_unsubscribe_from_link(link))
        
        results = await asyncio.gather(*unsubscribe_tasks)
        
        request.session["unsubscribe_results"] = results
        return RedirectResponse(url="/unsubscribe-results", status_code=303)

    return RedirectResponse(url=f"/categories/{category_id}", status_code=303)

@router.get("/unsubscribe-results")
def unsubscribe_results(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")
    
    links = request.session.pop("unsubscribe_links", [])
    return templates.TemplateResponse("unsubscribe_results.html", {"request": request, "links": links})
