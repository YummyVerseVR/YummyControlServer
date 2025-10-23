import qrcode
import base64

from io import BytesIO
from pylognet.client import LoggingClient, LogLevel


class QRHandler:
    def __init__(
        self,
        config: dict,
        logger: LoggingClient,
        debug_mode: bool = False,
    ) -> None:
        self.__debug = debug_mode
        self.__logger = logger
        self.__config = config.get("qr", {})

    def generate_qr(self, user_id: str) -> tuple[str, BytesIO]:
        """
        Generate a QR code for the given item uuid and return it as a base64-encoded string.

        Args:
            item (Item): An instance of Item containing uuid and request.
        """
        self.__logger.log(
            f"Generating QR code for User ID: {user_id}",
            LogLevel.INFO,
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)

        qr.add_data(user_id)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_buf = BytesIO()
        img.save(img_buf, format="PNG")
        img_buf.seek(0)
        qr_code_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        return qr_code_base64, img_buf
