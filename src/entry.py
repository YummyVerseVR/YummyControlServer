import argparse
import json
import uvicorn
from app import App


CONFIG_PATH = "./settings/meta.json"

parser = argparse.ArgumentParser(description="Run the FastAPI application.")
parser.add_argument(
    "-p",
    "--port",
    type=int,
    default=8000,
    help="Port to run the FastAPI application on",
)
parser.add_argument(
    "--config",
    type=str,
    default=CONFIG_PATH,
    help="Path to the configuration file",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Run the application in debug mode",
)
args = parser.parse_args()

with open(args.config, "r") as f:
    config = json.load(f)

app = App(config, args.debug).get_app()
if __name__ == "__main__":
    uvicorn.run("entry:app", host="0.0.0.0", port=args.port)
