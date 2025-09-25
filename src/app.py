import asyncio
import uuid
import os
import requests

from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, APIRouter, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse

from db.controller import DataBase
from llm.controller import LLMController, ResponseModel

from qr.email import EmailSender
from qr.handler import QRHandler, RequestItem


class UserRequest(BaseModel):
    email: str
    request: str


class App:
    def __init__(self, config: dict, debug_mode: bool = False):
        self.__db = DataBase(config, debug_mode)
        self.__llm = LLMController(config, debug_mode)
        self.__qr_handler = QRHandler(config, debug_mode)
        self.__email_sender = EmailSender(config.get("email", {}), debug_mode)

        self.__endpoints = config.get("endpoints", {})
        self.__audio_endpoint = self.__endpoints.get(
            "audio", "http://192.168.11.100:8001"
        )
        self.__model_endpoint = self.__endpoints.get(
            "model", "http://192.168.11.100:8002"
        )

        self.__executor = ThreadPoolExecutor()
        self.__app = FastAPI()
        self.__router = APIRouter()
        self.__setup_routes()

    def __del__(self):
        self.__executor.shutdown(True)

    def __setup_routes(self):
        self.__router.add_api_route(
            "/request",
            self.request,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/save/image",
            self.save_image,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/save/model",
            self.save_model,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/save/audio",
            self.save_audio,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/{user_id}/status",
            self.status,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/{user_id}/qr",
            self.get_qr,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/{user_id}/image",
            self.get_image,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/{user_id}/model",
            self.get_model,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/{user_id}/audio",
            self.get_audio,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/{user_id}/param",
            self.get_param,
            methods=["GET"],
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

    async def __send_email(self, user_id: str) -> JSONResponse:
        if not self.__db.is_exist(user_id):
            return JSONResponse(content={"detail": "UUID not found"}, status_code=404)

        user = self.__db.get_user(user_id)
        if user is None or not user.meta.email or not user.meta.qr_code:
            return JSONResponse(
                content={"detail": "User data incomplete"}, status_code=500
            )

        to = user.meta.email
        qr_code = user.meta.qr_code
        self.__executor.submit(self.__email_sender.send_email, to, qr_code)
        return JSONResponse(content={"detail": "QR Code sent successfully"})

    async def __call_llm(self, request: str) -> ResponseModel:
        print("[INFO] Calling LLM...")
        llm_response = await self.__llm.choose_dish(request)
        return llm_response

    def __generate_model(self, user_id: str, request: str) -> None:
        print("[INFO] Calling model generator...")
        data = {
            "user_id": user_id,
            "prompt": request,
        }

        try:
            requests.post(f"{self.__model_endpoint}/generate", json=data)
            print(f"[INFO] Model generation request succeeded for {user_id}")
        except requests.RequestException as e:
            print(f"[ERROR] Model generation request exception for {user_id}: {e}")

    def __generate_audio(self, user_id: str, request: str) -> None:
        print("[INFO] Calling audio generator...")
        data = {
            "user_id": user_id,
            "prompt": request,
        }

        try:
            requests.post(f"{self.__audio_endpoint}/generate", json=data)
            print(f"[INFO] Audio generation request succeeded for {user_id}")
        except requests.RequestException as e:
            print(f"[ERROR] Audio generation request exception for {user_id}: {e}")

    def get_app(self):
        self.__app.include_router(self.__router)
        return self.__app

    # /request
    async def request(self, request: UserRequest) -> JSONResponse:
        generated_uuid = str(uuid.uuid4())
        qr_data, qr_image = self.__qr_handler.generate_qr(
            RequestItem(uuid=generated_uuid, request=request.request)
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
        user.meta.request = request.request
        user.save_meta()

        print("[INFO] New request registered")
        print(f"  email : {request.email}")
        print(f"  uuid : {generated_uuid}")
        print(f"  request : {request.request}")

        llm_response = await self.__call_llm(request.request)
        self.__db.load_param(generated_uuid, llm_response.model_dump())

        self.__executor.submit(self.__generate_model, generated_uuid, request.request)
        self.__executor.submit(self.__generate_audio, generated_uuid, request.request)

        return JSONResponse(
            content={"detail": f"UUID:{generated_uuid}"}, status_code=200
        )

    # /save/image
    async def save_image(
        self,
        user_id: str = Form(...),
        file: UploadFile = File(...),
    ) -> JSONResponse:
        if not self.__db.is_exist(user_id):
            return JSONResponse(
                status_code=404,
                content={"message": f"User {user_id} not found."},
            )

        self.__db.load_image(user_id, file)

        if self.__db.is_ready(user_id):
            asyncio.create_task(self.__send_email(user_id))

        return JSONResponse(
            {"message": f"Image file for user {uuid} saved successfully."}
        )

    # /save/model
    async def save_model(
        self,
        user_id: str = Form(...),
        file: UploadFile = File(...),
    ) -> JSONResponse:
        if not self.__db.is_exist(user_id):
            return JSONResponse(
                status_code=404,
                content={"message": f"User {user_id} not found."},
            )

        self.__db.load_model(user_id, file)

        if self.__db.is_ready(user_id):
            asyncio.create_task(self.__send_email(user_id))

        return JSONResponse(
            {"message": f"Model file for user {uuid} saved successfully."}
        )

    # /save/audio
    async def save_audio(
        self,
        user_id: str = Form(...),
        file: UploadFile = File(...),
    ) -> JSONResponse:
        if not self.__db.is_exist(user_id):
            return JSONResponse(
                status_code=404,
                content={"message": f"User {user_id} not found."},
            )

        self.__db.load_audio(user_id, file)

        if self.__db.is_ready(user_id):
            asyncio.create_task(self.__send_email(user_id))

        return JSONResponse(
            {"message": f"Audio file for user {uuid} saved successfully."}
        )

    # /{user_id}/status
    async def status(self, user_id: str) -> JSONResponse:
        return JSONResponse(
            {
                "user_id": str(user_id),
                "status": self.__db.is_ready(user_id),
            }
        )

    # /{user_id}/qr
    async def get_qr(self, user_id: str) -> FileResponse:
        qr_path = ""
        if (userdata := self.__db.get_user(user_id)) is not None:
            qr_path = userdata.get_qr_path()
        else:
            return FileResponse("./dummy", status_code=404)

        if not qr_path or not os.path.exists(qr_path):
            return FileResponse("./dummy", status_code=404)

        return FileResponse(
            qr_path, media_type="image/png", filename=os.path.basename(qr_path)
        )

    # /{user_id}/image
    async def get_image(self, user_id: str) -> FileResponse:
        image_path = ""
        if (userdata := self.__db.get_user(user_id)) is not None:
            image_path = userdata.get_image_path()
        else:
            return FileResponse("./dummy", status_code=404)

        if not image_path or not os.path.exists(image_path):
            return FileResponse("./dummy", status_code=404)

        return FileResponse(
            image_path, media_type="image/png", filename=os.path.basename(image_path)
        )

    # /{user_id}/model
    async def get_model(self, user_id: str) -> FileResponse:
        model_path = ""
        if (userdata := self.__db.get_user(user_id)) is not None:
            model_path = userdata.get_model_path()
        else:
            return FileResponse("./dummy", status_code=404)

        if not model_path or not os.path.exists(model_path):
            return FileResponse("./dummy", status_code=404)

        return FileResponse(
            model_path,
            media_type="application/octet-stream",
            filename=os.path.basename(model_path),
        )

    # /{user_id}/audio
    async def get_audio(self, user_id: str) -> FileResponse:
        audio_path = ""
        if (userdata := self.__db.get_user(user_id)) is not None:
            audio_path = userdata.get_audio_path()
        else:
            return FileResponse("./dummy", status_code=404)

        if not audio_path or not os.path.exists(audio_path):
            return FileResponse("./dummy", status_code=404)

        return FileResponse(
            audio_path, media_type="audio/wav", filename=os.path.basename(audio_path)
        )

    # /{user_id}/param
    async def get_param(self, user_id: str) -> FileResponse:
        param_path = ""
        if (userdata := self.__db.get_user(user_id)) is not None:
            param_path = userdata.get_param_path()
        else:
            return FileResponse("./dummy", status_code=404)

        if not param_path or not os.path.exists(param_path):
            return FileResponse("./dummy", status_code=404)

        return FileResponse(
            param_path,
            media_type="application/json",
            filename=os.path.basename(param_path),
        )

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
