# DSE Pulse Backend Development Workflow

## Branching

- Create one focused branch from the latest `main`.
- Use descriptive prefixes such as `fix/`, `feat/`, `chore/`, `docs/`, or `test/`.
- Do not combine unrelated scanner, data, deployment, and documentation changes in one PR.

## Required local checks

Run from the repository root:

```bash
python -m compileall -q app tests
ruff check app tests
mypy app
pytest
```

A PR is not merge-ready when any required check is failing or skipped because of a code/configuration error.

## Pull request requirements

Each PR description should state:

- phase and progress impact
- exact scope
- files or subsystems changed
- verification evidence
- deployment or API compatibility impact
- remaining work

Do not merge before CI completes successfully. Do not claim test success without executed evidence.

## Review gates

Review must verify:

- no secrets or credentials are committed
- no fake market data or mock production responses are introduced
- scanner grading and hard gates are unchanged unless explicitly scoped
- privileged routes remain protected
- API contract changes are documented
- provider-specific deployment files match the approved Google Cloud architecture
- local CSV behavior is not represented as horizontally durable Cloud Run storage

## Deployment ownership

Application PRs prepare code only. Google Cloud deployment, secrets, Cloud SQL, Cloud Scheduler, and production environment changes are performed in dedicated deployment phases with explicit evidence.
