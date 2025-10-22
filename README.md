# ControlServer

## 実行方法
```
uv sync
uv run src/entry.py
```

## 引数一覧
- `--port / -p`: サーバのポート番号
    - デフォルト: 8000

- `--config / -c`: 設定ファイルのパス
    - デバッグ等の用途で設定ファイルを変更したい場合に指定します.
    - デフォルト: `./settings/config.json`

- `--debug / -d`: デバッグモードを有効化
    - デバッグが有効な場合, 一部のAPIエンドポイントが有効化される他, loggingを除くすべてのネットワークを必要とする処理が無効化されます.
    - デフォルト: 無効

- `--logging / -l`: ネットワークロギングを有効化
    - 有効な場合はpylognetを使用してログサーバにログを送信します.
    - デフォルト: 無効

## config.jsonの仕様
設定ファイル`config.json`は以下の形式で記述します.
```json
{
    "db": {
        "path": "データベースのパス(任意)"
    },
    "endpoints": {
        "audio": "オーディオ生成サーバのURL(任意)",
        "model": "モデル生成サーバのURL(任意)",
        "ollama": "OllamaサーバのURL(任意)",
        "logger": "ログサーバのURL(任意)"
    },
    "ollama": {
        "model": "モデル名(任意)",
        "prompt": "Ollamaへのプロンプトテンプレート(任意)",
        "candidates": [
            "近い食感か判定するための候補リスト(任意)",
            "{ "name": "食品名" } の形式で複数指定",
        ],
        "temperature": "モデルの温度(任意)",
        "num_predict": "思考回数(任意)"
    },
    "email": {
        "scopes": ["Google APIのスコープ(任意)"],
        "from": "送信元メールアドレス(任意)",
        "credential": "Google APIの認証情報ファイルパス(任意)",
        "token": "Google APIのトークンファイルパス(任意)"
    }
}
```

## APIエンドポイント
このサーバは以下のAPIエンドポイントを提供します. 詳細な仕様についてはFastAPIの自動生成ドキュメント`http://0.0.0.0:<port>/docs`を参照してください.
