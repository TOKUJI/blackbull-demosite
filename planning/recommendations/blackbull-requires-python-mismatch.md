# BlackBull — requires-python が実際の API 要件と不一致

## 症状

`blackbull` 0.48.1 の `pyproject.toml` には `requires-python = ">=3.11"` と
宣言されているが、`BlackBull()` コンストラクタ内で `HTTPStatus.is_client_error`
および `HTTPStatus.is_server_error` プロパティを使用している。

これらのプロパティは Python 3.12 で追加されたものであり（Python 3.12 公式
ドキュメントに `Added in version 3.12` と明記）、Python 3.11 には存在しない。

結果として、Python 3.11 環境で `blackbull` 0.48.1 を使用すると
`BlackBull()` のインスタンス化時に以下のエラーが発生する：

```
AttributeError: 'HTTPStatus' object has no attribute 'is_client_error'
```

## 再現手順

```bash
# Python 3.11.15 環境
$ python -c "from blackbull import BlackBull; BlackBull()"
AttributeError: 'HTTPStatus' object has no attribute 'is_client_error'
```

```bash
# Python 3.12 環境 — 問題なく動作
$ python -c "from blackbull import BlackBull; BlackBull()"
# OK
```

## 原因

`blackbull/app.py` および `blackbull/router.py` が以下のコードを実行している：

```python
# blackbull/app.py (BlackBull.__init__)
for status in HTTPStatus:
    if status.is_client_error or status.is_server_error:  # ← Python 3.12 API
        self._error_router[status] = _default_error_handler
```

```python
# blackbull/router.py (ErrorRouter.__setitem__)
if not key.is_client_error and not key.is_server_error:  # ← Python 3.12 API
    raise ValueError(f"{key} is not an error status (4xx/5xx).")
```

## 影響

- **blackbull-demosite CI**: `deploy.yml` で `python-version: '3.11'` を指定して
  いたため、テストが全件エラー（21/21 ERROR）
- **Python 3.11 ユーザー全般**: `requires-python = ">=3.11"` を信じて 3.11 を
  使用しているユーザーはアプリケーション起動時にクラッシュする

## 推奨される対応

`blackbull` 側で以下のいずれかを行うべき：

1. `requires-python` を `>=3.12` に修正する（推奨）
2. コードを修正して `is_client_error` に依存しないようにする（例: `400 <= status <= 499` の範囲チェック）

## 参考

- [Python 3.12 http.HTTPStatus ドキュメント](https://docs.python.org/3.12/library/http.html#http-status-category)
  — `is_client_error` 他は "Added in version 3.12"
- [Python 3.11 http.HTTPStatus ドキュメント](https://docs.python.org/3.11/library/http.html)
  — HTTP status category セクション自体が存在しない
- Python 3.11 EOL: 2027-10（現役サポート中）
