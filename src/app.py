import smtplib
import uuid
from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate
import base64
import os
from typing import NamedTuple
import requests
from pydantic import BaseModel


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
    def __init__(self, qr_endpoint: str):
        self.__app = FastAPI()
        self.__router = APIRouter()
        self.__setup_routes()
        self.__setup_email()
        # とりあえず仮で辞書型を。処理途中でサーバ落ちたら終わる
        self.__db = {}
        self.__qr_endpoint = qr_endpoint

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

    def get_app(self):
        self.__app.include_router(self.__router)
        return self.__app

    def __setup_email(self):
        load_dotenv()
        self.from_email = os.getenv("FROM_EMAIL")
        self.app_password = os.getenv("APP_PASSWORD")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465

    # async def periodic_notify(self):
    #     while True:
    #         await asyncio.sleep(10) # 10秒ごとに実行
    #         await self.notify_user()

    async def read_root(self):
        return {"detail": "A Control Server"}

    # /set-user-status
    async def set_user_status(self, item: UserState) -> JSONResponse:
        if item.uuid not in self.__db:
            print(f"now database: {self.__db}")
            return JSONResponse(content={"detail": "UUID not found"}, status_code=404)

        if not item.is_ready:
            self.__db.pop(item.uuid)
            return JSONResponse(
                content={"detail": "some thing wrong. please try again"},
                status_code=400,
            )

        await self.send_qr(item.uuid)
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
        r_post = requests.post(f"{self.__qr_endpoint}/gen-qr", json=item)
        if r_post.status_code != 201:
            print(f"Failed to generate QR code: {r_post.text}")
            return {"uuid": uuid, "qr_code": None}
        return {
            "uuid": r_post.json().get("uuid"),
            "qr_code": r_post.json().get("qr_code"),
        }

    async def send_qr(self, uuid: str):
        print(f"from: {self.from_email}")
        print(f"to: {self.__db[uuid]['email']}")
        print(f"QR Code (base64): {self.__db[uuid]['qr_code'][:30]}...")
        if not self.from_email or not self.app_password:
            raise HTTPException(
                status_code=500, detail="Email configuration is not set"
            )
        if uuid not in self.__db:
            raise HTTPException(status_code=404, detail="UUID not found")

        try:
            msg = MIMEMultipart()
            msg["From"] = formataddr(("YummyVerse[開発用]", self.from_email))
            msg["Subject"] = "YummyVerseのQRコード"
            msg["Date"] = formatdate(localtime=True)
            msg["To"] = self.__db[uuid]["email"]

            body = MIMEText(
                "YummyVerseのQRコードをお送りします。アプリで読み取ってください。",
                "plain",
            )
            msg.attach(body)

            attachment = MIMEApplication(base64.b64decode(self.__db[uuid]["qr_code"]))
            file_name = f"YummyVerse_QR_{uuid}.png"
            attachment.add_header(
                "Content-Disposition", "attachment", filename=file_name
            )
            msg.attach(attachment)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.from_email, self.app_password)
                server.send_message(msg)
            return {"detail": "QR code sent successfully"}
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
