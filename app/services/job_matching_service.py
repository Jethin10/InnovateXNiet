from __future__ import annotations

import hashlib
import html
import json
import math
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas import (
    JobListingResponse,
    JobMatchRequest,
    JobMatchResponse,
    JobsFetchResponse,
    MatchedJobResponse,
)
from app.services.pipeline_resume_state_service import PipelineResumeStateService
from trust_ml.roadmap import RoleProfileStore


SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "node": "node.js",
    "nodejs": "node.js",
    "reactjs": "react",
    "rest api": "rest api",
    "apis": "api",
    "data structures": "data structures",
    "system design": "system design",
}

COMMON_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "next.js", "node.js", "express",
    "fastapi", "django", "flask", "sql", "postgresql", "mysql", "mongodb", "redis",
    "rest api", "api", "graphql", "html", "css", "tailwind", "accessibility", "testing",
    "jest", "cypress", "playwright", "docker", "kubernetes", "aws", "azure", "gcp",
    "linux", "git", "github", "ci/cd", "devops", "data visualization", "excel",
    "power bi", "tableau", "statistics", "machine learning", "pandas", "numpy",
    "system design", "data structures", "algorithms", "security", "qa automation",
}


@dataclass(frozen=True)
class ProfileSignals:
    skills: list[str]
    resume_text: str
    ats_score: float
    test_score: float
    trust_score: float
    selected_role: str


class JobMatchingService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def fetch_jobs(self, query: str = "", location: str = "", remote: bool | None = None, limit: int = 12) -> JobsFetchResponse:
        profile = self._saved_profile()
        resolved_query = query.strip() or profile.selected_role or "software developer"
        resolved_location = location.strip() or "India"

        external = self._fetch_jsearch(resolved_query, resolved_location, remote, limit)
        if external:
            return JobsFetchResponse(query=resolved_query, location=resolved_location, source="jsearch", jobs=external[:limit])

        open_jobs = self._fetch_arbeitnow(resolved_query, resolved_location, remote, limit)
        if open_jobs:
            if len(open_jobs) < limit:
                seen = {job.job_id for job in open_jobs}
                for fallback in self._fallback_jobs(resolved_query, resolved_location, remote, limit):
                    if fallback.job_id not in seen:
                        open_jobs.append(fallback)
                    if len(open_jobs) >= limit:
                        break
            return JobsFetchResponse(query=resolved_query, location=resolved_location, source="arbeitnow", jobs=open_jobs[:limit])

        return JobsFetchResponse(
            query=resolved_query,
            location=resolved_location,
            source="fallback",
            jobs=self._fallback_jobs(resolved_query, resolved_location, remote, limit),
        )

    def match_jobs(self, request: JobMatchRequest) -> JobMatchResponse:
        profile = self._profile_from_request(request)
        jobs = request.jobs or self.fetch_jobs(profile.selected_role, request.location, request.remote, request.limit).jobs
        matched = [self._score_job(job, profile) for job in jobs]
        if request.remote is not None:
            matched = [job for job in matched if job.remote == request.remote]
        if request.location.strip():
            needle = request.location.strip().lower()
            matched = [job for job in matched if needle in job.location.lower() or job.remote]
        matched = [job for job in matched if job.match_score >= request.min_match_score]
        matched.sort(key=lambda item: item.match_score, reverse=True)
        return JobMatchResponse(
            source="jsearch_or_fallback",
            profile_role=profile.selected_role,
            filters={
                "location": request.location,
                "remote": request.remote,
                "min_match_score": request.min_match_score,
                "limit": request.limit,
            },
            jobs=matched[: max(1, min(request.limit, 25))],
        )

    def recommended_jobs(self, location: str = "", remote: bool | None = None, limit: int = 8) -> JobMatchResponse:
        profile = self._saved_profile()
        return self.match_jobs(
            JobMatchRequest(
                skills=profile.skills,
                resume_text=profile.resume_text,
                ats_score=profile.ats_score,
                test_score=profile.test_score,
                trust_score=profile.trust_score,
                selected_role=profile.selected_role,
                location=location,
                remote=remote,
                limit=limit,
            )
        )

    def _fetch_jsearch(
        self,
        query: str,
        location: str,
        remote: bool | None,
        limit: int,
    ) -> list[JobListingResponse]:
        if not self.settings.rapidapi_key:
            return []
        params = {
            "query": f"{query} in {location}",
            "page": "1",
            "num_pages": "1",
            "date_posted": "month",
        }
        if remote is True:
            params["remote_jobs_only"] = "true"
        url = f"https://{self.settings.jsearch_host}/search?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "X-RapidAPI-Key": self.settings.rapidapi_key,
                "X-RapidAPI-Host": self.settings.jsearch_host,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=0.75) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        jobs: list[JobListingResponse] = []
        for item in payload.get("data", [])[: max(limit, 1)]:
            description = item.get("job_description") or ""
            title = item.get("job_title") or "Untitled role"
            company = item.get("employer_name") or "Unknown company"
            location_text = item.get("job_city") or item.get("job_country") or location or "Remote"
            jobs.append(
                JobListingResponse(
                    job_id=str(item.get("job_id") or self._stable_id(title, company, description)),
                    title=title,
                    company=company,
                    location=location_text,
                    description=description,
                    apply_url=item.get("job_apply_link"),
                    remote=bool(item.get("job_is_remote")),
                    source="jsearch",
                    required_skills=self._extract_skills(f"{title} {description}"),
                )
            )
        return jobs

    def _fetch_arbeitnow(
        self,
        query: str,
        location: str,
        remote: bool | None,
        limit: int,
    ) -> list[JobListingResponse]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        request = urllib.request.Request(url, headers={"User-Agent": "placement-trust/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=1.25) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        query_terms = self._query_terms(query)
        location_terms = self._query_terms(location)
        jobs: list[JobListingResponse] = []
        for item in payload.get("data", [])[: max(limit * 6, limit, 1)]:
            title = item.get("title") or "Untitled role"
            company = item.get("company_name") or "Unknown company"
            description = self._plain_text(item.get("description") or "")
            location_text = item.get("location") or ("Remote" if item.get("remote") else location or "Unknown")
            is_remote = bool(item.get("remote")) or "remote" in location_text.lower()
            searchable = f"{title} {company} {description} {' '.join(item.get('tags') or [])}".lower()

            if remote is not None and is_remote != remote:
                continue
            if query_terms and not any(term in searchable for term in query_terms):
                continue
            if location_terms and not is_remote and not any(term in location_text.lower() for term in location_terms):
                continue

            jobs.append(
                JobListingResponse(
                    job_id=str(item.get("slug") or self._stable_id(title, company, description)),
                    title=title,
                    company=company,
                    location=location_text,
                    description=description,
                    apply_url=item.get("url"),
                    remote=is_remote,
                    source="arbeitnow",
                    required_skills=self._extract_skills(f"{title} {description} {' '.join(item.get('tags') or [])}"),
                )
            )
            if len(jobs) >= limit:
                break
        return jobs

    def _score_job(self, job: JobListingResponse, profile: ProfileSignals) -> MatchedJobResponse:
        required = job.required_skills or self._extract_skills(f"{job.title} {job.description}")
        candidate = {self._normalize_skill(skill) for skill in profile.skills if self._normalize_skill(skill)}
        required_set = {self._normalize_skill(skill) for skill in required if self._normalize_skill(skill)}
        matched = sorted(candidate & required_set)
        missing = sorted(required_set - candidate)
        skill_match = (len(matched) / len(required_set) * 100) if required_set else 0.0
        semantic = self._cosine_similarity(profile.resume_text, job.description)
        score = (
            0.4 * skill_match
            + 0.2 * self._clamp_score(profile.test_score)
            + 0.2 * self._clamp_score(profile.ats_score)
            + 0.2 * self._clamp_score(profile.trust_score)
        )
        if semantic:
            semantic_boosted_score = score * 0.88 + semantic * 100 * 0.12
            score = min(100.0, max(score, semantic_boosted_score))
        explanation = self._explain(job.title, matched, missing, semantic)
        return MatchedJobResponse(
            **job.model_dump(exclude={"required_skills"}),
            required_skills=sorted(required_set),
            skill_match_percent=round(skill_match, 1),
            match_score=round(score, 1),
            explanation=explanation,
            matched_skills=matched,
            missing_skills=missing[:8],
            semantic_similarity=round(semantic, 3),
        )

    def _profile_from_request(self, request: JobMatchRequest) -> ProfileSignals:
        saved = self._saved_profile()
        provided = request.model_fields_set
        return ProfileSignals(
            skills=request.skills or saved.skills,
            resume_text=request.resume_text or saved.resume_text,
            ats_score=request.ats_score if "ats_score" in provided else saved.ats_score,
            test_score=request.test_score if "test_score" in provided else saved.test_score,
            trust_score=request.trust_score if "trust_score" in provided else saved.trust_score,
            selected_role=request.selected_role or saved.selected_role,
        )

    def _saved_profile(self) -> ProfileSignals:
        state = PipelineResumeStateService(self.session)
        latest = state.latest_analysis()
        record = state.latest_record()
        if latest:
            return ProfileSignals(
                skills=latest.skills,
                resume_text=record.raw_text if record else "",
                ats_score=float(latest.ats.score),
                test_score=0.0,
                trust_score=float(latest.model_readiness_score),
                selected_role=latest.selected_role,
            )
        return ProfileSignals(
            skills=["python", "react", "sql", "api", "data structures"],
            resume_text="Python React SQL API data structures placement analytics dashboard",
            ats_score=55.0,
            test_score=0.0,
            trust_score=55.0,
            selected_role="Software Developer",
        )

    def _fallback_jobs(self, query: str, location: str, remote: bool | None, limit: int) -> list[JobListingResponse]:
        role = query or "Software Developer"
        role_skills = self._role_keywords(role)
        templates = [
            ("Associate Software Engineer", "Nexora Systems", "Bengaluru, India", ["python", "sql", "api", "git", "testing"]),
            ("Frontend Developer", "PixelGrid Labs", "Remote", ["react", "javascript", "typescript", "css", "accessibility", "testing"]),
            ("Backend Developer", "CloudForge", "Hyderabad, India", ["python", "fastapi", "postgresql", "rest api", "docker"]),
            ("Data Analyst", "MetricWorks", "Remote", ["sql", "python", "excel", "statistics", "data visualization", "power bi"]),
            ("Full Stack Engineer", "LaunchStack", "Pune, India", ["react", "node.js", "sql", "api", "system design"]),
            ("QA Automation Engineer", "TestPilot", "Remote", ["testing", "playwright", "javascript", "ci/cd", "git"]),
        ]
        jobs: list[JobListingResponse] = []
        for title, company, loc, skills in templates:
            combined = list(dict.fromkeys([*skills, *role_skills[:3]]))
            is_remote = loc.lower() == "remote"
            if remote is not None and is_remote != remote:
                continue
            description = (
                f"{company} is hiring a {title} for {role}. Required skills include "
                f"{', '.join(combined)}. The work involves practical delivery, code review, "
                "debugging, product collaboration, and measurable ownership."
            )
            jobs.append(
                JobListingResponse(
                    job_id=self._stable_id(title, company, description),
                    title=title,
                    company=company,
                    location=loc if not location else f"{loc} / {location}",
                    description=description,
                    apply_url=None,
                    remote=is_remote,
                    source="fallback",
                    required_skills=combined,
                )
            )
        return jobs[: max(1, min(limit, 25))]

    def _role_keywords(self, role: str) -> list[str]:
        store = RoleProfileStore.default()
        try:
            profile = store.get(role)
            return [self._normalize_skill(skill) for skill in profile.ats_keywords]
        except Exception:
            return self._extract_skills(role)

    def _extract_skills(self, text: str) -> list[str]:
        lowered = f" {text.lower().replace('-', ' ')} "
        found = set()
        for skill in COMMON_SKILLS:
            token = skill.lower().replace("-", " ")
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered):
                found.add(self._normalize_skill(skill))
        return sorted(found)

    def _cosine_similarity(self, left: str, right: str) -> float:
        left_vec = self._term_vector(left)
        right_vec = self._term_vector(right)
        if not left_vec or not right_vec:
            return 0.0
        dot = sum(left_vec.get(term, 0) * right_vec.get(term, 0) for term in set(left_vec) | set(right_vec))
        left_norm = math.sqrt(sum(value * value for value in left_vec.values()))
        right_norm = math.sqrt(sum(value * value for value in right_vec.values()))
        return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0

    def _term_vector(self, text: str) -> dict[str, int]:
        terms = re.findall(r"[a-zA-Z][a-zA-Z+#.]{1,}", text.lower())
        stop = {"and", "the", "for", "with", "from", "that", "this", "will", "role", "work"}
        vector: dict[str, int] = {}
        for term in terms:
            if term in stop:
                continue
            vector[term] = vector.get(term, 0) + 1
        return vector

    def _plain_text(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _query_terms(self, value: str) -> list[str]:
        stop = {"in", "and", "or", "the", "a", "an", "jobs", "job"}
        return [
            term
            for term in re.findall(r"[a-z0-9+#.]{2,}", value.lower())
            if term not in stop
        ]

    def _normalize_skill(self, skill: str) -> str:
        value = skill.strip().lower().replace("_", " ").replace("-", " ")
        value = re.sub(r"\s+", " ", value)
        return SKILL_ALIASES.get(value, value)

    def _stable_id(self, *parts: str) -> str:
        return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:16]

    def _clamp_score(self, value: float) -> float:
        return max(0.0, min(100.0, float(value or 0.0)))

    def _explain(self, title: str, matched: Iterable[str], missing: Iterable[str], semantic: float) -> str:
        matched_list = list(matched)
        missing_list = list(missing)
        if matched_list:
            base = f"You fit {title} because your profile shows {', '.join(matched_list[:4])}."
        else:
            base = f"{title} is a stretch role, but it is still useful for discovering target gaps."
        if missing_list:
            base += f" Missing skills include {', '.join(missing_list[:4])}."
        if semantic >= 0.25:
            base += " Resume wording is also semantically close to the job description."
        return base
