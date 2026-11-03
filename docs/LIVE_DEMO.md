# Recorded live demonstration ? 3 November 2026

This is a real model-backed demonstration using `qwen3.8-flash`, the existing
Tkinter GUI, Harness Runtime and Edge/Selenium. It is separate from the offline
Mock benchmark. No quality score or comparative performance improvement is claimed.

## Inputs and artifacts

The complete, deliberately fictional student profile is in
[DEMO_PROFILE.md](DEMO_PROFILE.md) and [the exact JSON fixture](../examples/fixtures/zhang_san_demo.json).
The named universities are real institutions; the enrollment, people, papers,
fictional venues, companies, awards, grades and experiences are demo settings,
not claims about a real person or endorsements. Contact links use `example.invalid`.
Papers have local placeholder anchors, no real DOI or publication link.

Five model-generated HTML files and five CSS files are published unchanged in
[the generated demo](https://bj-liu.github.io/resumeagent/demo/):
`index.html`, `publications.html`, `research.html`, `projects.html`, `experience.html`.
Each has its own CSS file. The project page includes a model-generated native SVG
process illustration; it is page content, not a second System Architecture.

## Actual Runs

| Purpose | Run ID | Final state | Recorded execution time |
|---|---|---|---|
| GUI Plan | `32b044a6d5db4b5597adeed60d70b868` | completed | 83.922 s |
| GUI Auto Generate | `ca605fa797414e1094758b196232fdac` | completed | 233.375 s |
| GUI Refine Website, then CLI resume | `836b5f8b3b024a2494f85c1cf6bbcc0a` | completed | 203.594 s |

The five-page generation included real rendering, five screenshot evaluations and
artifact validation. The critic requested no automatic revision in this particular
run. Independent mobile inspection then found a 3px overflow on the project page.
User feedback was entered through the actual GUI and submitted with Refine Website.

The first refinement request saved code but failed when an old Selenium session
was no longer available. Its finite retry returned an invalid refinement response;
the validator rejected it. No validator was relaxed. The same Run was resumed using
the existing public interface with a fresh browser session:

```powershell
python main.py --model qwen3.8-flash `
  --storage_root test-artifacts/showcase-live-recording-v2/state `
  --resume 836b5f8b3b024a2494f85c1cf6bbcc0a
```

The restored refinement, rendering and validation completed. Other pages were not
regenerated. Failed events remain in the trace; the report does not depict an
uninterrupted first-attempt success. The old GUI title can retain its earlier
failure until its next operation; SQLite/CLI provides the authoritative resumed
Run state. Restart the application before further work if its browser was closed.

## Checks and resource use

- Five HTML documents parsed without HTML5 parser errors.
- Actual Edge captures at 1440px and 390px: ten page/viewport checks, no missing
  images, Chinese text and local CSS loaded. All five pages fit the viewport.
- Projects changed from scrollWidth 393 to 390 at a 390px viewport after refinement.
- The original GUI Open Website action opened the real generated page successfully.
- Browser footage follows actual links and expands an actual paper abstract.
- No blinded human visual-quality score was collected. HTML validity and model
  screenshot judgments do not prove universal visual quality.

Provider usage records: **20 requests**, **141,578 input tokens**, **61,634 output tokens**, including failed attempts and recovery.

At the documented Beijing input/output rates of CNY 0.8/2.7 per million tokens, the estimate is **CNY 0.279674**. This is not a provider invoice; discounts, cache pricing and regional/account differences may change the charge. The user's CNY 15 cap was not approached. Runtime used deliberately conservative budget rates 10/50, totaling 4.49748 budget units across these Runs. The GUI's inherited dollar glyph does not establish a currency conversion. [Pricing reference](https://help.aliyun.com/en/model-studio/qwen3-8-flash).

## Video provenance and editing

[Watch or download the real recording](https://github.com/bj-Liu/resumeagent/releases/download/demo-20261103/resumeagent-demo-20261103.mp4).
The 3:40 recording (1920?1080, H.264, silent) combines original GUI recordings with actual Selenium viewport footage
of the final generated site. Input/wait intervals are accelerated at the speeds
shown in captions. A caption discloses the failed refinement and same-Run recovery.
The CLI recovery itself is supported by persisted trace metadata; it is not a
fabricated terminal recording. There is no voice-over or simulated Agent animation.

Original recordings, the editing manifest, full diagnostics, SQLite database and
all backups remain private under `test-artifacts/showcase-live-recording-v2`.
The public video excludes desktop/editor/configuration windows. Only the reviewed
edited MP4 is a GitHub Release asset; large raw videos are not Git objects.

[Machine-readable evidence](../showcase/data/live-demo.json) includes artifact
hashes and safe browser results. [Metadata-only traces](../showcase/data/live-trace.json)
include stages, tools, models, usage and failures, but no prompts/responses,
profile text, API keys or absolute local paths.

[Video checksum and editing provenance](DEMO_VIDEO.json).

Git normalizes generated HTML/CSS from CRLF to LF; the source code content is unchanged. `source_sha256` describes original local model-output bytes and `published_sha256` describes public Git bytes. Screenshots retain their original bytes.
