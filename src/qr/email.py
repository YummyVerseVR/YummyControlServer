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

from pylognet.client import LoggingClient, LogLevel


class EmailSender:
    TEST_QR_CODE = "iVBORw0KGgoAAAANSUhEUgAAADYAAAA2AQMAAAC2i/ieAAAABlBMVEX///8AAABVwtN+AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAeUlEQVQYlZXNMQoEMQiF4Qe2Aa8i2Aa8+oJtYK4SsB1wltlAnO3mb77KJ/AyyjDLIqQLFU2HxkP/sz2E5Lr/maFr//Ybr9e3dGp6FJlz8hZdO3JL07vxFqHaZhE05NhSzqNJESKsRZNIr2qz86F3FKEYUsz4eNu+7AJ7EFg5FDUcHwAAAABJRU5ErkJggg=="

    def __init__(
        self,
        config: dict,
        logger: LoggingClient,
        debug_mode: bool = False,
    ):
        self.__debug = debug_mode
        self.__logger = logger
        self.__config = config.get("email", {})
        self.__service = self.__get_service()

    def __get_service(self):
        if self.__debug:
            return None

        token_path = self.__config.get("token", "./settings/token.json")
        creds_path = self.__config.get("credentials", "./settings/credentials.json")
        scopes = self.__config.get(
            "scopes", ["https://www.googleapis.com/auth/gmail.send"]
        )
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def send_email(self, to: str, qr_code: str, uuid: str):
        if self.__debug or self.__service is None:
            return

        self.__logger.log(
            f"Sending email to {to} with QR code (base64): {qr_code[:30]}...",
            LogLevel.INFO,
        )

        message = MIMEMultipart()
        message["to"] = to
        message["from"] = "me"
        message["subject"] = "YummyVerseのQRコード"

        preview_base = self.__config.get("preview-link", "https://yummy-previewer.theunusuaru3.workers.dev/")
        preview_url = f"{preview_base}{uuid}"
        body_text = f"YummyVerseのQRコードをお送りします。アプリで読み取ってください。\n\nプレビューはこちら: {preview_url}"
        message.attach(MIMEText(body_text, "plain", "utf-8"))

        qr_data = base64.b64decode(qr_code)
        image = MIMEImage(qr_data, name="qr_code.png")
        image.add_header("Content-Disposition", "attachment", filename="qr_code.png")
        message.attach(image)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": encoded_message}

        try:
            _ = self.__service.users().messages().send(userId="me", body=body).execute()
            self.__logger.log(f"Email sent to {to} with QR code.", LogLevel.INFO)
        except Exception as e:
            self.__logger.log(f"Failed to send email to {to}: {e}", LogLevel.ERROR)
            raise HTTPException(status_code=500, detail=str(e))
