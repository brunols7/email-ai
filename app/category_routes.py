from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.models.category import Category
from app.models.email import Email
from app.db import engine
from app.email_routes import process_emails_task

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
        "request": request,
        "categories": categories,
        "user": user
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

    return RedirectResponse(url="/categories", status_code=303)

@router.get("/categories/{category_id}")
def get_category_details(request: Request, category_id: str, session: Session = Depends(get_session)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")

    category = session.get(Category, category_id)
    if not category or category.user_email != user['email']:
        return RedirectResponse(url="/categories")

    return templates.TemplateResponse("category_detail.html", {
        "request": request,
        "category": category,
        "user": user
    })