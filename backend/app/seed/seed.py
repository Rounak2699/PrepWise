from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.db import Base, SessionLocal, engine
from ..models import Question
from .questions import Q


def seed_questions(db: Session) -> int:
    existing = {p for (p,) in db.execute(select(Question.prompt))}
    added = 0
    for cat, topic, diff, prompt, options, answer, explanation in Q:
        assert len(options) == 4 and answer in "ABCD", prompt
        if prompt in existing:
            continue
        db.add(Question(type="mcq", category=cat, topic=topic, difficulty=diff, prompt=prompt, options_json=options,
                        correct_answer=answer, explanation=explanation, status="published", generation_source="seed"))
        added += 1
    db.commit()
    return added


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print(f"Seeded {seed_questions(db)} questions")
