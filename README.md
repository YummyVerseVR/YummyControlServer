# ControlServer

## 実行方法
```
uv sync

uv run src/entry.py
```

## /register-request
GAS Serverから叩く用
    email: str
    request: str

## set-user-status
DATABASE Serverからのnotify readyを受け取る用
    uuid: str
    is_ready: bool

is_readyをfalseのとき、異常事態であるとする