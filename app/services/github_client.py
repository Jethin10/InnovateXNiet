from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GITHUB_API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class GitHubCollectionRequest:
    username: str
    access_token: str | None = None
    include_private: bool = False
    max_repositories: int = 100
    max_enriched_repositories: int = 5


def collect_github_profile(request: GitHubCollectionRequest) -> dict:
    token = request.access_token
    username = request.username.strip()
    user = _get_json("/user", token) if token and not username else _get_json(f"/users/{username}", token)
    resolved_username = user.get("login") or username
    repositories = _list_repositories(resolved_username, token, request.include_private, request.max_repositories)
    enriched_repositories = []
    sorted_repositories = sorted(repositories, key=lambda repo: repo.get("pushed_at") or "", reverse=True)
    for index, repo in enumerate(sorted_repositories[: request.max_repositories]):
        if index < request.max_enriched_repositories:
            enriched_repositories.append(_enrich_repository(repo, resolved_username, token))
        else:
            enriched_repositories.append({**repo, "languages": {}, "contributors": [], "commits": []})
    return {
        "user": user,
        "repositories": enriched_repositories,
        "rate_limit_remaining": _rate_limit_remaining(token),
    }


def _list_repositories(
    username: str,
    token: str | None,
    include_private: bool,
    max_repositories: int,
) -> list[dict]:
    if token and include_private:
        query = urlencode(
            {
                "visibility": "all",
                "affiliation": "owner,collaborator,organization_member",
                "sort": "updated",
                "per_page": 100,
            }
        )
        path = f"/user/repos?{query}"
    else:
        query = urlencode({"sort": "updated", "per_page": 100})
        path = f"/users/{username}/repos?{query}"

    return _get_paginated(path, token, max_items=max_repositories)


def _enrich_repository(repo: dict, username: str, token: str | None) -> dict:
    full_name = repo.get("full_name")
    if not full_name:
        return {**repo, "languages": {}, "contributors": [], "commits": []}

    return {
        **repo,
        "languages": _safe_get_json(f"/repos/{full_name}/languages", token, default={}),
        "contributors": _safe_get_json(
            f"/repos/{full_name}/contributors?{urlencode({'per_page': 20, 'anon': 'false'})}",
            token,
            default=[],
        ),
        "commits": _safe_get_json(
            f"/repos/{full_name}/commits?{urlencode({'per_page': 20, 'author': username})}",
            token,
            default=[],
        ),
    }


def _get_paginated(path: str, token: str | None, max_items: int) -> list[dict]:
    items: list[dict] = []
    next_path: str | None = path
    while next_path and len(items) < max_items:
        payload, link_header = _request_json(next_path, token, include_headers=True)
        if isinstance(payload, list):
            items.extend(payload)
        next_path = _next_path_from_link(link_header)
    return items[:max_items]


def _get_json(path: str, token: str | None) -> dict:
    payload = _request_json(path, token)
    return payload if isinstance(payload, dict) else {}


def _safe_get_json(path: str, token: str | None, default):
    try:
        return _request_json(path, token)
    except (HTTPError, URLError, TimeoutError):
        return default


def _request_json(path: str, token: str | None, include_headers: bool = False):
    url = path if path.startswith("https://") else f"{GITHUB_API_BASE}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "placement-trust-passport",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with urlopen(Request(url, headers=headers), timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
        if include_headers:
            return payload, response.headers.get("Link")
        return payload


def _next_path_from_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for entry in link_header.split(","):
        url_part, _, rel_part = entry.partition(";")
        if 'rel="next"' in rel_part:
            return url_part.strip()[1:-1]
    return None


def _rate_limit_remaining(token: str | None) -> int | None:
    payload = _safe_get_json("/rate_limit", token, default={})
    core = payload.get("resources", {}).get("core", {}) if isinstance(payload, dict) else {}
    remaining = core.get("remaining")
    return int(remaining) if isinstance(remaining, int) else None
