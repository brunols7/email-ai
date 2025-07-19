from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List

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
        scopes=SCOPES
    )
    service = build("gmail", "v1", credentials=credentials)
    return service

def list_messages(service, user_id="me", max_results=10) -> List[str]:
    try:
        response = service.users().messages().list(userId=user_id, maxResults=max_results).execute()

        messages = response.get("messages")
        if not messages:
            return []

        return [msg["id"] for msg in messages]
    except HttpError as e:
        content = e.content.decode("utf-8") if e.content else "No content"
        raise

def get_message_content(service, msg_id: str, user_id="me") -> str:
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()
    except HttpError as e:
        content = e.content.decode("utf-8") if e.content else "No content"
        raise

    payload = message.get("payload", {})
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            data = part.get("body", {}).get("data")
            if data:
                import base64
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                body += decoded
    else:
        data = payload.get("body", {}).get("data")
        if data:
            import base64
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            body += decoded

    return body