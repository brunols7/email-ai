from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.models.category import Category
from app.db import engine

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/categories")
def list_categories(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")

    with Session(engine) as session:
        results = session.exec(
            select(Category).where(Category.user_email == user["email"])
        ).all()

    return templates.TemplateResponse("categories.html", {
        "request": request,
        "categories": results,
        "user": user
    })

@router.post("/categories")
def create_category(
    request: Request,
    name: str = Form(...),
    description: str = Form("")
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")

    new_cat = Category(name=name, description=description, user_email=user["email"])
    with Session(engine) as session:
        session.add(new_cat)
        session.commit()

    return RedirectResponse(url="/categories", status_code=303)
