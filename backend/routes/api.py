import logging
import os
from flask import Blueprint, request, jsonify, send_from_directory
from ..services.database import fetch_puzzles, save_submission, get_ranking
from ..services.wiki import check_link_exists

bp = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    """トップページを返す"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    return send_from_directory(frontend_dir, "index.html")


@bp.route("/api/puzzles", methods=["GET"])
def api_puzzles():
    puzzles = fetch_puzzles()
    return jsonify({"puzzles": puzzles})


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

