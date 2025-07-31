from datetime import datetime
from enum import Enum
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


class Sentiments(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


SENTIMENTS_MAPPING: dict[Sentiments, tuple[str]] = {
    Sentiments.POSITIVE: ("хорош", "люблю"),
    Sentiments.NEGATIVE: ("ненавиж",),
}


app = FastAPI()


DATABASE_URL = "reviews.db"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


class BaseReview(BaseModel):
    text: str


class ReviewToSave(BaseReview):
    sentiment: str
    created_at: str


class SavedReview(ReviewToSave):
    id: int


class ReviewsRepository:
    @classmethod
    def save_review(cls, review_to_save: ReviewToSave) -> SavedReview:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                f"INSERT INTO reviews (text, sentiment, created_at) values (?, ?, ?)",
                (review_to_save.text, review_to_save.sentiment, review_to_save.created_at)
            )
            review_id = cursor.lastrowid
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return SavedReview(
            id=review_id,
            **review_to_save.model_dump()
        )

    @classmethod
    def list_filtered_reviews(cls, sentiment: Sentiments | None) -> list[SavedReview]:
        conn = get_db_connection()
        cursor = conn.cursor()

        if sentiment:
            cursor.execute(
                f"SELECT * FROM reviews WHERE sentiment = ?",
                (sentiment,)
            )
        else:
            cursor.execute(
                "SELECT * FROM reviews"
            )

        rows = cursor.fetchall()
        conn.close()

        return [SavedReview(**dict(row)) for row in rows]


@app.post("/reviews")
def post_review(posted_review: BaseReview) -> SavedReview:
    if any(root in posted_review.text for root in SENTIMENTS_MAPPING[Sentiments.NEGATIVE]):
        sentiment = Sentiments.NEGATIVE
    elif any(root in posted_review.text for root in SENTIMENTS_MAPPING[Sentiments.POSITIVE]):
        sentiment = Sentiments.POSITIVE
    else:
        sentiment = Sentiments.NEUTRAL

    review_to_save = ReviewToSave(
        text=posted_review.text,
        sentiment=sentiment,
        created_at=datetime.utcnow().isoformat()
    )
    try:
        saved_review = ReviewsRepository.save_review(review_to_save)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding review record to db: {e}")

    return saved_review


@app.get("/reviews")
def get_reviews(sentiment: Sentiments | None = None) -> list[SavedReview]:
    return ReviewsRepository.list_filtered_reviews(sentiment=sentiment)
