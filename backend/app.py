#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from orm import init_db, Puzzle, Submission

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

WIKI_API  = 'https://ja.wikipedia.org/w/api.php'
USER_AGENT = 'WikiRaceApp/1.0 (+https://example.com)'

# ────────────────────────────────────
# ORM ラッパ関数
# ────────────────────────────────────
def fetch_puzzles():
    return [
        {
            'puzzle_id': p.puzzle_id,
            'start_title': p.start_title,
            'goal_title': p.goal_title,
        }
        for p in Puzzle.all()
    ]


def save_submission(puzzle_id, user_name, path, step_count):
    now = datetime.utcnow().isoformat()
    Submission(
        submission_id=None,
        puzzle_id=puzzle_id,
        user_name=user_name,
        path=json.dumps(path, ensure_ascii=False),
        step_count=step_count,
        created_at=now,
    ).save()


def get_ranking(puzzle_id):
    return Submission.ranking(puzzle_id)

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
