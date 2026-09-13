# GitHub-hosted dashboard refresh

**Goal:** Restore collection on GitHub-hosted Ubuntu and publish the weather-only README.

**Architecture:** One manually triggered job restores a verified backup artifact, runs the existing CLI, renders a complete dashboard from the selected export, and commits only dashboard files. Each run uploads a new backup artifact. No self-hosted label, personal identifier, external data branch, or recurring schedule is required.

- [x] Add regression tests for current-date rendering, source checksum failures, older exports, and failed rendering preserving the previous README.
- [x] Reuse the existing visual renderer; add export-to-dashboard staging and a parameterized README template.
- [x] Restore `.github/workflows/pipeline.yml` on `ubuntu-latest`, install Firefox, restore the latest unexpired state artifact, and preserve backups even when collection fails. Fail if previously saved artifacts are expired rather than silently starting over.
- [x] Publish only after successful collection and rendering. Use neutral commit attribution and the built-in repository token. A rejected push must fail without force pushing.
- [x] Keep README weather-only. Document manual Actions refresh and 90-day artifact retention in the operating guide.
- [x] Run targeted/full offline tests, dispatch the workflow on GitHub, and verify its runner labels, completion, published dashboard, and saved artifact.

**Validation commands:** `python -m pytest -q`; `python workflows/update_dashboard.py --data-dir PATH`; GitHub Actions run details and artifact listing. Retain the current dashboard if parsing, checksums, rendering, or source-date validation fails.

**Verification:** 98 offline tests passed locally. GitHub offline CI passed. Two manually dispatched Ubuntu runs completed successfully, including first-run initialization, subsequent state restoration, collection, backup upload, and README publication. Both saved an unexpired `weather-state` artifact.
