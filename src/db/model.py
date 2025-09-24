import shutil
import os
import json

from fastapi import UploadFile
from io import BytesIO
from pydantic import BaseModel


class MetaData(BaseModel):
    uuid: str
    email: str
    qr_code: str
    request: str


class UserData:
    META_FILE = "meta.json"
    QR_FILE = "qr.png"
    IMAGE_FILE = "image.png"
    MODEL_FILE = "model.glb"
    AUDIO_FILE = "audio.wav"
    PARAM_FILE = "params.json"

    def __init__(self, user_id: str, db_path: str):
        self.__db_path = db_path
        self.__uuid = user_id
        self.__meta_path = os.path.join(self.get_user_path(), UserData.META_FILE)
        self.__qr_path = os.path.join(self.get_user_path(), UserData.QR_FILE)
        self.__image_path = os.path.join(self.get_user_path(), UserData.IMAGE_FILE)
        self.__model_path = os.path.join(self.get_user_path(), UserData.MODEL_FILE)
        self.__audio_path = os.path.join(self.get_user_path(), UserData.AUDIO_FILE)
        self.__param_path = os.path.join(self.get_user_path(), UserData.PARAM_FILE)
        self.__status = {
            UserData.QR_FILE: False,
            UserData.IMAGE_FILE: False,
            UserData.MODEL_FILE: False,
            UserData.AUDIO_FILE: False,
            UserData.PARAM_FILE: False,
        }

        self.meta = MetaData(
            uuid=self.__uuid,
            email="",
            qr_code="",
            request="",
        )

        os.makedirs(self.get_user_path(), exist_ok=True)

    def get_uuid(self) -> str:
        return self.__uuid

    def get_user_path(self) -> str:
        return os.path.join(self.__db_path, str(self.__uuid))

    def get_meta_path(self) -> str:
        return self.__meta_path if os.path.exists(self.__meta_path) else ""

    def get_qr_path(self) -> str:
        return self.__qr_path if os.path.exists(self.__qr_path) else ""

    def get_image_path(self) -> str:
        return self.__image_path if os.path.exists(self.__image_path) else ""

    def get_model_path(self) -> str:
        return self.__model_path if os.path.exists(self.__model_path) else ""

    def get_audio_path(self) -> str:
        return self.__audio_path if os.path.exists(self.__audio_path) else ""

    def get_param_path(self) -> str:
        return self.__param_path if os.path.exists(self.__param_path) else ""

    def set_status(self, file_type: str, status: bool) -> None:
        if file_type in self.__status.keys():
            self.__status[file_type] = status

    def is_ready(self) -> bool:
        return all(self.__status.values())

    def remove_all_files(self) -> None:
        if not os.path.exists(self.get_user_path()):
            return

        if os.path.exists(self.__meta_path):
            os.remove(self.__meta_path)
        if os.path.exists(self.__qr_path):
            os.remove(self.__qr_path)
        if os.path.exists(self.__image_path):
            os.remove(self.__image_path)
        if os.path.exists(self.__model_path):
            os.remove(self.__model_path)
        if os.path.exists(self.__audio_path):
            os.remove(self.__audio_path)
        if os.path.exists(self.__param_path):
            os.remove(self.__param_path)

        self.__status = {
            UserData.QR_FILE: False,
            UserData.IMAGE_FILE: False,
            UserData.MODEL_FILE: False,
            UserData.AUDIO_FILE: False,
            UserData.PARAM_FILE: False,
        }

    def save_meta(self) -> None:
        """
        Save metadata to a JSON file.
        """
        with open(self.__meta_path, "w") as f:
            json.dump(self.meta.model_dump(), f, indent=4)

    def load_meta(self) -> None:
        """
        Load metadata from a JSON file.
        """
        if not os.path.exists(self.__meta_path):
            return

        with open(self.__meta_path, "r") as f:
            data = json.load(f)
            self.meta = MetaData(**data)

    def load_qr(self, qr_data: BytesIO) -> None:
        """
        Write QR code data to a file.

        Args:
            qr_data (BytesIO): QR code image data in bytes.
        """
        self.__status[UserData.QR_FILE] = True
        if os.path.exists(self.__qr_path):
            os.remove(self.__qr_path)

        with open(self.__qr_path, "wb") as f:
            f.write(qr_data.getbuffer())

    def load_image(self, image_data: UploadFile) -> None:
        """
        Write image data to a file.

        Args:
            image_data (UploadFile): Image file uploaded by the user.
        """
        self.__status[UserData.IMAGE_FILE] = True
        if os.path.exists(self.__image_path):
            os.remove(self.__image_path)

        with open(self.__image_path, "wb") as f:
            shutil.copyfileobj(image_data.file, f)

    def load_model(self, model_data: UploadFile) -> None:
        """
        Write model data to a file.

        Args:
            model_data (UploadFile): Model file uploaded by the user.
        """
        self.__status[UserData.MODEL_FILE] = True
        if os.path.exists(self.__model_path):
            os.remove(self.__model_path)

        with open(self.__model_path, "wb") as f:
            shutil.copyfileobj(model_data.file, f)

    def load_audio(self, audio_data: UploadFile) -> None:
        """
        Write audio data to a file.

        Args:
            audio_data (UploadFile): Audio file uploaded by the user.
        """
        self.__status[UserData.AUDIO_FILE] = True
        if os.path.exists(self.__audio_path):
            os.remove(self.__audio_path)

        with open(self.__audio_path, "wb") as f:
            shutil.copyfileobj(audio_data.file, f)

    def load_param(self, param_data: dict) -> None:
        """
        Write parameter data to a JSON file.

        Args:
            param_data (dict): Parameter data in dictionary format.
        """
        self.__status[UserData.PARAM_FILE] = True
        if os.path.exists(self.__param_path):
            os.remove(self.__param_path)

        with open(self.__param_path, "w") as f:
            json.dump(param_data, f, indent=4)
