# Pipelines and release process

## Workflows

| Workflow | File | Triggered by | What it does |
| --- | --- | --- | --- |
| CI | `workflows/ci.yml` | push to `develop`, PRs into `develop`, `workflow_call` | ruff lint + format, mypy, pytest on Python 3.10–3.13 with coverage, build sdist/wheel, `twine check --strict`, wheel import smoke test |
| Security | `workflows/security.yml` | push to `develop`, PRs into `develop`, weekly cron, `workflow_call` | gitleaks over full history, bandit, semgrep, pip-audit over the locked dependency set, dependency review, CodeQL (Python + JS), Trivy filesystem scan |
| Release gate | `workflows/release-gate.yml` | PRs into `main` | source-branch policy, version bump check, changelog check, then the full CI and Security suites |
| Release | `workflows/release.yml` | push to `main`, manual | re-validates, creates the `vX.Y.Z` tag, publishes to PyPI, cuts the GitHub release |

CI and Security are reusable (`workflow_call`), so the release gate and the
release job run the exact same checks rather than a second copy of them.

## Branch model

```
feature/* ──▶ develop ──▶ main ──▶ tag vX.Y.Z ──▶ PyPI + GitHub release
             (CI +        (release gate)
              Security)
```

Only `develop` and `hotfix/*` branches may open a pull request against `main`.

## Cutting a release

1. Bump `project.version` in `pyproject.toml` on `develop`.
2. Add a `## [X.Y.Z]` section to `CHANGELOG.md`.
3. Open a pull request from `develop` into `main`.
4. The release gate fails unless the version is strictly greater than the one
   on `main`, the tag `vX.Y.Z` does not already exist, and the changelog has a
   matching section.
5. Merge. The release workflow tags `vX.Y.Z`, publishes to PyPI and creates the
   GitHub release with the changelog section plus the distribution files.

The PyPI upload happens before the tag is created. A PyPI version cannot be
re-uploaded, so it is the one truly irreversible step and it goes first; a tag
written ahead of a failed upload would make every later attempt at the same
version skip itself. If the upload fails, fix the cause and re-run the failed
jobs: nothing needs cleaning up.

Re-running the release workflow on a commit whose tag already exists is a
no-op, so merges into `main` that do not bump the version never publish.

## One-time repository setup

### PyPI publishing — still pending

This is the only step that cannot be automated, because it is done on the PyPI
website. Add a [Trusted Publisher](https://docs.pypi.org/trusted-publishers/)
to the `reflex-map3d` project with:

| Field | Value |
| --- | --- |
| Owner | `ecrespo` |
| Repository | `reflex-map3d` |
| Workflow | `release.yml` |
| Environment | `pypi` |

If the project does not exist on PyPI yet, register a *pending* publisher
instead; PyPI turns it into a real one on the first upload.

Fallback: set a `PYPI_API_TOKEN` repository secret. The publish step uses the
token when the secret exists and OIDC trusted publishing when it does not.

### Already configured

The `pypi` environment exists and only accepts deployments from `main`, so no
other branch can publish even if a workflow is changed to try.

`main` requires a pull request and these status checks:

- `Gate`
- `Source branch policy`
- `Version and changelog`

The dependency graph, Dependabot alerts and Dependabot security updates are
enabled. The dependency review job hard-fails without the dependency graph, so
do not turn it off.

`develop` only blocks force pushes and deletion, so a solo maintainer can keep
pushing to it directly. If the project moves to a feature-branch flow, add
`Lint and format`, `Type check`, `Tests (Python 3.12)` and
`Build distributions` as required checks there too:

```bash
gh api -X PATCH repos/ecrespo/reflex-map3d/branches/develop/protection/required_status_checks \
  -f 'strict=false' \
  -F 'checks[][context]=Lint and format' \
  -F 'checks[][context]=Type check' \
  -F 'checks[][context]=Tests (Python 3.12)' \
  -F 'checks[][context]=Build distributions'
```

Note that required status checks also reject direct pushes, not just merges.

### Code scanning

The gitleaks, semgrep and Trivy jobs upload SARIF to GitHub code scanning.
Those uploads are marked `continue-on-error` so the pipeline still reports the
real finding on repositories where code scanning is unavailable. The scanners
themselves fail the build on a finding regardless.

## Running the same checks locally

```bash
uv sync --all-extras
uv run ruff check custom_components tests
uv run ruff format --check custom_components tests
uv run mypy
uv run pytest -q --cov=reflex_map3d
uv build
uvx --from 'bandit[toml]' bandit -c pyproject.toml -r custom_components
uv export --frozen --all-extras --no-emit-project --format requirements-txt -o /tmp/req.txt
uvx pip-audit --strict --requirement /tmp/req.txt --disable-pip
```
