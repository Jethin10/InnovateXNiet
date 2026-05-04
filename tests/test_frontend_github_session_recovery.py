from pathlib import Path


def test_github_sync_recovers_stale_demo_session() -> None:
    overlay = Path("frontend_original/app/components/product/ProductFeatureOverlay.tsx").read_text()

    assert "resetDemoSession" in overlay
    assert "isMissingStudentError" in overlay
    assert "runWithFreshSessionOnMissingStudent" in overlay
    assert "Student not found" in overlay
    assert "runWithFreshSessionOnMissingStudent((session) => connectGithubWithSession(session))" in overlay
