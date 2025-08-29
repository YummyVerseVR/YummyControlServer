from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse

class App:
    def __init__(self):
        self.app = FastAPI()
        self.router = APIRouter()
        self.__setup_routes()

        #とりあえず仮で辞書型を。処理途中でサーバ落ちたら終わる
        self.__db = {}
    
    def __setup_routes(self):
        self.router.get("/")(self.read_root)
        self.router.post("/set-user-status")(self.set_user_status)
        self.router.post("/register-qr")(self.register_qr)


    async def read_root(self):
        return {"detail": "A Control Server"}

    async def set_user_status(self, uuid: str,is_ready: bool) -> JSONResponse:
        if uuid not in self.__db:
            return JSONResponse(content={"detail": "UUID not found"}, status_code=404)
        if not is_ready:
            self.__db.pop(uuid)
            return JSONResponse(content={"detail": "some thing wrong. please try again"}, status_code=400)
        
        await self.send_qr(self.__db[uuid])
        return JSONResponse(content={"detail": "User status endpoint"})

    async def register_qr(self, uuid: str, qr_base64: str) -> JSONResponse:
        #多重の登録を回避(mail addressから一意にuuidが生成される前提)
        if uuid in self.__db:
            return JSONResponse(content={"detail": "UUID already exists, please wait for the previous request to complete"}, status_code=400)
        self.__db[uuid] = qr_base64
        return JSONResponse(content={"detail": "Register QR endpoint"})

    async def send_qr(self, qr_base64: str):
        # あとでYummyVerse/SendQRByGmailから移植
        pass