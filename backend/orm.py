from datetime import datetime
from typing import List, Dict

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# DB ファイルパス
DB_PATH = 'sqlite:///wikirace.db'

# SQLAlchemy 初期化
engine = create_engine(DB_PATH, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

Base = declarative_base()


class Puzzle(Base):
    __tablename__ = 'puzzle'

    puzzle_id = Column(Integer, primary_key=True, autoincrement=True)
    start_title = Column(String, nullable=False)
    goal_title = Column(String, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    @classmethod
    def all(cls) -> List['Puzzle']:
        with SessionLocal() as session:
            return session.query(cls).all()

    def save(self) -> None:
        with SessionLocal() as session:
            session.add(self)
            session.commit()
            session.refresh(self)


class Submission(Base):
    __tablename__ = 'submission'

    submission_id = Column(Integer, primary_key=True, autoincrement=True)
    puzzle_id = Column(Integer, ForeignKey('puzzle.puzzle_id'), nullable=False)
    user_name = Column(String)
    path = Column(Text, nullable=False)
    step_count = Column(Integer, nullable=False)
    created_at = Column(DateTime)

    def save(self) -> None:
        with SessionLocal() as session:
            session.add(self)
            session.commit()
            session.refresh(self)

    @classmethod
    def ranking(cls, puzzle_id: int) -> List[Dict[str, int]]:
        with SessionLocal() as session:
            rows = (
                session.query(cls.user_name, cls.step_count)
                .filter(cls.puzzle_id == puzzle_id)
                .order_by(cls.step_count.asc(), cls.submission_id.asc())
                .all()
            )
            return [
                {'user_name': r.user_name, 'step_count': r.step_count}
                for r in rows
            ]


def init_db() -> None:
    """テーブル作成とサンプルデータ挿入"""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if session.query(Puzzle).count() == 0:
            now = datetime.utcnow()
            puzzle = Puzzle(
                start_title='HTTP',
                goal_title='UNIX',
                created_at=now,
                updated_at=now,
            )
            session.add(puzzle)
            session.commit()

