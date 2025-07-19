from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict
import base64

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

def get_gmail_service(token_data):
    credentials = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=['openid', 'email', 'profile', 'https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
    )
    service = build("gmail", "v1", credentials=credentials)
    return service

def list_messages(service, user_id="me", max_results=10) -> List[Dict]:
    try:
        response = service.users().messages().list(
            userId=user_id,
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()

        messages = response.get("messages", [])
        return messages
    except HttpError as e:
        print(f"Erro ao listar mensagens: {e}")
        return []

def get_message_details(service, msg_id: str, user_id="me") -> Dict:
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()
        
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        body = ""

        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
        from_address = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)

        if "parts" in payload:
            for part in payload["parts"]:
                if part['mimeType'] == 'text/plain':
                    data = part.get("body", {}).get("data")
                    if data:
                        body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        break
        else:
            data = payload.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        
        return {
            "id": message['id'],
            "snippet": message['snippet'],
            "body": body,
            "date": date,
            "from": from_address
        }

    except HttpError as e:
        print(f"Erro ao buscar detalhes da mensagem {msg_id}: {e}")
        return None
    
def archive_email(service, msg_id: str, user_id="me"):
    try:
        body = {"removeLabelIds": ["INBOX"]}
        service.users().messages().modify(userId=user_id, id=msg_id, body=body).execute()
        print(f"E-mail {msg_id} arquivado com sucesso.")
    except HttpError as e:
        print(f"Erro ao arquivar e-mail {msg_id}: {e}")

def batch_delete_emails(service, email_ids: List[str], user_id="me"):
    if not email_ids:
        return
    try:
        body = {"ids": email_ids}
        service.users().messages().batchDelete(userId=user_id, body=body).execute()
    except HttpError as e:
        print(f"Error deleting emails: {e}")