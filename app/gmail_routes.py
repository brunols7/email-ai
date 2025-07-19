from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.gmail import get_gmail_service, list_messages, get_message_content
from googleapiclient.errors import HttpError
import traceback
from app.openai_utils import summarize_email

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/emails", response_class=HTMLResponse)
async def read_emails(request: Request):
    user = request.session.get("user")
    token_data = request.session.get("token")

    if not token_data:
        return RedirectResponse(url="/")

    try:
        service = get_gmail_service(token_data)
        message_ids = list_messages(service, max_results=5)

        if not message_ids:
            return templates.TemplateResponse("emails.html", {
                "request": request,
                "user": user,
                "emails": [],
                "message": "Nenhum e-mail encontrado."
            })

        emails = []
        for msg_id in message_ids:
            try:
                body = get_message_content(service, msg_id)
                result = summarize_and_categorize_email(body)
                
                emails.append({
                    "id": msg_id,
                    "summary": result["summary"],
                    "category": result["category"],
                })
            except Exception as e:
                continue

        return templates.TemplateResponse("emails.html", {
            "request": request,
            "user": user,
            "emails": emails,
            "message": None
        })

    except HttpError as e:
        content = e.content.decode("utf-8") if e.content else "Sem conteúdo"
        tb = traceback.format_exc()
        return HTMLResponse(
            content=f"""
                <h1>Erro da API do Gmail (status {e.resp.status})</h1>
                <h2>Detalhes:</h2>
                <pre>{content}</pre>
                <hr>
                <h2>Traceback:</h2>
                <pre>{tb}</pre>
            """,
            status_code=e.resp.status
        )

    except Exception as e:
        tb = traceback.format_exc()
        return HTMLResponse(
            content=f"""
                <h1>Erro Interno no Servidor</h1>
                <h2>Detalhes:</h2>
                <pre>{str(e)}</pre>
                <hr>
                <h2>Traceback:</h2>
                <pre>{tb}</pre>
            """,
            status_code=500
        )