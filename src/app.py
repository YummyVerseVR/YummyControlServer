import uuid
from fastapi import FastAPI, APIRouter, HTTPException, status, Form
from fastapi.responses import JSONResponse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64
import os
from typing import NamedTuple
import requests
from pydantic import BaseModel

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TEST_QR_CODE = "iVBORw0KGgoAAAANSUhEUgAAADYAAAA2AQMAAAC2i/ieAAAABlBMVEX///8AAABVwtN+AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAeUlEQVQYlZXNMQoEMQiF4Qe2Aa8i2Aa8+oJtYK4SsB1wltlAnO3mb77KJ/AyyjDLIqQLFU2HxkP/sz2E5Lr/maFr//Ybr9e3dGp6FJlz8hZdO3JL07vxFqHaZhE05NhSzqNJESKsRZNIr2qz86F3FKEYUsz4eNu+7AJ7EFg5FDUcHwAAAABJRU5ErkJggg=="


class DbStruct(NamedTuple):
    email: str
    qr: str


class UserState(BaseModel):
    uuid: str
    is_ready: bool


class UserRequest(BaseModel):
    email: str
    request: str


class App:
    def __init__(self, qr_endpoint: str, debug: bool = False):
        self.__app = FastAPI()
        self.__router = APIRouter()
        self.__setup_routes()
        self.__setup_email()
        # とりあえず仮で辞書型を。処理途中でサーバ落ちたら終わる
        self.__db = {}
        self.__qr_endpoint = qr_endpoint
        self.__debug = debug

    def __setup_routes(self):
        self.__router.add_api_route(
            "/set-user-status",
            self.set_user_status,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.__router.add_api_route(
            "/register-request",
            self.register_request,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.__router.add_api_route(
            "/list",
            self.list_db,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.__router.add_api_route(
            "/ping",
            self.ping,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )

    def get_app(self):
        self.__app.include_router(self.__router)
        return self.__app

    def __setup_email(self):
        self.service = self.get_service()

    # async def periodic_notify(self):
    #     while True:
    #         await asyncio.sleep(10) # 10秒ごとに実行
    #         await self.notify_user()

    async def read_root(self):
        return {"detail": "A Control Server"}

    def get_service(self):
        """Gmail APIサービスを取得"""
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    # /set-user-status
    async def set_user_status(
        self, uuid: str = Form(...), is_ready: bool = Form(...)
    ) -> JSONResponse:
        if uuid not in self.__db:
            print(f"now database: {self.__db}")
            return JSONResponse(content={"detail": "UUID not found"}, status_code=404)

        if not is_ready:
            self.__db.pop(uuid)
            return JSONResponse(
                content={"detail": "some thing wrong. please try again"},
                status_code=400,
            )

        await self.send_qr(uuid)
        return JSONResponse(content={"detail": "QR Code sent successfully"})

    # /register-request
    async def register_request(self, item: UserRequest) -> JSONResponse:
        generated_uuid = str(uuid.uuid4())

        r = await self.request_gen_qr(generated_uuid, item.request)
        self.__db[r["uuid"]] = {
            "email": item.email,
            "qr_code": r["qr_code"],
            "request": item.request,
        }
        print(f"email : {item.email}")
        print(f"uuid : {generated_uuid}")
        print(f"request : {item.request}")
        if r["qr_code"] is None:
            return JSONResponse(
                content={"detail": "Failed to generate QR code"}, status_code=500
            )
        return JSONResponse(
            content={"detail": f"UUID:{generated_uuid}"}, status_code=200
        )

    async def request_gen_qr(self, uuid: str, request: str):
        item = {"uuid": uuid, "request": request}
        if self.__debug:
            print(f"DEBUG MODE: {item}")
            return {"uuid": uuid, "qr_code": TEST_QR_CODE}
        r_post = requests.post(f"{self.__qr_endpoint}/gen-qr", json=item)
        if r_post.status_code != 201:
            print(f"Failed to generate QR code: {r_post.text}")
            return {"uuid": uuid, "qr_code": None}
        return {
            "uuid": r_post.json().get("uuid"),
            "qr_code": r_post.json().get("qr_code"),
        }

    async def send_qr(self, uuid: str):
        print(f"to: {self.__db[uuid]['email']}")
        print(f"QR Code (base64): {self.__db[uuid]['qr_code'][:30]}...")

        message = MIMEMultipart()
        message["to"] = self.__db[uuid]["email"]
        message["from"] = "me"
        message["subject"] = "YummyVerseのQRコード"

        body_text = "YummyVerseのQRコードをお送りします。アプリで読み取ってください。"
        message.attach(MIMEText(body_text, "plain", "utf-8"))

        qr_data = base64.b64decode(self.__db[uuid]["qr_code"])
        image = MIMEImage(qr_data, name="qr_code.png")
        image.add_header("Content-Disposition", "attachment", filename="qr_code.png")
        message.attach(image)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": encoded_message}

        try:
            sent = (
                self.service.users().messages().send(userId="me", body=body).execute()
            )
            print(f"ID: {sent['id']}")
        except Exception as e:
            print(f"error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # /list
    def list_db(self) -> JSONResponse:
        return JSONResponse(
            content={
                "list": [
                    {"uuid": k, "request": v["request"]} for k, v in self.__db.items()
                ]
            }
        )

    # /ping
    async def ping(self) -> JSONResponse:
        return JSONResponse(content={"message": "pong"}, status_code=200)
