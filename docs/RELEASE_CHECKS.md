# Release verification — 3 November 2026

These are local measurements, not a claim that the GitHub publication or every
live provider integration has succeeded. Python 3.10.21, Windows, conda
`machine_learning`. Automated tests use mocks; the separately documented
[live demo](LIVE_DEMO.md) uses real Qwen calls and reports their usage.

## Measured results

| Check | Actual result | Scope |
|---|---|---|
| Complete regression suite | **95 discovered; 94 passed, 1 opt-in skip; 0 failures/errors** in 158.458 s | Latest complete `python -m evals.run_tests` run |
| Final clean Git clone | **95 discovered; 94 passed, 1 opt-in skip; 0 failures/errors** in 213.507 s | No private YAML or old Demo files; same suite |
| Real Selenium opt-in | **1 passed** in 37.031 s | Real Edge; mocked LLM; no provider fees |
| GUI | Passed real Tk startup and GUI mock workflow subprocesses | Plan, generation, edit/refinement, page switching, preview dispatch, backup/restore, recovery, diagnostics and shutdown |
| Official MCP client | Passed stdio handshake and all three tools | Mock model/browser; generation, polling and local preview |
| Harness recovery example | Injected failure → failed checkpoint → completed after resume | Completed pages retained; fake provider failure explicitly injected |
| Paired benchmark | 6/6 primary Runs completed; 6/6 separate recoveries succeeded | Three fixed fictional profiles × baseline/refined; one repeat; mock model/browser |
| System architecture | One presentation SVG is used in README and showcase | The second detailed Mermaid diagram is no longer displayed or staged on Pages |
| Static build | Passed HTML/CSS/JS/SVG/JSON and local resource checks | Node 22.16.0, html5lib and tinycss2; isolated project-path build |
| Static failure cases | 6 passed | Bad CSS, bad JS, missing assets, traversal, inconsistent counters and valid anchors |
| Showcase browser QA | Passed at actual 1440 px and 390 px viewport widths | Real Edge; no overflow or broken images; tabs, keyboard, menu and copy |
| GUI main entry | Passed | Actual `main.py --gui` entry and mapped Tk event loop; timed normal close; no generation calls |
| Source package scan | No findings in reviewed candidate | Exact local credential matches and credential-shaped strings; private files excluded |
| Live demo | Five pages generated, rendered and evaluated; project refined and recovered | Real GUI / qwen3.8-flash / Selenium; see LIVE_DEMO.md |
| Demo video | Edited real GUI and browser footage | Accelerated waits and failed/refined Run recovery disclosed |

The complete tests cover provider failures, generation/render errors, interruption,
budget exhaustion, checkpoint reuse, tool validation and diagnostics. They do not
prove any particular live account has quota. The GUI test uses real Tk controls
and the actual Harness, but mocked provider and browser implementations.

See [benchmark results](benchmark.md), [public benchmark metadata](benchmark.json)
and [evidence JSON](../showcase/data/evidence.json). Primary benchmark timing
includes execution and draining, excludes Run creation, and excludes separate
recovery experiments. Token usage is synthetic fixture usage and estimated costs
are not actual API charges. All structural HTML checks passed for this small mock
batch; no visual-quality score or statistical performance advantage is claimed.

## Repairs discovered by release checks

- Missing private YAML prevented a clean public checkout from importing. The
  loader now supports environment-only/offline import; live credentials remain
  provider requirements. A regression checks that behavior in a subprocess.
- Runtime overwrote configured request timeout with 300 seconds. It now respects
  the tighter configured/request-specific limit and still accounts for late usage.
- Initial GUI background painting could be postponed past first display. It now
  paints initially and retains debouncing for later resize events.
- GUI teardown could delete child-owned Tcl timer commands twice. Pending events
  are cancelled without taking over their owner's command cleanup. The smoke test
  now includes a child-owned callback.
- Planner debug output included raw model replies/profile-derived specifications.
  Those prints were removed; structured redacted diagnostics remain available.
- Clean-checkout testing exposed three test-fixture dependencies: an old demo
  image, implicit local Qwen selection, and a checkout-specific screenshot path
  in frozen message hashes. Tests now create a tiny image, explicitly select the
  mocked backend, and freeze the historical path only. Original snapshots and
  message assertions remain unchanged; no validator is relaxed.

Trailing whitespace outside string literals was normalized only after proving
identical Python ASTs. Archived original GUI/prompt files remain byte-for-byte
preserved, including existing whitespace warnings. Prompt content was not altered.

No generator/refiner prompt, model request parameter, API credential, config key
or database schema was changed for this release. Existing prior local development
work was backed up before edits.

## Environment caveat

`pip check` in the pre-existing shared conda environment reports two unrelated
dependency conflicts: `ml-dtypes` requires NumPy >=2 while NumPy is 1.26.0;
`zhipuai` requires PyJWT <2.9 while PyJWT is 2.15.1. These packages are not imported
by ResumeAgent's current source. They were not uninstalled or upgraded because
other projects may depend on them. This is **not** a clean-environment installation
claim. Application regression tests nevertheless passed in the requested environment.

## Screenshot provenance and privacy

`showcase/assets/generated-homepage.png` is copied byte-for-byte from an earlier
local prompt-design run: a real Qwen-generated page, user-feedback revision and
Selenium capture of the fictional Zhang San AI-student profile. It contains no
real school, email, awards or identifiable user history. The SHA-256 is in the
evidence JSON. It is a historical example, not a newly measured live release run
or a blinded quality evaluation. The demo cover is a title graphic, not a fake GUI.

Private local YAML, credentials, profile catalogs, SQLite stores, diagnostics,
outputs, local logs, test artifacts and the pre-release backup are excluded from
the public source archive. Legacy GUI/prompt source is preserved because it is
not safe to assume it is disposable. No existing user output was deleted.

## Publication and deployment

Original main: `0edc63aa3b74b817d573c265c39d0e719fa791e2`.
The source workspace had no `.git`; it was privately backed up before editing.
The user provided a clean clone, and reviewed source was synchronized there while
retaining its `.git` and history. The original main is preserved remotely at
`backup/main-before-harness-release-20261103`. The initial authorization problem
was resolved by the maintainer before any backup/main write.

GitHub Pages is configured with `build_type: workflow` at
<https://bj-liu.github.io/resumeagent/>. Configuration is distinct from successful
deployment. The initial release was published as
[`3a8151b4fb8889a1d2e9590e3f6bcb1e61a91314`](https://github.com/bj-Liu/resumeagent/commit/3a8151b4fb8889a1d2e9590e3f6bcb1e61a91314).
Its [Pages build and deployment](https://github.com/bj-Liu/resumeagent/actions/runs/41502441363)
both completed successfully. Real Edge verification of the **live** URL passed
at 1440 px and 390 px: no horizontal overflow or missing images; role tabs,
keyboard navigation, mobile menu and copy command worked. The
[clean-runner Python test workflow](https://github.com/bj-Liu/resumeagent/actions/workflows/tests.yml)
provides independent installation/compilation/regression results.

The initial CI run exposed a Windows 8.3 temporary-directory alias in one test's
expected screenshot path (`RUNNER~1` versus `runneradmin`). The production tool
already returns a resolved path. The test now resolves its expected path too,
keeping the same strict message assertion rather than changing application paths.
Five synthetic secret-detector regressions also cover real-looking tokens, exact
matches, entropy review and the two false-positive cases found during the audit.

Normal HTTPS Git push repeatedly failed with network resets. As an authorized
transport fallback, the official Git Data API uploaded the exact Git blob objects,
verified the root tree and commit SHA against the local clone, and updated main
with `force: false`. The original parent and backup branch were verified before
the update. This was a normal fast-forward of the same local commit, not a new
root history or a force push. The local tracking reference was updated only after
the remote SHA was independently confirmed. No branch protection was bypassed.

The prepared Pages workflow validates and stages only the isolated showcase,
uploads its artifact after successful checks, and deploys through the official
Pages actions. It follows the [GitHub Pages custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
Repository Settings → Pages must use **GitHub Actions**. Publication status and
the final commit SHA must be updated after an actual successful push/deployment.

## Local reproducibility

```bash
python -m evals.run_tests --output test-artifacts/release/full-tests.log
python examples/mcp_client.py
python examples/harness_demo.py --fail-once
python evals/benchmark.py --output test-artifacts/release/benchmark
python -m pip install -r requirements-showcase.txt
python scripts/build_showcase.py --output release-dist/showcase
python -m http.server 8080 --directory release-dist/showcase
```

Real Selenium opt-in and GUI need a supported browser/driver and display as
described in README. `scripts/check_showcase_browser.py` optionally verifies the
built static site in Selenium. `scripts/render_architecture_svg.py` renders the
single presentation SVG using only Python's standard library. The detailed legacy
Mermaid diagram is not displayed in README or the showcase.

## Follow-up release checks

The Windows CI process-kill recovery test originally shared a short startup and
checkpoint timeout. Slow runner I/O could leave only one completed page when the
parent checked. The test now independently waits for startup and two completed
checkpoints; its blocked third page waits for process termination rather than a
fixed sleep. The exact two-completed-pages and resume-only-failed-page assertions
are retained. The local complete suite passed 95 discovered / 94 passed / one
opt-in skip in 158.458 seconds. No production workflow change was needed.

The user-supplied Homepage Studio screenshot is copied byte-for-byte, preserves
its 2880?1704 ratio and opens at full resolution. Its empty central preview is
explicitly identified; new final-page screenshots and the actual five-page site
are separate demo artifacts. Only the original presentation System Architecture
is displayed.

Final showcase validation checked 36 staged static files and six inline JavaScript blocks in generated pages. Six fail-closed build tests and five credential-detector tests passed. The final site passed real Edge checks at 1440px and 390px. Git whitespace review found nine pre-existing trailing-space lines in the generated publications HTML/CSS; their code content is preserved from actual model output. Git normalizes CRLF to LF; both original-source and public-file hashes are recorded. No authored-code whitespace error was introduced.

## Recorded-demo deployment verification

Commit [`f083b65`](https://github.com/bj-Liu/resumeagent/commit/f083b65c35c130862f1cfcaa3400ef7def9b4e52) was published with its exact Git tree/parent after a zero-finding post-commit security audit (170 files; 8 commits; 204 file blobs; 8 metadata objects). Normal Git transport failed with connection resets; the official Git Data API fast-forwarded that same SHA with `force: false`.

[Pages build and deployment](https://github.com/bj-Liu/resumeagent/actions/runs/41587295627) succeeded. Real Edge checks of the live URL passed at 1440px and 390px. The original GUI screenshot matched its local SHA-256; all ten public HTML/CSS files matched their Git-normalized checksums. The external MP4 loaded and played in Edge: duration 220.458333 s, 1920?1080, currentTime advanced. GitHub's asset SHA-256 matched the local edited video.

The remote pre-demo backup is `backup/main-before-demo-20261103`; the original pre-Harness backup is also retained. No history rewrite, forced ref update or repository recreation was used. The final follow-up only records these observed results and distinguishes source/public text hashes.
