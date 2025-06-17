import logging
import os
from flask import Blueprint, request, jsonify, send_from_directory
from ..services.database import (
    fetch_puzzles,
    save_submission,
    get_ranking,
    add_puzzle,
)
from ..services.wiki import check_link_exists

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admin-secret")

bp = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    """トップページを返す"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    return send_from_directory(frontend_dir, "index.html")


@bp.route("/static/<path:filename>")
def static_files(filename):
    """フロントエンドの静的ファイルを返す"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    return send_from_directory(frontend_dir, filename)


@bp.route("/api/puzzles", methods=["GET"])
def api_puzzles():
    puzzles = fetch_puzzles()
    return jsonify({"puzzles": puzzles})


@bp.route("/api/puzzles", methods=["POST"])
def api_add_puzzle():
    """管理者によるパズル追加"""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_TOKEN}":
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(force=True)
    start_title = payload.get("start_title")
    goal_title = payload.get("goal_title")
    if not start_title or not goal_title:
        return jsonify({"error": "invalid payload"}), 400

    puzzle = add_puzzle(start_title, goal_title)
    logger.info("Added puzzle %s", puzzle.puzzle_id)
    return jsonify({"puzzle_id": puzzle.puzzle_id}), 201


@bp.route("/api/validate", methods=["POST"])
def api_validate():
    payload = request.get_json(force=True)
    logger.info("POST /api/validate payload=%s", payload)

    puzzle_id = payload.get("puzzle_id")
    route = payload.get("route", [])
    user_name = payload.get("user_name", "anonymous")

    if not puzzle_id or len(route) < 2:
        logger.warning("Bad payload")
        return jsonify({"error": "invalid payload"}), 400

    puzzles = {p["puzzle_id"]: p for p in fetch_puzzles()}
    puzzle = puzzles.get(puzzle_id)
    if not puzzle:
        logger.warning("Puzzle %s not found", puzzle_id)
        return jsonify({"error": "puzzle not found"}), 404

    for i in range(len(route) - 1):
        src = route[i]
        dst = route[i + 1]
        try:
            if not check_link_exists(src, dst):
                logger.info("Validation FAIL at step %d (%s → %s)", i + 1, src, dst)
                return jsonify({"valid": False, "failed_step": i + 1}), 200
        except Exception:
            logger.error("Wikipedia API unreachable during validation")
            return jsonify({"valid": False, "error": "API unreachable"}), 503

    step_count = len(route) - 1
    # 検証がすべて成功した場合のみランキングへ登録
    save_submission(puzzle_id, user_name, route, step_count)
    logger.info("Validation OK steps=%d user=%s", step_count, user_name)
    return jsonify({"valid": True, "step_count": step_count}), 200


@bp.route("/api/ranking", methods=["GET"])
def api_ranking():
    puzzle_id = request.args.get("puzzle_id", type=int)
    if not puzzle_id:
        return jsonify({"error": "puzzle_id required"}), 400
    ranking = get_ranking(puzzle_id)
    return jsonify({"ranking": ranking})

