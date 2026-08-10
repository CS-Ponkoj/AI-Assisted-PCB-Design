# Streamlit Deployment Runbook

## Production configuration

The live app is deployed from:

- Repository: `CS-Ponkoj/AI-Assisted-PCB-Design`
- Branch: `main`
- Entry point: `app.py`
- URL: <https://ai-assisted-pcb-design.streamlit.app/>

Streamlit Community Cloud normally redeploys after a push to the configured
branch. GitHub Actions and Streamlit deployment are separate systems: a green
GitHub workflow verifies the commit, while Streamlit's app dashboard confirms
that the hosted process actually deployed it.

## Gemini secret configuration

Do not put the Gemini key in GitHub or any tracked file.

For local development, create the ignored file `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key-here"
```

For the live app, open the app in Streamlit Community Cloud, choose **Settings
> Secrets**, and add the same TOML entry there. Saving the hosted secret makes
it available to the running app without adding it to the repository. Rotate
the key in Google AI Studio and replace the hosted value if exposure is ever
suspected.

## Release procedure

1. Pull or fetch `main` and confirm the intended changes are the only changes.
2. Install `requirements-dev.txt` in a clean Python 3.11 or 3.12 environment.
3. Run `python scripts/run_sqa.py` and require every gate to pass.
4. When available, test Gemini requirement extraction and Review Copilot using the hidden local key; do not print the key.
5. Push the reviewed commit to `main`.
6. Wait for both Python 3.11 and 3.12 GitHub Actions jobs to pass.
7. Open the live URL and verify the **Deployment details** commit matches the pushed commit.
8. Generate a temperature, humidity, and light handoff. Confirm readiness, PCB visual, Review Copilot, and all five downloads.
9. Select Gemini API mode and verify one grounded request when the hosted key is configured.

An HTTP 200 or health response proves the service is running, but it does not
replace the interactive checks above. If the URL redirects to Streamlit sign-in,
review the app sharing settings before calling the public deployment verified.

## Rollback

Use a reversible Git commit; do not rewrite shared history:

```bash
git revert <bad-commit-sha>
git push origin main
```

Then wait for both SQA jobs, confirm Streamlit redeploys the revert commit, and
repeat the live smoke test. If only the Gemini credential is faulty, restore or
rotate it in Streamlit's secrets editor instead of changing repository history.

Record the failing commit, symptom, rollback commit, CI result, and live result
in the incident or release notes.
