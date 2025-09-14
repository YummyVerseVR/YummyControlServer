# ControlServer

## 実行方法
.envファイルに送信用Gmailの情報を設定
```
FROM_EMAIL="送信元email"
APP_PASSWORD="app pass"
```
アプリパスワードについては下記を参照

https://support.google.com/mail/answer/185833?hl=ja
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