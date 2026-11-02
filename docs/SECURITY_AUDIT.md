# API key and publication security audit

Date: 3 November 2026. No credential values, fragments or reversible encodings
are included in this report.

## Scope and method

- Scanned 605 local text files across Python, YAML, JSON, prompts, tests,
  documentation, HTML/CSS/JS, examples and text logs at the initial final audit.
  Private backup copies and downloaded browser/developer caches were excluded.
- Scanned the explicitly selected public source candidate before synchronization.
- Scanned all 38 tracked files of original main and every blob reachable from all
  fetched branches/tags: **5 commits, 41 unique file blobs**. Remote main was
  `0edc63aa3b74b817d573c265c39d0e719fa791e2`.
- Used exact matching against locally configured credential values, recognized
  provider token/private-key formats and high-entropy credential assignments.
  Findings contain paths, object IDs and classifications, never matched values.
- Inspected README/showcase copy, the published fictional-profile screenshot,
  architecture and original diagram-style video cover. There is no new recording
  containing a terminal, provider dashboard, credentials or private profile.

The audit script is `scripts/security_audit.py`; the release candidate scanner is
`scripts/prepare_release.py`. Final staged source and the new commit are rescanned
before any main push. Public results are kept distinct from private detailed logs.

## Findings and fixes

| Finding | Resolution |
|---|---|
| Two local private YAML files contain real credentials | Kept local, ignored, excluded from candidate synchronization, archive and Git staging |
| Original remote `config.yaml` uses placeholders, not real keys | Remove tracked runtime configuration from released main; provide safe `config.example.yaml` and `.env.example` |
| Original logs, local image catalogs and old demo outputs are runtime/history material | Exclude from the new public candidate; retain private original workspace and Git history/backup |
| Planner printed raw replies and profile-derived specs | Remove debug prints; preserve redacted Harness diagnostics |
| Example MCP config included machine-specific paths | Replace with explicit placeholder paths and offline Mock settings |
| New release source | No detected real credential matches or credential-shaped strings |
| Existing reachable Git history | No detected real API key or private-key finding |

Provider adapters already read actual keys from environment variables. No hardcoded
real key was found in Python or prompts. `.env.example` contains names and empty
values/comments only. `.env`, private YAML, logs, caches, stores, generated outputs,
local profile catalogs and private release backups are ignored. Existing ignored
files are never assumed to be untracked: the Git index is checked independently.

The historical-main backup branch was created **after** this history scan passed.
No history rewrite, force push or repository recreation is used. The user-owned
working source is preserved; sanitizing a public package does not require deleting
the user's private local credential store.

## Residual risks and credential rotation

No evidence of a real key entering the inspected public history was found, so this
report does not falsely assert a known credential leak. Pattern scanning cannot
prove absence of all unknown secrets. Unreachable objects, deleted remote refs,
forks, external caches and credentials outside the inspected repository are not
covered. Historical binary media were not subjected to exhaustive video-frame
OCR; they are not used as the new showcase demo.

**If a real key has ever been shared publicly, committed on another ref, shown
in a recording or otherwise exposed, revoke or rotate it at the provider
immediately. Deleting the current file does not revoke the key or erase public
history.** Do not rewrite or force-push history under the current authorization;
any necessary history-remediation plan requires a separate explicit decision.

Local private configurations and the pre-release backup still contain credentials.
Keep them private and do not upload the whole workspace. Review generated websites
and screenshots before sharing; SQLite state and local developer diagnostics may
contain user information even when API keys are redacted.
