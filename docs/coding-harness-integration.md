# Coding Harness Integration

## Selected Open Source Base

Use Judge0 as the execution engine and Judge0 IDE as the full editor app:

- Judge0 API: https://github.com/judge0/judge0
- Judge0 IDE: https://github.com/judge0/ide

Why this fit won:

- Judge0 is a sandboxed, self-hostable code execution system with a JSON API, webhooks, resource limits, and support for 90+ languages.
- Judge0 IDE is MIT-licensed and already built to talk to Judge0, so it can be opened from our Coding Harness while our backend owns users, problems, hidden tests, scoring, and trust evidence.
- Full online judges such as DMOJ and QingdaoU are stronger contest platforms, but they would duplicate our auth, assessment, and evidence model.

The source has been cloned locally:

- `external/judge0`
- `external/judge0-ide`

## Runtime Wiring

Backend:

- Set `JUDGE0_BASE_URL` to a self-hosted Judge0 CE endpoint, for example `http://localhost:2358`.
- Optional: set `JUDGE0_AUTH_TOKEN`, `JUDGE0_API_KEY`, and `JUDGE0_PYTHON_LANGUAGE_ID`.
- If `JUDGE0_BASE_URL` is missing, the backend keeps the existing local Python fallback for demos and tests.

Frontend:

- Set `NEXT_PUBLIC_HARNESS_APP_URL` to the editor app URL.
- Default is `https://ide.judge0.com`.
- For local development, serve `external/judge0-ide` with any static server and set `NEXT_PUBLIC_HARNESS_APP_URL` to that local URL.

## Security Hardening Roadmap

For the hackathon demo, the backend now has a Judge0 execution path. For a cheating-resistant production version, keep these rules:

- Run Judge0 on isolated Linux infrastructure, separate from the app database and private network.
- Keep hidden tests only on our backend; never ship hidden cases to the browser or Judge0 IDE.
- Disable network access for submissions unless a specific problem needs it.
- Enforce CPU, wall-time, memory, stack, and output-size limits per language.
- Require authenticated submissions through our backend; do not expose Judge0 directly to students.
- Store submission snapshots, timing, failed attempts, language, IP/device metadata, and integrity flags.
- Add plagiarism detection later with token/code similarity and cohort-level comparison.
- Use proctoring signals carefully: focus on code behavior, unusual copy/paste, tab-switching, timing, and repeated near-identical submissions.

## Integration Shape

The user clicks `Coding Harness` in the product UI:

1. Our modal loads backend-owned problems and lets a student submit proof.
2. `Open Judge0 IDE` launches the editor app for a richer coding workspace.
3. Submissions still go through our backend for auth, hidden tests, scoring, and evidence persistence.
4. Backend delegates execution to Judge0 when configured.
