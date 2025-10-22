from io import BytesIO
from pylognet.client import LoggingClient
import shutil
import os

from fastapi import UploadFile

from db.model import UserData


class DataBase:
    def __init__(
        self,
        config: dict,
        logger: LoggingClient,
        debug_mode: bool = False,
    ) -> None:
        self.__debug = debug_mode
        self.__logger = logger
        self.__config = config.get("db", {})
        db_path = self.__config.get("path", "~/YummyVerse")
        self.__db_path = os.path.expanduser(db_path)
        self.__tables: dict[str, UserData] = {}

        os.makedirs(self.__db_path, exist_ok=True)
        self.__load_tables()

    def __load_tables(self) -> None:
        for user_id in os.listdir(self.__db_path):
            try:
                self.__tables[user_id] = UserData(user_id, self.__db_path)
            except ValueError:
                continue

        for user_id, user_data in self.__tables.items():
            if os.path.exists(user_data.get_meta_path()):
                user_data.load_meta()

            if os.path.exists(user_data.get_qr_path()):
                user_data.set_status(UserData.QR_FILE, True)
            if os.path.exists(user_data.get_image_path()):
                user_data.set_status(UserData.IMAGE_FILE, True)
            if os.path.exists(user_data.get_model_path()):
                user_data.set_status(UserData.MODEL_FILE, True)
            if os.path.exists(user_data.get_audio_path()):
                user_data.set_status(UserData.AUDIO_FILE, True)
            if os.path.exists(user_data.get_param_path()):
                user_data.set_status(UserData.PARAM_FILE, True)

    def get_user(self, user_id: str) -> UserData | None:
        if user_id not in self.__tables.keys():
            return None

        return self.__tables[user_id]

    def remove_user(self, user_id: str) -> bool:
        if user_id not in self.__tables.keys():
            return False

        user_data = self.__tables[user_id]
        user_data.remove_all_files()
        shutil.rmtree(user_data.get_user_path(), ignore_errors=True)

        del self.__tables[user_id]

        return True

    def is_exist(self, user_id: str) -> bool:
        return user_id in self.__tables.keys()

    def is_ready(self, user_id: str) -> bool:
        if user_id not in self.__tables.keys():
            return False

        return self.__tables[user_id].is_ready()

    def add_user(self, user_id: str):
        if user_id in self.__tables.keys():
            return self.__tables[user_id]

        user_data = UserData(user_id, self.__db_path)

        self.__tables[user_id] = user_data

    def list_users(self) -> list[UserData]:
        return list(self.__tables.values())

    def load_qr(self, user_id: str, qr_data: BytesIO) -> None:
        if user_id not in self.__tables.keys():
            raise ValueError(f"User {user_id} not found in database.")

        self.__tables[user_id].load_qr(qr_data)

    def load_image(self, user_id: str, image_data: UploadFile) -> None:
        if user_id not in self.__tables.keys():
            raise ValueError(f"User {user_id} not found in database.")

        self.__tables[user_id].load_image(image_data)

    def load_model(self, user_id: str, model_data: UploadFile) -> None:
        if user_id not in self.__tables.keys():
            raise ValueError(f"User {user_id} not found in database.")

        self.__tables[user_id].load_model(model_data)

    def load_audio(self, user_id: str, audio_data: UploadFile) -> None:
        if user_id not in self.__tables.keys():
            raise ValueError(f"User {user_id} not found in database.")

        self.__tables[user_id].load_audio(audio_data)

    def load_param(self, user_id: str, param_data: dict) -> None:
        if user_id not in self.__tables.keys():
            raise ValueError(f"User {user_id} not found in database.")

        self.__tables[user_id].load_param(param_data)
