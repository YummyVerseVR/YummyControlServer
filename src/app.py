import asyncio
import uuid
import requests

from pydantic import BaseModel

from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse

from db.controller import DataBase
from qr.email import EmailSender
from qr.handler import QRHandler, RequestItem


class UserState(BaseModel):
    uuid: str
    is_ready: bool


class Request(BaseModel):
    email: str
    body: str


class App:
    def __init__(self, config: dict, debug_mode: bool = False):
        self.__db = DataBase(config.get("db", {}))
        self.__qr_handler = QRHandler()
        self.__email_sender = EmailSender(config.get("email", {}), debug_mode)

        self.__app = FastAPI()
        self.__router = APIRouter()
        self.__setup_routes()

    def __setup_routes(self):
        self.__router.add_api_route(
            "/set-status",
            self.set_status,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/request",
            self.request,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/list",
            self.list_db,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/ping",
            self.ping,
            methods=["GET"],
        )

    def get_app(self):
        self.__app.include_router(self.__router)
        return self.__app

    # /request
    async def request(self, request: Request) -> JSONResponse:
        generated_uuid = str(uuid.uuid4())
        qr_data, qr_image = self.__qr_handler.generate_qr(
            RequestItem(uuid=generated_uuid, request=request.body)
        )

        self.__db.add_user(generated_uuid)
        self.__db.load_qr(generated_uuid, qr_image)

        user = self.__db.get_user(generated_uuid)
        if user is None:
            return JSONResponse(
                content={"detail": "Failed to add user"}, status_code=500
            )

        user.meta.email = request.email
        user.meta.qr_code = qr_data
        user.meta.request = request.body
        user.save_meta()

        print("[INFO] New request registered")
        print(f"  email : {request.email}")
        print(f"  uuid : {generated_uuid}")
        print(f"  request : {request.body}")
        return JSONResponse(
            content={"detail": f"UUID:{generated_uuid}"}, status_code=200
        )

    # /set-status
    async def set_status(self, state: UserState) -> JSONResponse:
        if not self.__db.is_exist(state.uuid):
            print(f"now database: {self.__db}")
            return JSONResponse(content={"detail": "UUID not found"}, status_code=404)

        if not state.is_ready:
            self.__db.remove_user(state.uuid)
            return JSONResponse(
                content={"detail": "some thing wrong. please try again"},
                status_code=400,
            )

        user = self.__db.get_user(state.uuid)
        if user is None or user.meta.email == "" or user.meta.qr_code == "":
            return JSONResponse(
                content={"detail": "User data incomplete"}, status_code=500
            )

        to = user.meta.email
        qr_code = user.meta.qr_code
        asyncio.create_task(self.__email_sender.send_email(to, qr_code))
        return JSONResponse(content={"detail": "QR Code sent successfully"})

    # /list
    async def list_db(self) -> JSONResponse:
        users = self.__db.list_users()
        result = [
            {
                "uuid": user.get_uuid(),
                "email": user.meta.email,
                "request": user.meta.request,
                "has_qr": user.meta.qr_code != "",
            }
            for user in users
        ]
        return JSONResponse(content={"users": result}, status_code=200)

    # /ping
    async def ping(self) -> JSONResponse:
        return JSONResponse(content={"message": "pong"}, status_code=200)
