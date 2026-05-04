from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.assessment.question_bank import DEFAULT_QUESTION_BANK
from app.coding.problem_bank import DEFAULT_CODING_PROBLEM_BANK
from app.db.models import SkillRoadmapSnapshot, SkillRoadmapTaskProgressRecord
from app.schemas import (
    RecommendedJobInput,
    SkillRoadmapHarnessQuestionResponse,
    SkillRoadmapGenerateRequest,
    SkillRoadmapItemResponse,
    SkillRoadmapJobImpactResponse,
    SkillRoadmapProgressResponse,
    SkillRoadmapResponse,
    SkillRoadmapTaskResponse,
)
from app.services.pipeline_resume_state_service import PipelineResumeStateService


class SkillGapRoadmapService:
    def __init__(self, session: Session, owner_key: str = "pipeline-demo") -> None:
        self.session = session
        self.owner_key = owner_key

    def generate(self, request: SkillRoadmapGenerateRequest) -> SkillRoadmapResponse:
        request = self._with_saved_resume_defaults(request)
        completed = self._completed_task_ids()
        gaps = self._ordered_skill_gaps(request)
        roadmap = [self._build_item(skill, request, index, completed) for index, skill in enumerate(gaps)]
        response = self._with_overall_progress(
            SkillRoadmapResponse(target_role=request.target_role, skill_gaps=gaps, roadmap=roadmap)
        )
        self.session.add(
            SkillRoadmapSnapshot(
                owner_key=self.owner_key,
                target_role=request.target_role,
                skill_gaps_json=json.dumps(gaps),
                roadmap_json=response.model_dump_json(),
                source_json=request.model_dump_json(),
            )
        )
        self.session.commit()
        return response

    def clear(self) -> None:
        self.session.query(SkillRoadmapTaskProgressRecord).filter_by(owner_key=self.owner_key).delete()
        self.session.query(SkillRoadmapSnapshot).filter_by(owner_key=self.owner_key).delete()
        self.session.commit()

    def _with_saved_resume_defaults(self, request: SkillRoadmapGenerateRequest) -> SkillRoadmapGenerateRequest:
        latest = PipelineResumeStateService(self.session, self.owner_key).latest_analysis()
        if latest is None:
            return request
        data = request.model_dump()
        if not data["extracted_skills"]:
            data["extracted_skills"] = latest.skills
        if not data["missing_skills"]:
            data["missing_skills"] = latest.missing_keywords
        if not data["ats_score"]:
            data["ats_score"] = latest.ats.score
        if not data.get("experience_level") or data["experience_level"] == "Intermediate":
            data["experience_level"] = latest.experience_level
        if not data.get("target_role"):
            data["target_role"] = latest.selected_role
        return SkillRoadmapGenerateRequest(**data)

    def latest(self) -> SkillRoadmapResponse:
        snapshot = (
            self.session.query(SkillRoadmapSnapshot)
            .filter_by(owner_key=self.owner_key)
            .order_by(SkillRoadmapSnapshot.id.desc())
            .first()
        )
        if snapshot is None:
            latest = PipelineResumeStateService(self.session, self.owner_key).latest_analysis()
            if latest is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")
            return self.generate(
                SkillRoadmapGenerateRequest(
                    extracted_skills=latest.skills,
                    missing_skills=latest.missing_keywords,
                    ats_score=latest.ats.score,
                    target_role=latest.selected_role,
                    recommended_jobs=self._default_recommended_jobs(
                        latest.selected_role,
                        latest.suggested_roles,
                        latest.missing_keywords,
                        latest.skills,
                    ),
                    skill_breakdown={self._normalize(skill): 0.0 for skill in latest.missing_keywords},
                    experience_level=latest.experience_level,
                )
            )
        response = SkillRoadmapResponse.model_validate_json(snapshot.roadmap_json)
        return self._apply_progress(response)

    def update_progress(self, task_id: str, status_value: str, proof_summary: str | None) -> SkillRoadmapProgressResponse:
        self._latest_snapshot()
        progress = (
            self.session.query(SkillRoadmapTaskProgressRecord)
            .filter_by(owner_key=self.owner_key, task_id=task_id)
            .one_or_none()
        )
        if progress is None:
            progress = SkillRoadmapTaskProgressRecord(
                owner_key=self.owner_key,
                task_id=task_id,
                status=status_value,
                proof_summary=proof_summary,
            )
            self.session.add(progress)
        else:
            progress.status = status_value
            progress.proof_summary = proof_summary
        self.session.commit()
        return self.progress()

    def progress(self) -> SkillRoadmapProgressResponse:
        roadmap = self.latest()
        total = sum(len(item.daily_tasks) for item in roadmap.roadmap)
        completed = sum(1 for item in roadmap.roadmap for task in item.daily_tasks if task.status == "completed")
        percent = round((completed / total) * 100, 2) if total else 0.0
        return SkillRoadmapProgressResponse(
            completed_tasks=completed,
            total_tasks=total,
            progress_percent=percent,
            badges=self._badges(completed, percent),
            streak_days=1 if completed else 0,
        )

    def _latest_snapshot(self) -> SkillRoadmapSnapshot:
        snapshot = (
            self.session.query(SkillRoadmapSnapshot)
            .filter_by(owner_key=self.owner_key)
            .order_by(SkillRoadmapSnapshot.id.desc())
            .first()
        )
        if snapshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")
        return snapshot

    def _apply_progress(self, response: SkillRoadmapResponse) -> SkillRoadmapResponse:
        completed = self._completed_task_ids()
        items = []
        for item in response.roadmap:
            tasks = [
                task.model_copy(update={"status": "completed" if task.task_id in completed else task.status})
                for task in item.daily_tasks
            ]
            done = sum(1 for task in tasks if task.status == "completed")
            percent = round((done / len(tasks)) * 100, 2) if tasks else 0.0
            items.append(item.model_copy(update={"daily_tasks": tasks, "progress_percent": percent}))
        return self._with_overall_progress(response.model_copy(update={"roadmap": items}))

    def _with_overall_progress(self, response: SkillRoadmapResponse) -> SkillRoadmapResponse:
        total = sum(len(item.daily_tasks) for item in response.roadmap)
        completed = sum(1 for item in response.roadmap for task in item.daily_tasks if task.status == "completed")
        percent = round((completed / total) * 100, 2) if total else 0.0
        return response.model_copy(update={"overall_progress_percent": percent, "badges": self._badges(completed, percent), "streak_days": 1 if completed else 0})

    def _completed_task_ids(self) -> set[str]:
        records = (
            self.session.query(SkillRoadmapTaskProgressRecord)
            .filter_by(owner_key=self.owner_key, status="completed")
            .all()
        )
        return {record.task_id for record in records}

    def _ordered_skill_gaps(self, request: SkillRoadmapGenerateRequest) -> list[str]:
        skills: dict[str, str] = {}
        for skill in [*request.missing_skills, *request.weak_areas]:
            normalized = self._normalize(skill)
            if normalized and normalized not in skills:
                skills[normalized] = self._display_skill(skill)

        def sort_key(item: tuple[str, str]) -> tuple[int, int, int, str]:
            normalized, display = item
            priority_rank = {"High": 0, "Medium": 1, "Low": 2}[self._priority(display, request)]
            return (
                priority_rank,
                -self._job_count(display, request.recommended_jobs),
                0 if normalized in {self._normalize(skill) for skill in request.weak_areas} else 1,
                display.lower(),
            )

        return [display for _, display in sorted(skills.items(), key=sort_key)]

    def _build_item(
        self,
        skill: str,
        request: SkillRoadmapGenerateRequest,
        index: int,
        completed: set[str],
    ) -> SkillRoadmapItemResponse:
        priority = self._priority(skill, request)
        hf_details = self._generate_with_hugging_face(skill, request)
        duration = "1 week" if priority == "High" else "4 days" if priority == "Medium" else "2 days"
        concepts = self._clean_list(hf_details.get("concepts")) or self._concepts(skill)
        practice = self._practice_tasks(skill, request.target_role)
        steps = self._clean_list(hf_details.get("steps")) or [
            f"Learn the core {skill} concepts used in {request.target_role} roles.",
            f"Complete targeted practice for {skill} and write short notes on mistakes.",
            f"Build and deploy a mini project that proves {skill}.",
            "Add measurable proof to the resume and recalculate job match.",
        ]
        daily_tasks = self._daily_tasks(skill, index, priority, completed, self._clean_list(hf_details.get("daily_tasks")))
        impact = self._job_impact(skill, request.recommended_jobs)
        score = request.skill_breakdown.get(self._normalize(skill), request.skill_breakdown.get(skill, 0.0))
        reason_parts = []
        if self._normalize(skill) in {self._normalize(item) for item in request.missing_skills}:
            reason_parts.append(f"Missing in job matching for {request.target_role}")
        if self._normalize(skill) in {self._normalize(item) for item in request.weak_areas} or 0 < score < 60:
            reason_parts.append(f"low test performance ({round(score)}%)")
        if impact.impacted_job_count:
            reason_parts.append(f"required by {impact.impacted_job_count} matched jobs")
        reason = " and ".join(reason_parts) or f"Improves practical readiness for {request.target_role}"
        done = sum(1 for task in daily_tasks if task.status == "completed")
        progress = round((done / len(daily_tasks)) * 100, 2) if daily_tasks else 0.0
        return SkillRoadmapItemResponse(
            skill=skill,
            priority=priority,
            duration=duration,
            concepts=concepts,
            practice_tasks=practice,
            steps=steps,
            project=str(hf_details.get("project") or self._project(skill, request.target_role)),
            resources=self._resources(skill),
            resource_queries=self._resource_queries(skill, request),
            harness_questions=self._harness_questions(skill, request),
            daily_tasks=daily_tasks,
            reason=reason,
            job_impact=impact,
            progress_percent=progress,
        )

    def _generate_with_hugging_face(self, skill: str, request: SkillRoadmapGenerateRequest) -> dict:
        model = os.getenv("HUGGINGFACE_ROADMAP_MODEL", "google/flan-t5-small")
        token = os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_TOKEN")
        if os.getenv("HUGGINGFACE_ROADMAP_DISABLED", "").lower() == "true":
            return {}
        if not token and os.getenv("HUGGINGFACE_ALLOW_ANONYMOUS", "").lower() != "true":
            return {}

        prompt = (
            "Generate a concise practical learning roadmap as JSON only. "
            "Use keys concepts, steps, project, daily_tasks. "
            f"Skill: {skill}. Target role: {request.target_role}. "
            f"Current skills: {', '.join(request.extracted_skills[:8])}. "
            f"Missing skills: {', '.join(request.missing_skills[:8])}. "
            f"Weak areas: {', '.join(request.weak_areas[:8])}. "
            "Daily tasks must be concrete one-line actions."
        )
        payload = json.dumps(
            {
                "inputs": prompt,
                "parameters": {"max_new_tokens": 220, "temperature": 0.35, "return_full_text": False},
                "options": {"wait_for_model": True},
            }
        ).encode("utf-8")
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            request_obj = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(request_obj, timeout=8) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return {}

        generated = self._extract_generated_text(body)
        return self._parse_hf_details(generated)

    def _extract_generated_text(self, body: str) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                return str(first.get("generated_text") or first.get("summary_text") or "")
        if isinstance(payload, dict):
            return str(payload.get("generated_text") or payload.get("summary_text") or payload.get("text") or "")
        return ""

    def _parse_hf_details(self, text: str) -> dict:
        if not text:
            return {}
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
        lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
        return {"steps": lines[:4]} if lines else {}

    def _clean_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:8]

    def _daily_tasks(
        self,
        skill: str,
        index: int,
        priority: str,
        completed: set[str],
        generated_actions: list[str] | None = None,
    ) -> list[SkillRoadmapTaskResponse]:
        day_count = 5 if priority == "High" else 3
        actions = (generated_actions or [
            "Learn basics and write a one-page checklist",
            "Practice with two small exercises",
            "Build the first project slice",
            "Connect the skill to a realistic job workflow",
            "Deploy or document proof and update resume bullets",
        ])[:day_count]
        slug = self._normalize(skill)
        return [
            SkillRoadmapTaskResponse(
                task_id=f"{slug}-day-{day}",
                day=day,
                title=f"Day {day}: {skill}",
                action=action,
                status="completed" if f"{slug}-day-{day}" in completed else "not_started",
            )
            for day, action in enumerate(actions, start=1)
        ]

    def _priority(self, skill: str, request: SkillRoadmapGenerateRequest) -> str:
        normalized = self._normalize(skill)
        missing = normalized in {self._normalize(item) for item in request.missing_skills}
        weak = normalized in {self._normalize(item) for item in request.weak_areas}
        score = request.skill_breakdown.get(normalized, request.skill_breakdown.get(skill, 0.0))
        if missing or weak or (0 < score < 50):
            return "High"
        if 50 <= score < 75:
            return "Medium"
        return "Low"

    def _job_count(self, skill: str, jobs: list[RecommendedJobInput]) -> int:
        normalized = self._normalize(skill)
        return sum(1 for job in jobs if normalized in {self._normalize(item) for item in job.required_skills})

    def _job_impact(self, skill: str, jobs: list[RecommendedJobInput]) -> SkillRoadmapJobImpactResponse:
        normalized = self._normalize(skill)
        impacted = [job for job in jobs if normalized in {self._normalize(item) for item in job.required_skills}]
        lift = min(20, 6 + len(impacted) * 4)
        names = [job.title for job in impacted]
        return SkillRoadmapJobImpactResponse(
            impacted_job_count=len(impacted),
            estimated_match_lift_percent=lift,
            jobs=names,
            summary=f"Learning {skill} increases your match score for {len(impacted)} jobs by ~{lift}%",
        )

    def _concepts(self, skill: str) -> list[str]:
        key = self._normalize(skill)
        concepts = {
            "rest_api": ["HTTP methods", "status codes", "request validation", "auth basics"],
            "system_design": ["scalability", "caching", "queues", "database trade-offs"],
            "testing": ["unit tests", "integration tests", "test data", "CI checks"],
        }
        return concepts.get(key, [f"{skill} fundamentals", "common mistakes", "production usage", "resume proof"])

    def _practice_tasks(self, skill: str, role: str) -> list[str]:
        return [
            f"Solve 3 focused {skill} drills for {role}.",
            f"Review one production example of {skill}.",
            f"Explain the trade-offs of {skill} in an interview answer.",
        ]

    def _project(self, skill: str, role: str) -> str:
        key = self._normalize(skill)
        projects = {
            "rest_api": "Build a Todo API with CRUD operations, validation, and deployment.",
            "system_design": "Design and document a scalable placement analytics service.",
            "testing": "Add unit and integration tests to a backend API with CI reporting.",
        }
        return projects.get(key, f"Build a {role} mini-project that proves {skill} with measurable output.")

    def _resources(self, skill: str) -> list[str]:
        key = self._normalize(skill)
        resources = {
            "rest_api": ["https://restfulapi.net/", "https://developer.mozilla.org/en-US/docs/Web/HTTP"],
            "system_design": ["https://github.com/donnemartin/system-design-primer", "https://roadmap.sh/system-design"],
            "testing": ["https://docs.pytest.org/", "https://testing-library.com/docs/"],
        }
        return resources.get(key, ["https://roadmap.sh/", "YouTube tutorials"])

    def _resource_queries(self, skill: str, request: SkillRoadmapGenerateRequest) -> list[str]:
        role = request.target_role
        level = request.experience_level.lower()
        return [
            f"{skill} practical tutorial for {role}",
            f"{skill} interview coding questions {level}",
            f"{role} project using {skill} resume proof",
            f"{skill} docs examples testing deployment",
        ]

    def _harness_questions(
        self,
        skill: str,
        request: SkillRoadmapGenerateRequest,
    ) -> list[SkillRoadmapHarnessQuestionResponse]:
        normalized_targets = set(self._expanded_skill_terms(skill))
        role_terms = set(self._expanded_skill_terms(request.target_role))

        scored = []
        for problem in DEFAULT_CODING_PROBLEM_BANK.list_public():
            problem_terms = set()
            for tag in problem["skill_tags"]:
                problem_terms.update(self._expanded_skill_terms(tag))
            problem_terms.update(self._expanded_skill_terms(problem["title"]))
            score = len(problem_terms & normalized_targets) * 3
            if score == 0:
                score = len(problem_terms & role_terms)
            if problem["difficulty"] == "medium":
                score += 1
            if score:
                scored.append((score, problem))
        scored.sort(key=lambda item: (-item[0], item[1]["difficulty"], item[1]["title"]))

        selected = [
            SkillRoadmapHarnessQuestionResponse(
                problem_id=problem["problem_id"],
                title=problem["title"],
                difficulty=problem["difficulty"],
                reason=f"Targets {skill} with hidden backend tests in the coding harness.",
            )
            for _, problem in scored[:3]
        ]
        if selected:
            return selected

        public_questions = DEFAULT_QUESTION_BANK.list_public()
        fallback = [
            question
            for question in public_questions
            if self._normalize(question["skill_tag"]) in normalized_targets
        ][:2]
        return [
            SkillRoadmapHarnessQuestionResponse(
                problem_id=question["question_id"],
                title=question["prompt"],
                difficulty=question["difficulty_band"],
                reason=f"Adaptive assessment question for {skill}; use it before the coding harness task.",
            )
            for question in fallback
        ]

    def _expanded_skill_terms(self, value: str) -> list[str]:
        normalized = self._normalize(value)
        aliases = {
            "rest_api": ["rest_api", "api", "apis", "backend", "idempotency"],
            "api": ["rest_api", "api", "apis", "backend", "idempotency"],
            "apis": ["rest_api", "api", "apis", "backend", "idempotency"],
            "system_design": ["system_design", "scalability", "architecture", "queues"],
            "testing": ["testing", "tests", "qa"],
            "sql": ["sql", "analytics", "dashboards"],
            "react": ["react", "frontend", "dashboards"],
            "frontend_developer": ["frontend", "react", "javascript", "css", "accessibility"],
            "backend_sde": ["backend", "api", "apis", "sql", "idempotency"],
            "full_stack_developer": ["frontend", "backend", "api", "react", "sql"],
            "job_matching": ["job_matching", "ats", "sets"],
            "ats": ["job_matching", "ats", "sets"],
            "data_structures": ["data_structures", "dsa", "arrays", "stack", "strings"],
        }
        return [normalized, *aliases.get(normalized, [])]

    def _default_recommended_jobs(
        self,
        selected_role: str,
        suggested_roles: list[str],
        missing_skills: list[str],
        current_skills: list[str],
    ) -> list[RecommendedJobInput]:
        roles = list(dict.fromkeys([selected_role, *suggested_roles]))[:4] or [selected_role or "Target Role"]
        return [
            RecommendedJobInput(
                title=role,
                match_score=max(45, 72 - index * 7),
                required_skills=list(dict.fromkeys([*missing_skills[:4], *current_skills[:3]])),
            )
            for index, role in enumerate(roles)
        ]

    def _badges(self, completed: int, percent: float) -> list[str]:
        badges = []
        if completed >= 1:
            badges.append("First Task Completed")
        if percent >= 50:
            badges.append("Halfway Roadmap")
        if percent >= 100:
            badges.append("Job Match Ready")
        return badges

    def _display_skill(self, skill: str) -> str:
        text = re.sub(r"[_-]+", " ", skill.strip())
        known = {"rest api": "REST API", "sql": "SQL", "api": "API", "apis": "APIs"}
        return known.get(text.lower(), text.title())

    def _normalize(self, skill: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", skill.strip().lower()).strip("_")
