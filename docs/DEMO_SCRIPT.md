# Recorded demonstration guide

The real recording is available as a [GitHub Release asset](https://github.com/bj-Liu/resumeagent/releases/tag/demo-20261103).
See [LIVE_DEMO.md](LIVE_DEMO.md) for exact Run IDs, usage, checks, failure and recovery.

Use the complete [fictional profile](DEMO_PROFILE.md), not private personal data.
The existing GUI is launched with `python main.py --gui`. The optional
`python examples/showcase_demo.py --folder NEW_EMPTY_DIRECTORY` launcher only sets
conservative budgets and the existing GUI; it installs no alternate scheduler.
Its input forms remain manual. Configure an available multimodal model and a
browser driver locally. `.env` is not automatically loaded. Never show config
contents, provider dashboards, environment values or personal Run data in a video.

| Approximate video time | Genuine recorded content |
|---|---|
| 0:00?0:48 | Existing GUI; language, framework and fictional profile entered; accelerated input explicitly captioned |
| 0:48?1:15 | Real Planner request and five validated page specifications; waits accelerated |
| 1:15?1:50 | Actual Generator, Selenium preview and integrated screenshot evaluation; five pages complete |
| 1:50?2:30 | Project page feedback and real Refiner operation; failed attempt and same-Run CLI recovery disclosed |
| Final minute | Actual Selenium browser capture: homepage, education, papers, abstract expansion, research, refined projects and fictional internships |

The recording contains no simulated Agent progress or Mock LLM output. Browser
footage captures actual rendered viewports and real link/button interactions.
There is no separate QualityAgent class: the quality role is Refiner screenshot
evaluation plus Filesystem artifact validation under Runtime control.

For a separate reproducible engineering walkthrough:

```bash
python examples/mcp_client.py
python examples/harness_demo.py --fail-once
python -m evals.run_tests
```

These defaults use Mock providers and must be labeled as such. They exercise real
SDK transport, Runtime and recovery control flow without paid calls. They are
covered by published test evidence, not presented as live model video footage.
Keep original raw captures private; share only the reviewed edited video.
