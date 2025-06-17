#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Flask アプリケーションのエントリーポイント"""

import logging
from flask import Flask
from orm import init_db
from routes.api import bp as api_bp

# ────────────────────────────────────
# ロガー初期化
# ────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────
# Flask アプリ
# ────────────────────────────────────
app = Flask(__name__)
app.register_blueprint(api_bp)

# ────────────────────────────────────
# セキュリティヘッダ（拡張注入を抑止したい場合は有効化）
# ────────────────────────────────────
@app.after_request
def apply_csp(resp):
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "object-src 'none';"
    )
    return resp

# ────────────────────────────────────
# 起動時に DB 初期化
# ────────────────────────────────────
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
