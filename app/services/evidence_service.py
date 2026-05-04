from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.services.github_client import GitHubCollectionRequest, collect_github_profile
from app.db.models import EvidenceVerificationRecord, StudentProfile
from app.schemas import (
    CodeforcesEvidenceRequest,
    CodeforcesEvidenceResponse,
    EvidenceSummaryResponse,
    GitHubEvidenceRequest,
    GitHubEvidenceResponse,
)


def fetch_codeforces_user_info(handle: str) -> dict:
    query = urlencode({"handles": handle})
    with urlopen(f"https://codeforces.com/api/user.info?{query}", timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_github_user(username: str) -> dict:
    with urlopen(f"https://api.github.com/users/{username}", timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_github_repositories(username: str) -> list[dict]:
    query = urlencode({"sort": "updated", "per_page": 20})
    try:
        with urlopen(f"https://api.github.com/users/{username}/repos?{query}", timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError):
        return []


class EvidenceService:
    def __init__(self, session: Session, request: Request) -> None:
        self.session = session
        self.request = request

    def verify_codeforces(
        self,
        student_id: int,
        request: CodeforcesEvidenceRequest,
    ) -> CodeforcesEvidenceResponse:
        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        client = getattr(self.request.app.state, "codeforces_client", fetch_codeforces_user_info)
        payload = client(request.handle)
        if payload.get("status") != "OK" or not payload.get("result"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Codeforces handle not verified")

        user = payload["result"][0]
        rating = user.get("rating") or user.get("maxRating")
        response = CodeforcesEvidenceResponse(
            source="codeforces",
            handle=user.get("handle", request.handle),
            verified=True,
            rating=rating,
            max_rating=user.get("maxRating"),
            rank=user.get("rank"),
        )
        record = EvidenceVerificationRecord(
            student_profile_id=student_id,
            source="codeforces",
            handle=response.handle,
            verified=True,
            rating=response.rating,
            payload_json=json.dumps(response.model_dump()),
        )
        student.coding_handle = response.handle
        self.session.add(record)
        self.session.add(student)
        self.session.commit()
        return response

    def verify_github(
        self,
        student_id: int,
        request: GitHubEvidenceRequest,
    ) -> GitHubEvidenceResponse:
        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        profile_payload = self._collect_github_profile(request)
        cached_response = profile_payload.get("cached_response")
        if cached_response:
            response = GitHubEvidenceResponse(**cached_response)
            self._store_github_response(student_id, response)
            return response

        payload = profile_payload.get("user", {})
        repositories = profile_payload.get("repositories", [])
        username = payload.get("login") or request.username
        github_profile = self._summarize_github_profile(
            repositories,
            username=username,
            authorized=bool(request.access_token or getattr(self.request.app.state.settings, "github_token", None)),
        )
        repo_count = (
            len(repositories)
            if github_profile["access_scope"] == "authorized"
            else max(len(repositories), int(payload.get("public_repos", 0) or 0))
        )
        response = GitHubEvidenceResponse(
            source="github",
            username=username,
            verified=bool(username),
            repo_count=repo_count,
            followers=payload.get("followers"),
            original_repo_count=github_profile["original_repo_count"],
            private_repo_count=github_profile["private_repo_count"],
            fork_repo_count=github_profile["fork_repo_count"],
            total_stars=github_profile["total_stars"],
            total_forks=github_profile["total_forks"],
            total_open_issues=github_profile["total_open_issues"],
            total_commits_analyzed=github_profile["total_commits_analyzed"],
            authored_commit_count=github_profile["authored_commit_count"],
            recent_commit_count=github_profile["recent_commit_count"],
            language_breakdown=github_profile["language_breakdown"],
            top_languages=github_profile["top_languages"],
            contribution_summary=github_profile["contribution_summary"],
            repositories=github_profile["repositories"],
            recent_commits=github_profile["recent_commits"],
            project_recommendations=github_profile["project_recommendations"],
            access_scope=github_profile["access_scope"],
            rate_limit_remaining=profile_payload.get("rate_limit_remaining"),
        )
        if not response.verified:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub user not verified")

        self._store_github_response(student_id, response)
        return response

    def _store_github_response(self, student_id: int, response: GitHubEvidenceResponse) -> None:
        self.session.add(
            EvidenceVerificationRecord(
                student_profile_id=student_id,
                source="github",
                handle=response.username,
                verified=True,
                rating=None,
                payload_json=json.dumps(response.model_dump()),
            )
        )
        self.session.commit()

    def _collect_github_profile(self, request: GitHubEvidenceRequest) -> dict:
        profile_client = getattr(self.request.app.state, "github_profile_client", None)
        if profile_client is not None:
            try:
                return profile_client(request)
            except HTTPError as error:
                return self._handle_github_http_error(error, request)

        legacy_client = getattr(self.request.app.state, "github_client", None)
        legacy_repos_client = getattr(self.request.app.state, "github_repos_client", None)
        if legacy_client is not None or legacy_repos_client is not None:
            username = request.username.strip()
            try:
                return {
                    "user": (legacy_client or fetch_github_user)(username),
                    "repositories": (legacy_repos_client or fetch_github_repositories)(username),
                    "rate_limit_remaining": None,
                }
            except HTTPError as error:
                return self._handle_github_http_error(error, request)

        settings = self.request.app.state.settings
        token = request.access_token or settings.github_token
        username = request.username.strip()
        if not username and not token:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub username or access token is required")

        try:
            return collect_github_profile(
                GitHubCollectionRequest(
                    username=username,
                    access_token=token,
                    include_private=request.include_private,
                    max_repositories=settings.github_max_repositories,
                    max_enriched_repositories=settings.github_max_enriched_repositories if token else min(settings.github_max_enriched_repositories, 3),
                )
            )
        except HTTPError as error:
            return self._handle_github_http_error(error, request)
        except (URLError, TimeoutError) as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub API request timed out") from error

    def _handle_github_http_error(self, error: HTTPError, request: GitHubEvidenceRequest) -> dict:
        if error.code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub user not found") from error

        detail = self._github_error_detail(error)
        if error.code == status.HTTP_403_FORBIDDEN and "rate limit" in detail.lower():
            cached_payload = self._cached_public_github_payload(request.username)
            if cached_payload:
                return {"cached_response": cached_payload}
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub rate limit reached. Add a GitHub token, or try again after the public API budget resets.",
            ) from error

        if error.code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            raise HTTPException(
                status_code=error.code,
                detail="GitHub authorization failed. Check the token permissions or use public-only access.",
            ) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub API request failed") from error

    def _github_error_detail(self, error: HTTPError) -> str:
        if error.fp is None:
            return error.reason or str(error)
        try:
            payload = json.loads(error.fp.read().decode("utf-8"))
            return str(payload.get("message") or error.reason or error)
        except Exception:
            return error.reason or str(error)

    def _cached_public_github_payload(self, username: str) -> dict | None:
        if not username.strip():
            return None
        record = (
            self.session.query(EvidenceVerificationRecord)
            .filter_by(source="github", handle=username.strip(), verified=True)
            .order_by(EvidenceVerificationRecord.id.desc())
            .first()
        )
        if record is None:
            return None
        payload = json.loads(record.payload_json)
        if payload.get("private_repo_count", 0) or payload.get("access_scope") == "authorized":
            return None
        payload["access_scope"] = "cached_public"
        payload["rate_limit_remaining"] = 0
        payload["contribution_summary"] = [
            "Using cached public GitHub evidence because the GitHub public API rate limit was reached.",
            *payload.get("contribution_summary", []),
        ]
        return payload

    def latest_summary(self, student_id: int) -> EvidenceSummaryResponse:
        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        codeforces = (
            self.session.query(EvidenceVerificationRecord)
            .filter_by(student_profile_id=student_id, source="codeforces", verified=True)
            .order_by(EvidenceVerificationRecord.id.desc())
            .first()
        )
        github = (
            self.session.query(EvidenceVerificationRecord)
            .filter_by(student_profile_id=student_id, source="github", verified=True)
            .order_by(EvidenceVerificationRecord.id.desc())
            .first()
        )
        coding_records = (
            self.session.query(EvidenceVerificationRecord)
            .filter_by(student_profile_id=student_id, source="coding_harness")
            .order_by(EvidenceVerificationRecord.id.desc())
            .all()
        )
        solved_problem_ids = {
            json.loads(record.payload_json).get("problem_id")
            for record in coding_records
            if record.verified
        }
        return EvidenceSummaryResponse(
            codeforces=json.loads(codeforces.payload_json) if codeforces is not None else None,
            github=json.loads(github.payload_json) if github is not None else None,
            coding_harness={
                "solved_count": len(solved_problem_ids),
                "latest_submission": json.loads(coding_records[0].payload_json) if coding_records else None,
            }
            if coding_records
            else None,
        )

    def _summarize_github_profile(self, repositories: list[dict], username: str, authorized: bool = False) -> dict:
        original_repos = [repo for repo in repositories if not repo.get("fork")]
        language_breakdown: dict[str, int] = {}
        for repo in original_repos:
            languages = repo.get("languages") or {}
            if languages:
                for language, bytes_count in languages.items():
                    language_breakdown[language] = language_breakdown.get(language, 0) + int(bytes_count or 0)
            else:
                language = repo.get("language")
                if language:
                    language_breakdown[language] = language_breakdown.get(language, 0) + 1

        top_languages = [
            language
            for language, _count in sorted(language_breakdown.items(), key=lambda item: (-item[1], item[0]))[:3]
        ]
        recent_originals = sorted(
            original_repos,
            key=lambda repo: repo.get("pushed_at") or "",
            reverse=True,
        )[:3]
        repository_summaries = [self._repository_summary(repo, username) for repo in original_repos]
        recent_commits = self._recent_commits(original_repos, username)
        total_commits = sum(repo["commit_count_analyzed"] for repo in repository_summaries)
        authored_commits = sum(repo["authored_commit_count"] for repo in repository_summaries)
        contribution_summary = self._contribution_summary(
            repositories=repository_summaries,
            top_languages=top_languages,
            total_commits=total_commits,
            authored_commits=authored_commits,
            private_repo_count=sum(1 for repo in repositories if repo.get("private")),
        )
        recommendations = self._github_project_recommendations(top_languages, recent_originals, repository_summaries)
        return {
            "original_repo_count": len(original_repos),
            "private_repo_count": sum(1 for repo in repositories if repo.get("private")),
            "fork_repo_count": sum(1 for repo in repositories if repo.get("fork")),
            "total_stars": sum(int(repo.get("stargazers_count") or 0) for repo in repositories),
            "total_forks": sum(int(repo.get("forks_count") or 0) for repo in repositories),
            "total_open_issues": sum(int(repo.get("open_issues_count") or 0) for repo in repositories),
            "total_commits_analyzed": total_commits,
            "authored_commit_count": authored_commits,
            "recent_commit_count": len(recent_commits),
            "language_breakdown": language_breakdown,
            "top_languages": top_languages,
            "contribution_summary": contribution_summary,
            "repositories": repository_summaries,
            "recent_commits": recent_commits,
            "project_recommendations": recommendations,
            "access_scope": "authorized" if authorized else "public",
        }

    def _repository_summary(self, repo: dict, username: str) -> dict:
        contributors = repo.get("contributors") or []
        commits = repo.get("commits") or []
        return {
            "name": repo.get("name") or "repository",
            "full_name": repo.get("full_name") or repo.get("name") or "repository",
            "url": repo.get("html_url") or "",
            "description": repo.get("description"),
            "primary_language": repo.get("language"),
            "private": bool(repo.get("private")),
            "fork": bool(repo.get("fork")),
            "stars": int(repo.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or 0),
            "open_issues": int(repo.get("open_issues_count") or 0),
            "pushed_at": repo.get("pushed_at"),
            "topics": repo.get("topics") or [],
            "languages": repo.get("languages") or {},
            "contributor_count": len(contributors),
            "commit_count_analyzed": len(commits),
            "authored_commit_count": sum(
                1
                for commit in commits
                if (commit.get("author") or {}).get("login", "").lower() == username.lower()
            ),
        }

    def _recent_commits(self, repositories: list[dict], username: str) -> list[dict]:
        commits: list[dict] = []
        for repo in repositories:
            repo_name = repo.get("name") or "repository"
            for commit in repo.get("commits") or []:
                commit_payload = commit.get("commit") or {}
                author_payload = commit_payload.get("author") or {}
                commits.append(
                    {
                        "repo": repo_name,
                        "sha": str(commit.get("sha") or "")[:9],
                        "message": str(commit_payload.get("message") or "").splitlines()[0],
                        "authored_at": author_payload.get("date"),
                        "author_login": (commit.get("author") or {}).get("login") or username,
                        "url": commit.get("html_url"),
                    }
                )
        return sorted(commits, key=lambda commit: commit.get("authored_at") or "", reverse=True)[:8]

    def _contribution_summary(
        self,
        repositories: list[dict],
        top_languages: list[str],
        total_commits: int,
        authored_commits: int,
        private_repo_count: int,
    ) -> list[str]:
        if not repositories:
            return ["No repositories were available for evidence analysis."]

        summary = [
            f"{total_commits} commits analyzed across {len(repositories)} original repositories; {authored_commits} are attributed to the connected GitHub user.",
        ]
        if top_languages:
            summary.append(f"Strongest language evidence: {', '.join(top_languages)}.")
        if private_repo_count:
            summary.append(f"{private_repo_count} private repositories were included through authorized access.")
        most_active = max(repositories, key=lambda repo: repo.get("commit_count_analyzed", 0))
        summary.append(
            f"{most_active['name']} is the strongest recent evidence repo with {most_active['commit_count_analyzed']} analyzed commits and {most_active['stars']} stars."
        )
        return summary

    def _github_project_recommendations(
        self,
        top_languages: list[str],
        repositories: list[dict],
        repository_summaries: list[dict],
    ) -> list[dict]:
        repo_names = [repo.get("name", "repository") for repo in repositories]
        languages = {language.lower() for language in top_languages}
        active_repo_names = [
            repo["name"]
            for repo in sorted(repository_summaries, key=lambda item: item.get("commit_count_analyzed", 0), reverse=True)[:3]
        ]
        evidence_repo_names = active_repo_names or repo_names
        if "python" in languages:
            return [
                {
                    "title": "Production API reliability upgrade",
                    "rationale": "Your Python repositories already show backend activity. Turn the strongest repo into recruiter-grade proof by exposing tests, architecture, API metrics, and deployment traces.",
                    "suggested_scope": [
                        "Add authenticated CRUD APIs with database migrations",
                        "Add unit and API tests that cover failure cases",
                        "Publish a README with architecture, trade-offs, and metrics",
                    ],
                    "evidence_repo_names": evidence_repo_names,
                }
            ]
        if "typescript" in languages or "javascript" in languages:
            return [
                {
                    "title": "Full-stack dashboard evidence project",
                    "rationale": "Your frontend repositories can become recruiter-facing proof by connecting them to live backend data and measurable user workflows.",
                    "suggested_scope": [
                        "Connect dashboard screens to real API endpoints",
                        "Add loading, empty, and error states",
                        "Document deployment and product decisions",
                    ],
                    "evidence_repo_names": evidence_repo_names,
                }
            ]
        return [
            {
                "title": "Evidence-backed capstone upgrade",
                "rationale": "Your repositories need clearer role alignment and proof artifacts to support the Trust Stamp.",
                "suggested_scope": [
                    "Choose one repository and define a target role story",
                    "Add tests and a concise architecture README",
                    "Record verified outcomes as roadmap proof",
                ],
                "evidence_repo_names": evidence_repo_names,
            }
        ]
