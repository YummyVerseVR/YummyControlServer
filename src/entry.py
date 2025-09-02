import uvicorn
from app import App

app = App().get_app()
if __name__ == "__main__":
    uvicorn.run("entry:app", host="0.0.0.0", port=8002, reload=True)