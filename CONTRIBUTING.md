# Contributing and SQA

## Development setup

Use Python 3.11 or 3.12 in a virtual environment, then install the pinned
development dependencies from the repository root:

```bash
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes the production runtime plus pytest, coverage,
Ruff, and pip-audit. Do not add test tools to `requirements.txt`; Streamlit
Cloud should install only the production runtime.

## Incremental verification

Keep each change small and validate it before starting the next one:

1. Run the closest focused pytest file or test case.
2. If UI or runtime behavior changed, run `python scripts/check_streamlit_health.py`.
3. Before committing, run `python scripts/run_sqa.py`.
4. Inspect `git diff --check` and confirm `.streamlit/secrets.toml` is not tracked.

The complete gate includes:

- `pip check`
- bytecode compilation
- pytest with source and branch coverage of at least 85%
- Ruff correctness checks
- pip-audit against pinned production dependencies
- tracked-secret scanning
- an HTTP health and root-page check against a temporary Streamlit process

## Dependency upgrades

Upgrade intentionally, one package at a time:

1. Change the exact version in `requirements.txt` or `requirements-dev.txt`.
2. Recreate a clean virtual environment and install `requirements-dev.txt`.
3. Run `python scripts/run_sqa.py`.
4. Verify the generated handoff, five downloads, Local Review Mode, and Gemini mode when credentials are available.
5. Review upstream release notes for breaking or security changes.
6. Commit the pin and any required compatibility change together.

Never loosen the coverage threshold or suppress a correctness rule merely to
make a dependency upgrade pass.

## Credentials

Never commit `.streamlit/secrets.toml`, `.env`, API keys, private keys, or copied
provider error messages containing credentials. Use local Streamlit secrets for
development and the Streamlit Community Cloud secrets editor for the live app.
The automated secret scan reports only file names, never matching values.
