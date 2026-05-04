# Production Assessment Integrity Plan

Goal: make assessment scoring depend on backend-owned question definitions rather than client-submitted correctness flags.

Scope for this implementation slice:
- Add a static v1 question bank with question ids, stage metadata, answer keys, and timing limits.
- Require submitted answers to include `submitted_answer`.
- Compute correctness on the server.
- Reject unknown question ids and invalid timing values.
- Persist computed answer events so the existing trust model, roadmap, trust stamp, and dashboard flow keep working.

Out of scope for this slice:
- Full proctoring.
- Live code sandboxing.
- Real auth replacement.
- Frontend test-taking UI.
- Dynamic adaptive question generation.
