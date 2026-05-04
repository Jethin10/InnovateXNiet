from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import textwrap
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.coding.problem_bank import DEFAULT_CODING_PROBLEM_BANK, SUPPORTED_CODING_LANGUAGES, CodingProblem, CodingTestCase
from app.db.models import EvidenceVerificationRecord, StudentProfile
from app.schemas import CodingSubmissionRequest, CodingSubmissionResponse, CodingTestResultResponse


BLOCKED_CALLS = {"open", "eval", "exec", "compile", "__import__", "input", "globals", "locals"}
SUPPORTED_LANGUAGE_IDS = {language["id"] for language in SUPPORTED_CODING_LANGUAGES}
LANGUAGE_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "c++": "cpp",
    "cplusplus": "cpp",
}
LANGUAGE_LABELS = {language["id"]: language["label"] for language in SUPPORTED_CODING_LANGUAGES}


class CodingHarnessService:
    def __init__(self, session: Session | None, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings

    def list_problems(self) -> list[dict]:
        return DEFAULT_CODING_PROBLEM_BANK.list_public()

    def submit(self, student_id: int, request: CodingSubmissionRequest) -> CodingSubmissionResponse:
        if self.session is None:
            raise RuntimeError("Database session is required for coding submissions")
        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        language = self._normalize_language(request.language)

        try:
            problem = DEFAULT_CODING_PROBLEM_BANK.require(request.problem_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coding problem not found") from exc

        if language != "python" and not (self.settings and self.settings.judge0_base_url):
            label = LANGUAGE_LABELS[language]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{label} submissions require Judge0 to be configured",
            )

        integrity_flags = self._validate_code(request.code, problem) if language == "python" else self._validate_text_code(request.code, problem)
        if integrity_flags:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=integrity_flags[0])
        proctoring_flags = self._proctoring_flags(request)
        blocking_flags = [
            flag
            for flag in proctoring_flags
            if flag in {
                "fullscreen_not_active",
                "screen_share_not_active",
                "screen_share_surface_not_monitor",
                "camera_not_active",
                "copy_paste_attempt",
                "copy_paste_not_blocked",
                "hf_multiple_people_visible",
                "hf_no_person_visible",
                "hf_phone_visible",
            }
        ]
        if blocking_flags:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=blocking_flags[0])

        public_results = self._run_cases(request.code, language, problem, problem.public_cases, include_details=True)
        hidden_results = self._run_cases(request.code, language, problem, problem.hidden_cases, include_details=False)
        passed_public = sum(1 for result in public_results if result.passed)
        passed_hidden = sum(1 for result in hidden_results if result.passed)
        total_cases = len(public_results) + len(hidden_results)
        score = round(((passed_public + passed_hidden) / total_cases) * 100)
        passed = score == 100
        submission_id = str(uuid.uuid4())

        self._persist_submission_summary(
            student_id,
            {
                "submission_id": submission_id,
                "problem_id": problem.problem_id,
                "title": problem.title,
                "language": language,
                "passed": passed,
                "score": score,
                "skill_tags": list(problem.skill_tags),
                "proctoring_checks": request.proctoring_checks,
                "proctoring_events": [event.model_dump() for event in request.proctoring_events],
                "integrity_flags": proctoring_flags,
            },
        )

        return CodingSubmissionResponse(
            submission_id=submission_id,
            problem_id=problem.problem_id,
            passed=passed,
            score=score,
            public_results=public_results,
            hidden_passed_count=passed_hidden,
            hidden_total_count=len(hidden_results),
            integrity_flags=proctoring_flags,
            skill_tags=list(problem.skill_tags),
        )

    def _normalize_language(self, language: str) -> str:
        normalized = language.strip().lower().replace(" ", "")
        normalized = LANGUAGE_ALIASES.get(normalized, normalized)
        if normalized not in SUPPORTED_LANGUAGE_IDS:
            supported = ", ".join(language["label"] for language in SUPPORTED_CODING_LANGUAGES)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported language. Choose one of: {supported}",
            )
        return normalized

    def _proctoring_flags(self, request: CodingSubmissionRequest) -> list[str]:
        checks = request.proctoring_checks or {}
        flags: list[str] = []
        if not checks.get("fullscreen_active"):
            flags.append("fullscreen_not_active")
        if not checks.get("screen_share_active"):
            flags.append("screen_share_not_active")
        if not checks.get("screen_share_surface_monitor"):
            flags.append("screen_share_surface_not_monitor")
        if not checks.get("camera_active"):
            flags.append("camera_not_active")
        if not checks.get("copy_paste_blocked"):
            flags.append("copy_paste_not_blocked")

        for event in request.proctoring_events:
            event_type = event.event_type.strip().lower().replace(" ", "_")
            if event.count <= 0:
                continue
            if event_type in {"copy", "paste", "cut", "drop", "copy_paste"}:
                flags.append("copy_paste_attempt")
            elif event_type in {"tab_switch", "visibility_hidden", "window_blur"}:
                flags.append("focus_lost")
            elif event_type in {"fullscreen_exit"}:
                flags.append("fullscreen_exit")
            elif event_type in {"screen_share_ended"}:
                flags.append("screen_share_ended")
            elif event_type in {"camera_ended"}:
                flags.append("camera_ended")
            elif event_type.startswith("hf_"):
                flags.append(event_type)
        return list(dict.fromkeys(flags))

    def _validate_code(self, code: str, problem: CodingProblem) -> list[str]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return [f"Syntax error: {exc.msg}"]

        has_function = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return ["Imports are disabled for coding harness submissions"]
            if isinstance(node, ast.FunctionDef) and node.name == problem.function_name:
                has_function = True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
                return [f"Blocked call: {node.func.id}"]
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return ["Dunder attribute access is disabled"]
        if not has_function:
            return [f"Submission must define {problem.function_name}"]
        return []

    def _validate_text_code(self, code: str, problem: CodingProblem) -> list[str]:
        if problem.function_name not in code:
            return [f"Submission must define {problem.function_name}"]
        return []

    def _run_cases(
        self,
        code: str,
        language: str,
        problem: CodingProblem,
        cases: tuple[CodingTestCase, ...],
        *,
        include_details: bool,
    ) -> list[CodingTestResultResponse]:
        results: list[CodingTestResultResponse] = []
        for case in cases:
            raw = self._run_single_case(code, language, problem, case)
            passed = raw.get("passed", False)
            results.append(
                CodingTestResultResponse(
                    name=case.name,
                    passed=passed,
                    input=case.input if include_details else None,
                    expected=case.expected if include_details else None,
                    actual=raw.get("actual") if include_details else None,
                    error=raw.get("error") if include_details else None,
                )
            )
        return results

    def _run_single_case(self, code: str, language: str, problem: CodingProblem, case: CodingTestCase) -> dict[str, Any]:
        if self.settings and self.settings.judge0_base_url:
            return self._run_single_case_with_judge0(code, language, problem, case)
        return self._run_single_case_locally(code, problem.function_name, case)

    def _run_single_case_with_judge0(self, code: str, language: str, problem: CodingProblem, case: CodingTestCase) -> dict[str, Any]:
        assert self.settings is not None
        runner = self._build_judge0_runner(code, language, problem, case)
        payload = {
            "language_id": self._judge0_language_id(language),
            "source_code": runner,
            "stdin": "",
            "cpu_time_limit": 2,
            "cpu_extra_time": 0.5,
            "wall_time_limit": 5,
            "memory_limit": 128000,
            "stack_limit": 64000,
            "max_file_size": 1024,
            "enable_network": False,
            "redirect_stderr_to_stdout": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.judge0_api_key:
            headers["X-RapidAPI-Key"] = self.settings.judge0_api_key
        if self.settings.judge0_auth_token:
            headers["X-Auth-Token"] = self.settings.judge0_auth_token

        url = f"{self.settings.judge0_base_url.rstrip('/')}/submissions?wait=true"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            return {"passed": False, "error": f"Judge0 unavailable: {exc.reason}"}

        if result.get("compile_output"):
            return {"passed": False, "error": str(result["compile_output"]).strip()}
        if result.get("stderr"):
            return {"passed": False, "error": str(result["stderr"]).strip()}
        stdout = str(result.get("stdout") or "").strip()
        if not stdout:
            status_description = result.get("status", {}).get("description", "No output")
            return {"passed": False, "error": status_description}
        try:
            return json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            return {"passed": False, "error": "Submission produced invalid output"}

    def _judge0_language_id(self, language: str) -> int:
        assert self.settings is not None
        return {
            "c": self.settings.judge0_c_language_id,
            "cpp": self.settings.judge0_cpp_language_id,
            "java": self.settings.judge0_java_language_id,
            "javascript": self.settings.judge0_javascript_language_id,
            "python": self.settings.judge0_python_language_id,
        }[language]

    def _build_judge0_runner(self, code: str, language: str, problem: CodingProblem, case: CodingTestCase) -> str:
        payload = json.dumps({"input": case.input, "expected": case.expected})
        expected_json = json.dumps(case.expected, separators=(",", ":"))
        if language == "python":
            return textwrap.dedent(
                f"""
                import json

                {code}

                payload = {payload}
                try:
                    actual = {problem.function_name}(**payload["input"])
                    print(json.dumps({{"passed": actual == payload["expected"], "actual": actual}}))
                except Exception as exc:
                    print(json.dumps({{"passed": False, "error": str(exc)}}))
                """
            ).strip()
        if language == "javascript":
            args = ", ".join(json.dumps(value) for value in case.input.values())
            return textwrap.dedent(
                f"""
                {code}

                const expected = {json.dumps(case.expected)};
                try {{
                  const actual = {problem.function_name}({args});
                  console.log(JSON.stringify({{
                    passed: JSON.stringify(actual) === JSON.stringify(expected),
                    actual
                  }}));
                }} catch (error) {{
                  console.log(JSON.stringify({{ passed: false, error: String(error && error.message ? error.message : error) }}));
                }}
                """
            ).strip()
        if language == "java":
            return textwrap.dedent(
                f"""
                {code}

                public class Main {{
                    public static void main(String[] args) {{
                        String input = {json.dumps(payload)};
                        String expected = {json.dumps(expected_json)};
                        try {{
                            String actual = Solution.solve(input);
                            boolean passed = actual != null && actual.trim().equals(expected);
                            System.out.println("{{\\\"passed\\\":" + passed + ",\\\"actual\\\":" + jsonString(actual) + "}}");
                        }} catch (Exception exc) {{
                            System.out.println("{{\\\"passed\\\":false,\\\"error\\\":" + jsonString(exc.getMessage()) + "}}");
                        }}
                    }}

                    private static String jsonString(String value) {{
                        if (value == null) return "null";
                        return "\\\"" + value.replace("\\\\", "\\\\\\\\").replace("\\\"", "\\\\\\\"") + "\\\"";
                    }}
                }}
                """
            ).strip()
        if language == "cpp":
            return textwrap.dedent(
                f"""
                {code}

                #include <iostream>
                int main() {{
                    std::string input = {json.dumps(payload)};
                    std::string expected = {json.dumps(expected_json)};
                    try {{
                        std::string actual = solve(input);
                        bool passed = actual == expected;
                        std::cout << "{{\\\"passed\\\":" << (passed ? "true" : "false") << "}}" << std::endl;
                    }} catch (...) {{
                        std::cout << "{{\\\"passed\\\":false,\\\"error\\\":\\\"Runtime error\\\"}}" << std::endl;
                    }}
                    return 0;
                }}
                """
            ).strip()
        if language == "c":
            return textwrap.dedent(
                f"""
                #include <stdio.h>
                #include <string.h>

                {code}

                int main(void) {{
                    const char* input = {json.dumps(payload)};
                    const char* expected = {json.dumps(expected_json)};
                    const char* actual = solve(input);
                    int passed = actual != NULL && strcmp(actual, expected) == 0;
                    printf("{{\\\"passed\\\":%s}}\\n", passed ? "true" : "false");
                    return 0;
                }}
                """
            ).strip()
        raise ValueError(f"Unsupported language: {language}")

    def _run_single_case_locally(self, code: str, function_name: str, case: CodingTestCase) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            solution_path = tmp_path / "solution.py"
            runner_path = tmp_path / "runner.py"
            solution_path.write_text(code, encoding="utf-8")
            runner_path.write_text(
                textwrap.dedent(
                    """
                    import importlib.util
                    import json
                    import sys

                    solution_path = sys.argv[1]
                    function_name = sys.argv[2]
                    payload = json.loads(sys.argv[3])

                    try:
                        spec = importlib.util.spec_from_file_location("solution", solution_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        fn = getattr(module, function_name)
                        actual = fn(**payload["input"])
                        print(json.dumps({"passed": actual == payload["expected"], "actual": actual}))
                    except Exception as exc:
                        print(json.dumps({"passed": False, "error": str(exc)}))
                    """
                ).strip(),
                encoding="utf-8",
            )
            payload = json.dumps({"input": case.input, "expected": case.expected})
            try:
                process = subprocess.run(
                    [sys.executable, str(runner_path), str(solution_path), function_name, payload],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    cwd=str(tmp_path),
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return {"passed": False, "error": "Time limit exceeded"}

        if process.returncode != 0:
            return {"passed": False, "error": process.stderr.strip() or "Runtime error"}
        try:
            return json.loads(process.stdout.strip())
        except json.JSONDecodeError:
            return {"passed": False, "error": "Submission produced invalid output"}

    def _persist_submission_summary(self, student_id: int, payload: dict) -> None:
        self.session.add(
            EvidenceVerificationRecord(
                student_profile_id=student_id,
                source="coding_harness",
                handle=payload["problem_id"],
                verified=bool(payload["passed"]),
                payload_json=json.dumps(payload),
            )
        )
        self.session.commit()
