import smtplib
import string
import uuid
from fastapi import FastAPI, APIRouter, HTTPException, params, status
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
import httpx
from pydantic import BaseModel
import asyncio
class DbStruct(NamedTuple):
    email: str
    qr: str

class UserState(BaseModel):
    uuid: str
    is_ready: bool

class UserRequest(BaseModel):
    email: str
    request: str

DB_API_URL = "http://localhost:8000/"
QR_API_URL = "http://localhost:8001/"

class App:
    def __init__(self):
        self.app = FastAPI()
        self.router = APIRouter()
        self.__setup_routes()
        self.__setup_email()
        #とりあえず仮で辞書型を。処理途中でサーバ落ちたら終わる
        self.__db = {}
    
    def __setup_routes(self):
        self.router.add_api_route("/", self.read_root)
        self.router.add_api_route("/set-user-status", self.set_user_status, methods=["POST"], status_code=status.HTTP_200_OK)
        self.router.add_api_route("/register-request", self.register_request, methods=["POST"], status_code=status.HTTP_200_OK)

    def get_app(self):
        self.app.include_router(self.router)
        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self.periodic_notify())
        return self.app

    def __setup_email(self):
        load_dotenv()
        self.from_email = os.getenv("FROM_EMAIL")
        self.app_password = os.getenv("APP_PASSWORD")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465

    async def periodic_notify(self):
        while True:
            await asyncio.sleep(10) # 10秒ごとに実行
            await self.notify_user()

    async def read_root(self):
        return {"detail": "A Control Server"}

    #Database ServerからNotify Readyを受け取る
    async def set_user_status(self, item: UserState) -> JSONResponse:
        if item.uuid not in self.__db:
            print(f"now database: {self.__db}")
            return JSONResponse(content={"detail": "UUID not found"}, status_code=404)

        if not item.is_ready:
            self.__db.pop(item.uuid)
            return JSONResponse(content={"detail": "some thing wrong. please try again"}, status_code=400)

        await self.send_qr(item.uuid)
        return JSONResponse(content={"detail": "QR Code sent successfully"})

    #GAS ServerからSend requestを受け取る
    async def register_request(self, item: UserRequest) -> JSONResponse:
        #uuidを鍵としてemail, qrを保存
        generated_uuid = str(uuid.uuid4())

        r = await self.request_gen_qr(generated_uuid, item.request)
        self.__db[r["uuid"]] = {"email": item.email, "qr_code": r["qr_code"]}
        print(f"email : {item.email}")
        print(f"uuid : {generated_uuid}")
        print(f"request : {item.request}")
        if r["qr_code"] is None:
            return JSONResponse(content={"detail": "Failed to generate QR code"}, status_code=500)
        return JSONResponse(content={"detail": "User registered successfully"}, status_code=200)

    async def request_gen_qr(self, uuid: str, request: str):
        item = {
            "uuid": uuid,
            "request": request
        }
        # URLを適切に構築
        url = f"{QR_API_URL.rstrip('/')}/gen-qr"
        print(f"Requesting QR URL: {url}")
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r_post = await client.post(url, json=item)
        
        print(f"QR Response status: {r_post.status_code}")
        if r_post.status_code != 201:
            print(f"gen-qrとの接続に失敗しました: {r_post.status_code}, {r_post.text}")
            return {"uuid": uuid, "qr_code": None}
        return {"uuid": r_post.json().get("uuid"), "qr_code": r_post.json().get("qr_code")}

    async def send_qr(self, uuid: str):
        print(f"from: {self.from_email}")
        print(f"to: {self.__db[uuid]['email']}")
        print(f"QR Code (base64): {self.__db[uuid]['qr_code'][:30]}...")
        if not self.from_email or not self.app_password:
            raise HTTPException(status_code=500, detail="Email configuration is not set")
        if uuid not in self.__db:
            raise HTTPException(status_code=404, detail="UUID not found")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = formataddr(('YummyVerse[開発用]', self.from_email))
            msg['Subject'] = 'YummyVerseのQRコード'
            msg['Date'] = formatdate(localtime=True)
            msg['To'] = self.__db[uuid]["email"]

            body = MIMEText('YummyVerseのQRコードをお送りします。アプリで読み取ってください。', 'plain')
            msg.attach(body)

            attachment = MIMEApplication(base64.b64decode(self.__db[uuid]["qr_code"]))
            file_name = f"YummyVerse_QR_{uuid}.png"
            attachment.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(attachment)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.from_email, self.app_password)
                server.send_message(msg)
            return {"detail": "QR code sent successfully"}
        except Exception as e:
            print(f"error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def notify_user(self):
        for uuid in list(self.__db.keys()): 
            if await self.check_user_ready(uuid):
                print(f"User {uuid} is ready. Sending QR code...")
                await self.send_qr(uuid)
                self.__db.pop(uuid)
            else:
                print(f"User {uuid} is not ready yet.")

    async def check_user_ready(self, uuid: str) -> bool:
        try:
            params = {
                "user_id": uuid
            }
            headers = {
                "accept": "application/json"
            }
            # URLを適切に構築（スラッシュの重複を避ける）
            url = f"{DB_API_URL.rstrip('/')}/{uuid}/status"
            print(f"Requesting URL: {url}")
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=headers)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Response data: {data}, Tyepe: {type(data['status'])}")
                if data["status"] == True:
                    return True
                else:
                    return False
            else:
                print(f"Failed to fetch user status: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            print(f"Error checking user status: {e}")
            return False