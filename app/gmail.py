from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict
import base64

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
            userId=user_id, maxResults=max_results, labelIds=['INBOX']
        ).execute()
        return response.get("messages", [])
    except HttpError as e:
        print(f"Error listing messages: {e}")
        return []

def get_message_details(service, msg_id: str, user_id="me") -> Dict:
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()
        
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        
        body_html = ""
        body_plain = ""

        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
        from_address = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)

        def decode_part(part):
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            return ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part['mimeType'] == 'text/html':
                    body_html = decode_part(part)
                elif part['mimeType'] == 'text/plain':
                    body_plain = decode_part(part)
        else:
            body_plain = decode_part(payload)
        
        final_body = body_html if body_html else body_plain
        
        return {
            "id": message['id'],
            "snippet": message['snippet'],
            "body": final_body, 
            "date": date,
            "from": from_address
        }
    except HttpError as e:
        print(f"Error fetching message details for {msg_id}: {e}")
        return None
    
def archive_email(service, msg_id: str, user_id="me"):
    try:
        body = {"removeLabelIds": ["INBOX"]}
        service.users().messages().modify(userId=user_id, id=msg_id, body=body).execute()
        print(f"Email {msg_id} archived successfully.")
    except HttpError as e:
        print(f"Error archiving email {msg_id}: {e}")

def batch_delete_emails(service, email_ids: List[str], user_id="me"):
    if not email_ids:
        return
    try:
        body = {"ids": email_ids}
        service.users().messages().batchDelete(userId=user_id, body=body).execute()
        print(f"{len(email_ids)} emails successfully deleted from Gmail.")
    except HttpError as e:
        print(f"Error batch deleting emails: {e}")