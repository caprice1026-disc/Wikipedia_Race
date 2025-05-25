#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
import time
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import os
import requests

# ────────────────────────────────────
# ロガー初期化
# ────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,                       # DEBUG にしたいときは環境変数などで切替えてね
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────
# Flask アプリ
# ────────────────────────────────────
app = Flask(__name__)

DB_PATH   = 'wikirace.db'
WIKI_API  = 'https://ja.wikipedia.org/w/api.php'
USER_AGENT = 'WikiRaceApp/1.0 (+https://example.com)'

# ────────────────────────────────────
# DB ヘルパ
# ────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS puzzle (
            puzzle_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            start_title TEXT NOT NULL,
            goal_title  TEXT NOT NULL,
            created_at  TEXT,
            updated_at  TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS submission (
            submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id     INTEGER NOT NULL,
            user_name     TEXT,
            path          TEXT NOT NULL,
            step_count    INTEGER NOT NULL,
            created_at    TEXT,
            FOREIGN KEY(puzzle_id) REFERENCES puzzle(puzzle_id)
    )""")
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM puzzle")
    if cur.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO puzzle (start_title, goal_title, created_at, updated_at) VALUES (?,?,?,?)",
            ('HTTP', 'UNIX', now, now)
        )
        conn.commit()
        logger.info('Sample puzzle inserted (HTTP → UNIX)')

    conn.close()

# ────────────────────────────────────
# クエリ用ユーティリティ
# ────────────────────────────────────
def fetch_puzzles():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT puzzle_id, start_title, goal_title FROM puzzle")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def save_submission(puzzle_id, user_name, path, step_count):
    conn = get_db()
    cur  = conn.cursor()
    now  = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO submission (puzzle_id, user_name, path, step_count, created_at) VALUES (?,?,?,?,?)",
        (puzzle_id, user_name, json.dumps(path, ensure_ascii=False), step_count, now)
    )
    conn.commit()
    conn.close()

def get_ranking(puzzle_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "SELECT user_name, step_count FROM submission "
        "WHERE puzzle_id=? ORDER BY step_count ASC, submission_id ASC",
        (puzzle_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ────────────────────────────────────
# Wikipedia リンク存在チェック
# ────────────────────────────────────
def check_link_exists(source_title, target_title, retries=3):
    """
    Return True if `source_title` page directly links to `target_title`.
    Retries network errors with exponential backoff.
    """

    base_params = {
        'action': 'query',
        'prop'  : 'links',
        'titles': source_title,
        'pllimit': 'max',
        'format': 'json',
        'redirects': 1,             # ソースがリダイレクトでも本体で検索
    }

    attempt = 0
    while attempt < retries:
        try:
            next_cursor = None
            while True:
                params = dict(base_params)
                if next_cursor:
                    params['plcontinue'] = next_cursor

                resp = requests.get(
                    WIKI_API, params=params,
                    headers={'User-Agent': USER_AGENT},
                    timeout=10
                )
                resp.raise_for_status()
                data = resp.json()

                pages = data.get('query', {}).get('pages', {})
                for page in pages.values():
                    for link in page.get('links', []):
                        if link.get('title') == target_title:
                            logger.debug('FOUND link %s → %s', source_title, target_title)
                            return True

                next_cursor = data.get('continue', {}).get('plcontinue')
                if not next_cursor:
                    break

            logger.debug('NOT FOUND link %s → %s', source_title, target_title)
            return False

        except Exception as e:
            logger.warning('Link check error (%s → %s) %s', source_title, target_title, e)
            time.sleep((2 ** attempt) + random.random())
            attempt += 1

    raise RuntimeError('Wikipedia API unreachable')

# ────────────────────────────────────
# ルート定義
# ────────────────────────────────────
@app.route('/')
def index():
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/api/puzzles', methods=['GET'])
def api_puzzles():
    puzzles = fetch_puzzles()
    return jsonify({'puzzles': puzzles})

@app.route('/api/validate', methods=['POST'])
def api_validate():
    payload = request.get_json(force=True)
    logger.info('POST /api/validate payload=%s', payload)

    puzzle_id  = payload.get('puzzle_id')
    route      = payload.get('route', [])
    user_name  = payload.get('user_name', 'anonymous')

    if not puzzle_id or len(route) < 2:
        logger.warning('Bad payload')
        return jsonify({'error': 'invalid payload'}), 400

    puzzles = {p['puzzle_id']: p for p in fetch_puzzles()}
    puzzle  = puzzles.get(puzzle_id)
    if not puzzle:
        logger.warning('Puzzle %s not found', puzzle_id)
        return jsonify({'error': 'puzzle not found'}), 404

    # 検証開始
    for i in range(len(route) - 1):
        src = route[i]
        dst = route[i + 1]
        try:
            if not check_link_exists(src, dst):
                logger.info('Validation FAIL at step %d (%s → %s)', i + 1, src, dst)
                return jsonify({'valid': False, 'failed_step': i + 1}), 200
        except Exception:
            logger.error('Wikipedia API unreachable during validation')
            return jsonify({'valid': False, 'error': 'API unreachable'}), 503

    step_count = len(route) - 1
    save_submission(puzzle_id, user_name, route, step_count)
    logger.info('Validation OK steps=%d user=%s', step_count, user_name)
    return jsonify({'valid': True, 'step_count': step_count}), 200

@app.route('/api/ranking', methods=['GET'])
def api_ranking():
    puzzle_id = request.args.get('puzzle_id', type=int)
    if not puzzle_id:
        return jsonify({'error': 'puzzle_id required'}), 400
    ranking = get_ranking(puzzle_id)
    return jsonify({'ranking': ranking})

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
    app.run(host='0.0.0.0', port=5000, debug=False)   # debug=True だと Flask が自前ロガーを出すので注意
