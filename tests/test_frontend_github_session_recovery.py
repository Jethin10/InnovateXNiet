from pathlib import Path


def test_github_sync_recovers_stale_or_expired_demo_session() -> None:
    overlay = Path("frontend_original/app/components/product/ProductFeatureOverlay.tsx").read_text()

    assert "resetDemoSession" in overlay
    assert "isRecoverableSessionError" in overlay
    assert "runWithFreshSessionOnRecoverableSessionError" in overlay
    assert "Student not found" in overlay
    assert "Invalid or expired access token" in overlay
    assert "runWithFreshSessionOnRecoverableSessionError((session) => connectGithubWithSession(session))" in overlay
