from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AIReport, PerformanceSnapshot, Response, Test
from ..taxonomy import APTITUDE, topic_label
from . import ai


def create_report(db: Session, test: Test) -> AIReport:
    responses = {r.question_id: r for r in db.scalars(select(Response).where(Response.test_id == test.id))}
    snap = db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.test_id == test.id))

    by_topic: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # attempted, correct
    quant_time: list[int] = []
    other_time: list[int] = []
    skipped_topics: set[str] = set()
    for item in test.items:
        q = item.question
        r = responses.get(q.id)
        if not r or not r.selected_answer:
            skipped_topics.add(q.topic)
            continue
        by_topic[q.topic][0] += 1
        by_topic[q.topic][1] += int(bool(r.is_correct))
        (quant_time if q.category == "quantitative" else other_time).append(r.time_spent_seconds)

    strengths = [topic_label(t) for t, (a, c) in by_topic.items() if a and c == a]
    weak_topics = [t for t, (a, c) in by_topic.items() if c < a]
    weaknesses = [topic_label(t) for t in weak_topics] + [f"{topic_label(t)} (skipped)" for t in sorted(skipped_topics - set(weak_topics))]

    recs: list[str] = []
    for t in weak_topics[:2] + sorted(skipped_topics - set(weak_topics))[:1]:
        recs.append(f"Practice about 5 questions on {topic_label(t).lower()} before your next challenge.")
    if snap and snap.completion < 100:
        recs.append("Answer every question, even with a best guess. Skipped questions cannot score.")
    if not recs:
        recs.append("Solid session. Keep the streak going and let tomorrow's mix raise the difficulty.")

    pattern = ""
    if quant_time and other_time:
        q_avg, o_avg = sum(quant_time) / len(quant_time), sum(other_time) / len(other_time)
        if q_avg > o_avg * 1.3:
            pattern = "You spent noticeably longer on numerical questions than on the rest."
        elif o_avg > q_avg * 1.3:
            pattern = "Conceptual and verbal questions took you longer than the numerical ones."

    pct = round(snap.score / snap.total * 100) if snap and snap.total else 0
    summary = f"You scored {snap.score if snap else 0}/{snap.total if snap else test.total_questions} ({pct}%)."
    if snap:
        summary += f" Accuracy on attempted questions was {snap.accuracy:.0f}%."
    if pattern:
        summary += " " + pattern

    narrative = ai.generate_narrative({
        "percentage": pct, "accuracy": snap.accuracy if snap else 0, "completion": snap.completion if snap else 0,
        "average_seconds_per_question": snap.average_time if snap else 0,
        "strong_topics": strengths, "weak_topics": weaknesses,
        "aptitude_questions": sum(1 for i in test.items if i.question.category in APTITUDE),
    })
    source = "template"
    if narrative:
        summary += "\n\n" + narrative
        source = "ai"

    report = AIReport(user_id=test.user_id, test_id=test.id, summary=summary, strengths_json=strengths,
                      weaknesses_json=weaknesses, recommendations_json=recs, narrative_source=source)
    db.add(report)
    return report
