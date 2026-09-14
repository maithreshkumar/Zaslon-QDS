from zaslon_shared.config import settings


def active_threshold() -> dict:
    return {"value": settings.verification_threshold, "source": settings.threshold_source,
            "proven_security_bound": False}

