CATEGORIES = {
    "quantitative": "Quantitative Aptitude",
    "logical": "Logical Reasoning",
    "verbal": "Verbal Ability",
    "dsa": "Data Structures & Algorithms",
    "oop": "Object-Oriented Programming",
    "dbms": "Database Systems",
    "os": "Operating Systems",
    "networks": "Computer Networks",
    "software-eng": "Software Engineering",
}
APTITUDE = {"quantitative", "logical", "verbal"}
DIFFICULTIES = ["easy", "medium", "hard", "expert"]


def topic_label(topic: str) -> str:
    return topic.replace("-", " ").capitalize()


def category_label(category: str) -> str:
    return CATEGORIES.get(category, category.replace("-", " ").title())
