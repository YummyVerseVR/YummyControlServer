import uvicorn
from app import App

if __name__ == "__main__":
    App.run()
    uvicorn.run(App, host="0.0.0.0", port=8000)