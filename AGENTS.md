# AGENTS.md

## Purpose and scope

This file is the operating contract for engineers and coding agents working in
this repository. It applies to the entire repository unless a more specific
`AGENTS.md` is added in a subdirectory. Follow user instructions first, then
this file, then the existing project documentation.

The project is a controlled Streamlit prototype that converts natural-language
requirements into a reviewable PCB design handoff. Changes must preserve
correctness, traceability, security, deterministic fallbacks, and the ability to
run without a paid or hosted AI provider.

## Engineering priorities

Apply these priorities in order:

1. Protect credentials, user data, and repository integrity.
2. Preserve the controlled PCB architecture and cross-section consistency.
3. Keep Base mode deterministic and available without network access.
4. Make the smallest complete change that satisfies the requirement.
5. Verify each increment before starting the next increment.
6. Keep tests, documentation, deployment metadata, and behavior synchronized.
7. Report evidence accurately; never claim a check passed when it was skipped,
   blocked, inferred, or run against the wrong environment.

## Product invariants

The generated board architecture is intentionally constrained:

```text
USB-C 5 V input -> 3.3 V regulator -> ESP32-WROOM-32 -> shared I2C sensor bus
```

Unless a user explicitly approves an architectural redesign:

- Do not silently add unsupported hardware, interfaces, or fabrication claims.
- Only selected sensor footprints and their associated handoff rows may vary.
- Unsupported requirements must be reported, not converted into invented parts.
- BOM, pin map, netlist, power budget, readiness, visuals, checklists, and
  exports must agree on components, reference designators, nets, and status.
- Readiness states remain `Ready`, `Needs Review`, or `Blocked` and must be
  grounded in generated package data and validation results.
- PCB Review Copilot may review, explain, summarize, and identify risk. It must
  not mutate the current handoff or imply professional fabrication signoff.
- The five user-facing exports must remain available after a successful handoff.

## Repository map and ownership

- `app.py`: Streamlit composition, rendering, session flow, and compatibility
  wrappers. Keep domain logic in `src/` when practical.
- `src/data_loader.py`: JSON loading, sensor discovery, and indexing.
- `src/validation.py`: sensor definition and schema validation.
- `src/parser.py`: controlled requirement parsing.
- `src/base_assistant.py`: deterministic local assistant and output validation.
- `src/ollama_assistant.py`: optional Ollama integration and Base fallback.
- `src/gemini_assistant.py`: optional Gemini requirement extraction and Base
  fallback.
- `src/design_generator.py`: handoff tables, checklists, and package generation.
- `src/readiness.py`: readiness gates and status logic.
- `src/review_copilot.py`: grounded local and Gemini review responses.
- `src/provider_security.py`: safe endpoint display and sanitized provider
  failures.
- `src/visuals.py`: PCB, architecture, and schematic visuals.
- `src/exports.py`: CSV, Markdown, and JSON exports.
- `src/build_info.py` and `VERSION`: non-sensitive deployment traceability.
- `data/sensors/<sensor>/sensor.json`: sensor plugins and capabilities.
- `data/board_template.json`: fixed board-level design context.
- `data/requirement_keywords.json`: controlled parsing vocabulary.
- `tests/`: unit, integration, Streamlit AppTest, provider, export, and UI
  regression tests.
- `scripts/run_sqa.py`: canonical local and CI quality gate.
- `.github/workflows/sqa.yml`: Python 3.11 and 3.12 CI matrix.
- `CONTRIBUTING.md`: developer setup and incremental verification.
- `DEPLOYMENT.md`: secrets, release, live verification, and rollback runbook.

Before editing a subsystem, read its source, its closest tests, and the relevant
documentation. Do not duplicate business rules in multiple modules.

## Supported environments and setup

Supported Python versions are 3.11 and 3.12.

Create an isolated environment and install the pinned development toolchain:

```bash
python -m pip install -r requirements-dev.txt
```

Production runtime dependencies belong in `requirements.txt`. Test, lint,
coverage, and audit tooling belong in `requirements-dev.txt`. Both files use
exact versions for reproducibility.

Do not treat a developer machine's existing environment as reproducibility
evidence. Dependency or runtime changes require a clean-environment install.

## Required change workflow

### 1. Orient before editing

- Read this file, `README.md`, and the relevant source and tests.
- Run `git status --short` and preserve unrelated or pre-existing user changes.
- Confirm the requested scope and identify behavioral invariants at risk.
- For an audit or diagnosis, inspect and report first; do not expand into an
  implementation unless the user requested a change.

### 2. Plan a small increment

- Prefer one cohesive change at a time.
- Identify the closest focused test before editing.
- Avoid opportunistic refactors, broad formatting, or dependency upgrades.
- New abstractions must remove real duplication or enforce a meaningful
  boundary; do not add layers merely for style.

### 3. Implement safely

- Preserve public function names and existing user workflows unless the change
  explicitly requires a breaking change.
- Use clear names, focused functions, type hints where they improve contracts,
  and `pathlib.Path` for new filesystem code.
- Keep provider calls behind testable functions and injectable or mockable
  boundaries.
- Handle expected failures explicitly and give users actionable, sanitized
  messages.
- Never catch broad exceptions silently. If a UI boundary must remain
  available, log only safe diagnostic categories and present a safe fallback.

### 4. Verify the increment

Run the closest relevant check first. Examples:

```bash
python -m pytest tests/test_app.py -q
python -m pytest tests/test_review_copilot.py -q
python -m pytest tests/test_build_info.py -q
python scripts/check_streamlit_health.py
```

For Streamlit AppTest, resolve `app.py` from the repository root with an
absolute path. A relative `AppTest.from_file("app.py")` inside `tests/` resolves
to `tests/app.py` and is not portable.

After the focused check passes, run the complete gate:

```bash
python scripts/run_sqa.py
```

The canonical gate must retain all of these checks:

- dependency consistency with `pip check`
- bytecode compilation
- pytest with source and branch coverage
- a minimum overall coverage threshold of 85%
- Ruff correctness checks
- production dependency vulnerability audit
- repository secret scan
- real local Streamlit root and health checks

Do not lower the coverage threshold, weaken the secret scan, disable a test, or
suppress a correctness rule merely to make a change pass.

### 5. Review the final diff

Before handoff or publication:

```bash
git diff --check
git status --short
python scripts/check_secrets.py
```

Inspect the complete diff, including new files. Confirm that generated assets,
local environments, caches, credentials, logs, and unrelated changes are not
included.

## Testing standards

- Every behavior change requires a regression test at the lowest useful level.
- Test success, validation failure, empty/missing data, and safe fallback paths.
- Prefer deterministic fixtures and mocks over network calls.
- Tests must not require Gemini, Ollama, internet access, or billable API use.
- Provider tests must use fake keys and sanitized exceptions.
- UI changes require AppTest coverage for critical labels, state transitions,
  exceptions, and download availability.
- Generated-package tests must assert consistency across the relevant BOM, pin
  map, netlist, power, readiness, visual, and export representations.
- A local HTTP 200 is runtime evidence, not proof that every interactive feature
  works.
- Do not report historical test counts or coverage as current; rerun the gate.

## AI provider and fallback rules

- Base mode is mandatory, local, deterministic, and free of provider calls.
- Ollama and Gemini are optional enhancement paths.
- Provider output must be validated before it influences the design package.
- Invalid, incomplete, unavailable, timed-out, or unreachable provider results
  must fall back safely without corrupting the handoff.
- Gemini Review Copilot responses must stay grounded in the generated context,
  use allowed source labels, and retain the normalized response contract.
- Never include raw provider exceptions, request headers, tokens, keys, or
  sensitive endpoints in the UI, logs, exports, test output, or commits.
- Do not make real paid or quota-consuming provider calls unless the user
  explicitly authorizes them. When authorized, print only mode, model, outcome,
  and sanitized failure category.

## Secrets and security

- `GEMINI_API_KEY` belongs in local `.streamlit/secrets.toml`, an environment
  variable, or Streamlit Community Cloud App Settings -> Secrets.
- Never commit `.streamlit/secrets.toml`, `.env`, API keys, private keys, session
  cookies, access tokens, or copied provider payloads.
- Never print, echo, partially reveal, transform, or write a credential into a
  temporary artifact for debugging.
- Do not inspect browser cookie stores, credential managers, or unrelated user
  files.
- Preserve `src/provider_security.py` as the single sanitization boundary for
  provider-facing failures where applicable.
- Run `python scripts/check_secrets.py` before every commit.
- If credential exposure is suspected, stop publication, report the affected
  file or surface without reproducing the value, rotate the credential, and
  remove it from both the current tree and repository history through an
  explicitly approved remediation plan.

Making the Streamlit app public does not publish Streamlit Secrets, but public
visitors can trigger provider-backed features and consume quota. Any public AI
feature should retain fallbacks and should consider rate or usage controls.

## Sensor plugin changes

Prefer data-driven additions under `data/sensors/<sensor>/sensor.json`.

- Follow `data/sensors/README.md` and the disabled template sensor.
- Use stable reference designators and valid supply, interface, address, pin,
  footprint, category, keyword, and visual metadata.
- Add validation, parsing, package, visual, and export assertions for the new
  sensor.
- A normal 3.3 V I2C sensor should not require hard-coded `app.py` logic.
- Non-I2C or board-architecture changes require explicit design approval and a
  broader consistency review.

## Dependency and configuration changes

- Upgrade one dependency or tightly coupled group at a time.
- Review upstream release and security notes before changing a pin.
- Recreate a clean environment after changing dependency files.
- Run the full SQA gate and verify Base mode, Local Review Mode, five downloads,
  and authorized Gemini/Ollama paths as applicable.
- Do not add a dependency when the standard library or existing dependency
  provides a clear, maintainable solution.
- Keep `pyproject.toml`, `requirements*.txt`, CI, and documentation consistent.

## Git and publication discipline

- Treat uncommitted changes as user-owned until proven otherwise.
- Never discard, overwrite, reset, or reformat unrelated work.
- Keep commits focused and use an imperative message that describes the outcome.
- Do not commit caches, virtual environments, local secrets, generated exports,
  logs, or ignored personal notes.
- Do not use history-rewriting or destructive commands on shared branches.
- Do not commit, push, open a pull request, tag, release, change hosted secrets,
  or alter deployment settings unless the user explicitly authorizes that
  external action.
- Before pushing, fetch the target branch and confirm it has not moved. If it
  moved, stop and integrate deliberately rather than overwriting remote work.
- After pushing, require the Python 3.11 and 3.12 CI jobs to pass. Investigate
  actual job logs before attempting a CI fix.
- Roll back shared changes with a new `git revert` commit; do not rewrite `main`.

## Deployment and live verification

Production currently uses Streamlit Community Cloud from `main` with `app.py`
as the entry point. Follow `DEPLOYMENT.md` for release and rollback procedures.

Repository, CI, deployment, endpoint, and rendered UI evidence are distinct:

- A matching Git commit proves source publication.
- Green GitHub Actions proves the repository gate on that commit.
- A root or health response proves endpoint availability.
- Only a rendered browser interaction proves form submission, diagrams,
  Copilot, downloads, Gemini behavior, and responsive layout.

For the public Streamlit endpoint, follow the complete anonymous redirect chain
and retain session cookies before classifying access. The first `303` may be
normal Streamlit session initialization and is not proof that the app is
private.

For every live release, verify and record:

1. Final public root and health responses after the full redirect chain.
2. The **Deployment details** version and short commit match the release.
3. A temperature, humidity, and light handoff generates successfully.
4. AHT20 and BH1750 selection and reference designators are correct.
5. Readiness, PCB visual, connectivity diagrams, and detail tables render.
6. Review Copilot answers a grounded question.
7. All five downloads complete with the correct content types.
8. Gemini mode works when the hosted secret is configured and authorized.
9. No secret or raw provider failure appears in the UI or response.
10. Desktop and narrow/mobile layouts remain usable.

If browser automation is unavailable, mark rendered interaction checks
`Blocked`; do not infer them from HTTP status, CI, local AppTest, or source code.

## Documentation and versioning

- Update `README.md` for user-visible setup, usage, or feature changes.
- Update `CONTRIBUTING.md` for developer workflow or quality-gate changes.
- Update `DEPLOYMENT.md` for hosting, secret, release, verification, or rollback
  changes.
- Update `VERSION` intentionally for a release and add or revise build-info
  tests when traceability behavior changes.
- Keep examples free of real credentials and environment-specific absolute
  paths.
- Durable repository documentation belongs in tracked files. `docs/` is
  currently ignored and is not suitable for required project instructions.

## Definition of done

A change is complete only when all applicable items are true:

- The requested behavior is implemented without unrelated scope expansion.
- Product invariants and Base-mode behavior are preserved.
- Focused regression tests pass.
- `python scripts/run_sqa.py` passes from the declared development environment.
- Coverage remains at or above 85% without artificial exclusions.
- Secret and vulnerability checks pass.
- UI/runtime changes pass local health and AppTest checks.
- Documentation and version metadata are updated when required.
- `git diff --check` passes and the final diff contains only intended files.
- No external publication action was taken without explicit authorization.
- The final report lists commands run, evidence, Pass/Fail/Blocked results,
  limitations, and any required follow-up.

Never replace missing evidence with confidence. A precise `Blocked` result is
more valuable than an unsupported `Pass`.
