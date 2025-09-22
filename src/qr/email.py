import base64
import os

from fastapi import HTTPException

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class EmailSender:
    TEST_QR_CODE = "iVBORw0KGgoAAAANSUhEUgAAADYAAAA2AQMAAAC2i/ieAAAABlBMVEX///8AAABVwtN+AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAeUlEQVQYlZXNMQoEMQiF4Qe2Aa8i2Aa8+oJtYK4SsB1wltlAnO3mb77KJ/AyyjDLIqQLFU2HxkP/sz2E5Lr/maFr//Ybr9e3dGp6FJlz8hZdO3JL07vxFqHaZhE05NhSzqNJESKsRZNIr2qz86F3FKEYUsz4eNu+7AJ7EFg5FDUcHwAAAABJRU5ErkJggg=="

    def __init__(self, config: dict, debug_mode: bool = False):
        self.__debug = debug_mode
        self.__config = config.get("email", {})
        self.__service = self.__get_service()

    def __get_service(self):
        if self.__debug:
            return None

        creds_path = self.__config.get("token", "./settings/token.json")
        token_path = self.__config.get("credentials", "./settings/credentials.json")
        scopes = self.__config.get(
            "scopes", ["https://www.googleapis.com/auth/gmail.send"]
        )
        creds = None
        if os.path.exists(creds_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(token_path, scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    async def send_email(self, to: str, qr_code: str):
        if self.__debug or self.__service is None:
            return

        print("[INFO] Sending email...")
        print(f"  To: {to}")
        print(f"  QR Code (base64): {qr_code[:30]}...")

        message = MIMEMultipart()
        message["to"] = to
        message["from"] = "me"
        message["subject"] = "YummyVerseのQRコード"

        body_text = "YummyVerseのQRコードをお送りします。アプリで読み取ってください。"
        message.attach(MIMEText(body_text, "plain", "utf-8"))

        qr_data = base64.b64decode(qr_code)
        image = MIMEImage(qr_data, name="qr_code.png")
        image.add_header("Content-Disposition", "attachment", filename="qr_code.png")
        message.attach(image)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": encoded_message}

        try:
            sent = (
                self.__service.users().messages().send(userId="me", body=body).execute()
            )
            print(f"ID: {sent['id']}")
        except Exception as e:
            print(f"error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
