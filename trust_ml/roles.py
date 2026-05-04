from __future__ import annotations

from dataclasses import dataclass

from .schemas import RoadmapResource


@dataclass(frozen=True)
class RoleNodeBlueprint:
    node_id: str
    title: str
    skill_track: str
    summary: str
    prerequisites: tuple[str, ...]
    resources: tuple[RoadmapResource, ...]
    assignment: str
    proof_requirement: str
    completion_skills: tuple[str, ...]
    threshold: float


@dataclass(frozen=True)
class RoleBlueprint:
    name: str
    aliases: tuple[str, ...]
    claim_keywords: tuple[str, ...]
    roadmap_nodes: tuple[RoleNodeBlueprint, ...]
    model_skill_weights: dict[str, float]


def _res(title: str, url: str, kind: str) -> RoadmapResource:
    return RoadmapResource(title=title, url=url, kind=kind)


ROLE_BLUEPRINTS: tuple[RoleBlueprint, ...] = (
    RoleBlueprint(
        name="Full Stack Developer",
        aliases=("full stack", "fullstack", "mern"),
        claim_keywords=(
            "html",
            "css",
            "javascript",
            "react",
            "node",
            "nodejs",
            "express",
            "mongodb",
            "sql",
            "api",
        ),
        model_skill_weights={"projects": 0.4, "fundamentals": 0.3, "dsa": 0.3},
        roadmap_nodes=(
            RoleNodeBlueprint(
                node_id="fs_html",
                title="HTML Basics",
                skill_track="frontend",
                summary="Learn semantic HTML and page structure.",
                prerequisites=(),
                resources=(
                    _res("MDN HTML Guide", "https://developer.mozilla.org/en-US/docs/Learn/HTML", "docs"),
                    _res("freeCodeCamp Responsive Web Design", "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "course"),
                ),
                assignment="Build a multi-section personal landing page using semantic HTML.",
                proof_requirement="Pass a short HTML structure quiz and submit the landing page.",
                completion_skills=("html",),
                threshold=0.3,
            ),
            RoleNodeBlueprint(
                node_id="fs_css",
                title="CSS Foundations",
                skill_track="frontend",
                summary="Understand layout, spacing, and responsive styling.",
                prerequisites=("fs_html",),
                resources=(
                    _res("MDN CSS Guide", "https://developer.mozilla.org/en-US/docs/Learn/CSS", "docs"),
                    _res("CSS Tricks Flexbox Guide", "https://css-tricks.com/snippets/css/a-guide-to-flexbox/", "guide"),
                ),
                assignment="Style the landing page for desktop and mobile layouts.",
                proof_requirement="Submit the responsive page and pass a layout-focused review.",
                completion_skills=("css",),
                threshold=0.35,
            ),
            RoleNodeBlueprint(
                node_id="fs_js",
                title="JavaScript Foundations",
                skill_track="frontend",
                summary="Learn variables, functions, arrays, objects, and DOM basics.",
                prerequisites=("fs_css",),
                resources=(
                    _res("JavaScript.info", "https://javascript.info/", "docs"),
                    _res("MDN JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "docs"),
                ),
                assignment="Build an interactive todo or note-taking app with plain JavaScript.",
                proof_requirement="Complete the project and pass a JavaScript fundamentals quiz.",
                completion_skills=("javascript",),
                threshold=0.45,
            ),
            RoleNodeBlueprint(
                node_id="fs_react",
                title="React Basics",
                skill_track="frontend",
                summary="Learn components, props, state, and data flow.",
                prerequisites=("fs_js",),
                resources=(
                    _res("React Docs Learn", "https://react.dev/learn", "docs"),
                    _res("Scrimba React Intro", "https://scrimba.com/learn/learnreact", "course"),
                ),
                assignment="Convert the plain JS app into a React app with reusable components.",
                proof_requirement="Ship the React app and answer component/state questions.",
                completion_skills=("react",),
                threshold=0.55,
            ),
            RoleNodeBlueprint(
                node_id="fs_api",
                title="REST API Design",
                skill_track="backend",
                summary="Build and document CRUD APIs with validation and error handling.",
                prerequisites=("fs_js",),
                resources=(
                    _res("MDN Express Introduction", "https://developer.mozilla.org/en-US/docs/Learn/Server-side/Express_Nodejs/Introduction", "docs"),
                    _res("REST API Tutorial", "https://restfulapi.net/", "guide"),
                ),
                assignment="Create an API for the app with auth-safe routes and validation.",
                proof_requirement="Pass the API test suite and explain your endpoint design.",
                completion_skills=("node_js", "express", "apis"),
                threshold=0.6,
            ),
            RoleNodeBlueprint(
                node_id="fs_db",
                title="Database Modeling",
                skill_track="backend",
                summary="Model data correctly and query it safely.",
                prerequisites=("fs_api",),
                resources=(
                    _res("SQLBolt", "https://sqlbolt.com/", "interactive"),
                    _res("MongoDB University Basics", "https://learn.mongodb.com/", "course"),
                ),
                assignment="Design a schema and integrate persistent storage into the API.",
                proof_requirement="Submit schema choices and pass query correctness checks.",
                completion_skills=("sql", "mongodb"),
                threshold=0.65,
            ),
        ),
    ),
    RoleBlueprint(
        name="Backend SDE",
        aliases=("backend", "backend developer", "sde", "software engineer"),
        claim_keywords=("python", "java", "go", "sql", "api", "database", "system design"),
        model_skill_weights={"dsa": 0.4, "fundamentals": 0.35, "projects": 0.25},
        roadmap_nodes=(
            RoleNodeBlueprint(
                node_id="be_programming",
                title="Programming Fundamentals",
                skill_track="fundamentals",
                summary="Build fluency with one backend language and core problem solving.",
                prerequisites=(),
                resources=(
                    _res("Python Official Tutorial", "https://docs.python.org/3/tutorial/", "docs"),
                    _res("Exercism Python Track", "https://exercism.org/tracks/python", "practice"),
                ),
                assignment="Solve a set of functions, classes, and file I/O exercises.",
                proof_requirement="Pass a timed coding set and explain the code clearly.",
                completion_skills=("python", "java", "go"),
                threshold=0.45,
            ),
            RoleNodeBlueprint(
                node_id="be_dsa",
                title="DSA Core Patterns",
                skill_track="dsa",
                summary="Master arrays, strings, hash maps, stacks, queues, and trees.",
                prerequisites=("be_programming",),
                resources=(
                    _res("NeetCode Roadmap", "https://neetcode.io/roadmap", "roadmap"),
                    _res("LeetCode Study Plan", "https://leetcode.com/studyplan/", "practice"),
                ),
                assignment="Finish a curated DSA set and explain the trade-offs for each solution.",
                proof_requirement="Clear the DSA verification stage and solve tagged platform problems.",
                completion_skills=("data_structures", "algorithms"),
                threshold=0.6,
            ),
            RoleNodeBlueprint(
                node_id="be_api",
                title="REST API Design",
                skill_track="backend",
                summary="Design robust APIs with validation, auth, and observability.",
                prerequisites=("be_programming",),
                resources=(
                    _res("FastAPI Tutorial", "https://fastapi.tiangolo.com/tutorial/", "docs"),
                    _res("REST API Tutorial", "https://restfulapi.net/", "guide"),
                ),
                assignment="Build an authenticated API with tests and clear error handling.",
                proof_requirement="Pass endpoint tests and justify your route/resource design.",
                completion_skills=("api", "apis", "backend"),
                threshold=0.6,
            ),
            RoleNodeBlueprint(
                node_id="be_db",
                title="Data Storage And Queries",
                skill_track="backend",
                summary="Use relational or document databases safely and efficiently.",
                prerequisites=("be_api",),
                resources=(
                    _res("PostgreSQL Tutorial", "https://www.postgresqltutorial.com/", "docs"),
                    _res("Use The Index, Luke", "https://use-the-index-luke.com/", "guide"),
                ),
                assignment="Design schema, write indexed queries, and integrate persistence.",
                proof_requirement="Submit schema, queries, and performance reasoning.",
                completion_skills=("sql", "database"),
                threshold=0.65,
            ),
        ),
    ),
    RoleBlueprint(
        name="AI/ML Engineer",
        aliases=("ai", "ml", "ml engineer", "machine learning", "data science"),
        claim_keywords=("python", "machine learning", "deep learning", "statistics", "numpy", "pandas", "pytorch", "tensorflow"),
        model_skill_weights={"projects": 0.45, "fundamentals": 0.35, "dsa": 0.2},
        roadmap_nodes=(
            RoleNodeBlueprint(
                node_id="ml_python",
                title="Python And Data Basics",
                skill_track="data",
                summary="Learn Python, NumPy, pandas, and clean notebook workflow.",
                prerequisites=(),
                resources=(
                    _res("Python Data Science Handbook", "https://jakevdp.github.io/PythonDataScienceHandbook/", "book"),
                    _res("Kaggle Python Course", "https://www.kaggle.com/learn/python", "course"),
                ),
                assignment="Load, clean, and analyze a small dataset in Python.",
                proof_requirement="Submit the notebook and pass a short Python data quiz.",
                completion_skills=("python", "numpy", "pandas"),
                threshold=0.4,
            ),
            RoleNodeBlueprint(
                node_id="ml_stats",
                title="Math And Statistics Foundations",
                skill_track="math",
                summary="Cover probability, linear algebra intuition, and evaluation metrics.",
                prerequisites=("ml_python",),
                resources=(
                    _res("StatQuest", "https://www.youtube.com/c/joshstarmer", "videos"),
                    _res("Khan Academy Statistics", "https://www.khanacademy.org/math/statistics-probability", "course"),
                ),
                assignment="Explain model metrics and solve a probability-focused worksheet.",
                proof_requirement="Pass the statistics verification stage.",
                completion_skills=("statistics", "math"),
                threshold=0.5,
            ),
            RoleNodeBlueprint(
                node_id="ml_models",
                title="Machine Learning Fundamentals",
                skill_track="ml",
                summary="Learn supervised learning, validation, leakage, and baselines.",
                prerequisites=("ml_stats",),
                resources=(
                    _res("Kaggle Intro to ML", "https://www.kaggle.com/learn/intro-to-machine-learning", "course"),
                    _res("Google ML Crash Course", "https://developers.google.com/machine-learning/crash-course", "course"),
                ),
                assignment="Train and evaluate a baseline model with a reproducible pipeline.",
                proof_requirement="Submit the pipeline and justify metric choices.",
                completion_skills=("machine_learning", "ml"),
                threshold=0.6,
            ),
            RoleNodeBlueprint(
                node_id="ml_project",
                title="End-To-End ML Project",
                skill_track="projects",
                summary="Ship a real ML project with data prep, training, evaluation, and reporting.",
                prerequisites=("ml_models",),
                resources=(
                    _res("Made With ML", "https://madewithml.com/", "guide"),
                    _res("Weights & Biases Reports", "https://wandb.ai/site", "tooling"),
                ),
                assignment="Build an ML project repo with experiments, metrics, and a clear README.",
                proof_requirement="Complete the project review and explain model trade-offs.",
                completion_skills=("projects", "github", "deployment"),
                threshold=0.7,
            ),
        ),
    ),
    RoleBlueprint(
        name="Frontend Developer",
        aliases=("frontend", "front end", "react developer", "ui developer"),
        claim_keywords=("html", "css", "javascript", "react", "accessibility", "testing", "performance"),
        model_skill_weights={"projects": 0.45, "fundamentals": 0.25, "dsa": 0.30},
        roadmap_nodes=(),
    ),
    RoleBlueprint(
        name="Data Analyst",
        aliases=("data analyst", "business analyst", "analytics"),
        claim_keywords=("sql", "python", "excel", "statistics", "dashboards", "data visualization", "business metrics"),
        model_skill_weights={"projects": 0.50, "fundamentals": 0.35, "dsa": 0.15},
        roadmap_nodes=(),
    ),
    RoleBlueprint(
        name="DevOps Engineer",
        aliases=("devops", "site reliability", "sre"),
        claim_keywords=("linux", "docker", "kubernetes", "ci/cd", "cloud", "monitoring", "terraform"),
        model_skill_weights={"projects": 0.55, "fundamentals": 0.30, "dsa": 0.15},
        roadmap_nodes=(),
    ),
    RoleBlueprint(
        name="Cloud Engineer",
        aliases=("cloud", "aws", "azure", "gcp"),
        claim_keywords=("aws", "azure", "gcp", "networking", "security", "infrastructure", "serverless"),
        model_skill_weights={"projects": 0.50, "fundamentals": 0.35, "dsa": 0.15},
        roadmap_nodes=(),
    ),
    RoleBlueprint(
        name="Cybersecurity Analyst",
        aliases=("cybersecurity", "security analyst", "infosec"),
        claim_keywords=("network security", "owasp", "threat modeling", "incident response", "linux", "python", "siem"),
        model_skill_weights={"projects": 0.40, "fundamentals": 0.45, "dsa": 0.15},
        roadmap_nodes=(),
    ),
    RoleBlueprint(
        name="QA Automation Engineer",
        aliases=("qa", "automation tester", "test automation"),
        claim_keywords=("testing", "selenium", "playwright", "automation", "api testing", "ci/cd", "quality"),
        model_skill_weights={"projects": 0.45, "fundamentals": 0.35, "dsa": 0.20},
        roadmap_nodes=(),
    ),
    RoleBlueprint(
        name="Mobile App Developer",
        aliases=("mobile", "android", "ios", "react native", "flutter"),
        claim_keywords=("android", "ios", "react native", "flutter", "mobile", "api integration", "app performance"),
        model_skill_weights={"projects": 0.50, "fundamentals": 0.30, "dsa": 0.20},
        roadmap_nodes=(),
    ),
)


def get_role_blueprint(role_name: str) -> RoleBlueprint:
    normalized = role_name.strip().lower()
    for blueprint in ROLE_BLUEPRINTS:
        if blueprint.name.lower() == normalized or normalized in blueprint.aliases:
            return blueprint
    return ROLE_BLUEPRINTS[1]


def infer_role_from_text(text: str) -> str:
    lowered = text.lower()
    explicit_role_matches: list[str] = []

    for blueprint in ROLE_BLUEPRINTS:
        if blueprint.name.lower() in lowered:
            explicit_role_matches.append(blueprint.name)

    if explicit_role_matches:
        return explicit_role_matches[0]

    for blueprint in ROLE_BLUEPRINTS:
        if any(alias in lowered for alias in blueprint.aliases):
            return blueprint.name
    return "Backend SDE"
