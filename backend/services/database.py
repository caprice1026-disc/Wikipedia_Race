from datetime import datetime
import json
from ..orm import Puzzle, Submission


def fetch_puzzles():
    """Puzzle一覧を辞書形式で取得"""
    return [
        {
            "puzzle_id": p.puzzle_id,
            "start_title": p.start_title,
            "goal_title": p.goal_title,
        }
        for p in Puzzle.all()
    ]


def save_submission(puzzle_id: int, user_name: str, path, step_count: int) -> None:
    """検証済みの解答を保存"""
    now = datetime.utcnow().isoformat()
    Submission(
        submission_id=None,
        puzzle_id=puzzle_id,
        user_name=user_name,
        path=json.dumps(path, ensure_ascii=False),
        step_count=step_count,
        created_at=now,
    ).save()


def get_ranking(puzzle_id: int):
    """ランキング情報を取得"""
    return Submission.ranking(puzzle_id)
