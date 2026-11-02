# A reproducible 2–3 minute walkthrough

**Recording status: not yet recorded.** This is a script, not evidence that a
video exists. Use fictional data below. Do not show terminal environment values,
provider dashboards, personal profiles, config contents or raw SQLite context.

## Preparation

- Install dependencies, a supported browser and its driver. Use a fresh output
  folder and a vision model actually available to your account. Live calls cost
  money; agree a cap before recording. Use `--max_cost 1 --max_iterations 1` for
  a short demonstration; the units depend on configured pricing.
- Alternatively use `python examples/harness_demo.py --fail-once` for offline
  execution evidence. Explicitly call this a Mock model and simulated PNG browser.
- Start GUI: `python main.py --gui --model YOUR_VISION_MODEL --max_cost 1`.
- Prepare a terminal for `python main.py --storage_root storage --status RUN_ID`
  and `--trace RUN_ID`. Do not use a real person's Run.

## Fictional profile

Name: Zhang San. AI master's student. Interests: large language models, agent
systems and automated decision-making. Project titles: Personal Homepage
Generator; Multi-agent Execution Framework. Skills: Python, PyTorch, Transformer,
RAG, Agent, Selenium, HTML, CSS. No institution, papers, awards, dates, email,
project implementation claims or proficiency numbers are supplied.

Design feedback: “A professional editorial research portfolio. Preserve only
these facts. Use clear typography, restrained color and varied content layouts.
Keep navigation consistent and make the mobile layout readable.”

## Timeline

| Time | On screen | Narration / evidence |
|---|---|---|
| 0:00–0:20 | GUI inputs and fresh Save folder | Explain facts versus art direction. Select language/framework; retain all fields. |
| 0:20–0:40 | Click Plan; show actual returned page specifications | Planner creates an executable description and shared page_style. Never substitute a prepared image for a failed run. Cut waiting time transparently if necessary. |
| 0:40–1:05 | Auto Generate, page states and real screenshots | Runtime owns generation, tool calls, budgets and checkpoints. Different page workers can generate concurrently; Selenium access is locked. |
| 1:05–1:25 | Open Website; inspect desktop/mobile and navigation | Show the actual generated files. Include a visible defect if present instead of claiming perfect quality. |
| 1:25–1:45 | Real screenshot critique and one refinement | “Quality Agent” is a role integrated into Refiner plus artifact validation, not a separate implemented agent. Show actual feedback and the bounded outcome; if no change is requested, say so. |
| 1:45–2:05 | CLI status/trace and offline recovery example | Point to the Run ID, stage, usage and completed-page skipping. Distinguish a simulated injected failure from a real provider failure. |
| 2:05–2:25 | `python examples/mcp_client.py` | Official MCP Client handshake, generate_homepage → Run ID → status → preview. This default example uses Mock and has no paid model call. |
| 2:25–2:45 | Test command and actual result summary | Show fresh test output and benchmark mode labels. HTML checks are not visual quality scores. End with limitations and repository link. |

## Recording and publishing

Record a real walkthrough, edit only waiting time with an explicit label, and
upload to an external video host. Set the `video_url` field in
`showcase/data/evidence.json` to an HTTPS MP4/WebM URL or provide a normal external
watch link in the Demo section. Do not commit a large new MP4. The current cover
is an original diagram/title graphic and is explicitly labeled as a recording
placeholder, not a captured application screen.

The showcase's example webpage screenshot is a real historical Selenium capture
of this fictional profile. Its provenance and limitations are separate from the
new release's Mock benchmark and test results; see [release checks](RELEASE_CHECKS.md).
