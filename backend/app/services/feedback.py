from app.core.config import settings
from app.schemas import Feedback
from app.services.openrouter import structured
from app.services.skills import evidence


def generate_feedback(snapshot, listing, status, note):
    matched, missing = evidence(snapshot.get("extracted_skills", []), listing["required_skills"])
    if settings().ai_mode == "demo":
        return Feedback(
            summary="Demo learning suggestions based on your application-time profile. "
            + (
                "Potential gaps are not the employer's rejection reason."
                if status == "rejected"
                else "Prepare to discuss your relevant coursework and projects."
            ),
            strengths=matched[:8],
            potential_gaps=missing[:8],
            next_steps=[f"Build a small project demonstrating {s}." for s in missing[:3]]
            or ["Prepare a concise explanation of a project and its tradeoffs."],
            practice_questions=[f"How have you used {s} in a project?" for s in matched[:3]],
        )
    return structured(
        Feedback,
        "Provide practical interview preparation for viewed applications or learning improvements for rejected applications. Label advice as AI suggestions. Never claim to know a rejection reason unless the employer note supplies it. Do not invent qualifications or guarantee outcomes.",
        {"application_time_profile": snapshot, "listing": listing, "status": status, "employer_note": note},
    )
