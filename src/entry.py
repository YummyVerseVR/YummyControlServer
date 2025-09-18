import argparse
import uvicorn
from app import App

parser = argparse.ArgumentParser(description="Run the FastAPI application.")
parser.add_argument(
    "-q",
    "--qr-server",
    type=str,
    default="http://192.168.11.101:8006",
    help="QR code server address",
)
parser.add_argument(
    "-p",
    "--port",
    type=int,
    default=8000,
    help="Port to run the FastAPI application on",
)
parser.add_argument(
    "--debug",
    type=bool,
    default=False,
    help="Enable debug mode",
)
args = parser.parse_args()

app = App(args.qr_server,
          args.debug
        ).get_app()
if __name__ == "__main__":
    uvicorn.run("entry:app", host="0.0.0.0", port=args.port)
