import logging
import sys
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import MusicPreference
from .personalize import answers_from_preference, summary_from_preference

logger = logging.getLogger(__name__)

# The recommendation engine lives outside the Django apps (machine/).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "machine"))
import recommender  # noqa: E402


@login_required
def home(request):
    preference = MusicPreference.objects.filter(
        user=request.user, completed=True
    ).first()
    if preference is None:
        return redirect("music_preferences")

    answers = answers_from_preference(preference)
    context = {
        "summary": summary_from_preference(preference),
        "answers": answers,
    }
    try:
        results, meta = recommender.recommend(answers, k=20)
        context["results"] = results
        context["candidate_count"] = meta["candidates"]
    except Exception:
        logger.exception("recommendation failed for user %s", request.user.username)
        context["error"] = (
            "We couldn't build your recommendations right now. Please try again later."
        )

    return render(request, "home.html", context)
