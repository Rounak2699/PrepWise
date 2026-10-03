from ..models import User
from ..schemas import PreferencesOut, UserOut


def user_out(user: User) -> UserOut:
    onboarded = bool(user.academic_year and user.preferences and user.preferences.preferred_topics)
    return UserOut(
        id=user.id, name=user.name, email=user.email, role=user.role,
        academic_year=user.academic_year, branch=user.branch,
        graduation_year=user.graduation_year, target_role=user.target_role,
        onboarded=onboarded,
        preferences=PreferencesOut.model_validate(user.preferences),
    )
