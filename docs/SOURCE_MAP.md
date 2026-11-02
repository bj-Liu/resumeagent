# Source map and retained history

| Area | Canonical source | Notes |
|---|---|---|
| Startup | `main.py`, `resumeagent/main.py`, `resumeagent/__main__.py` | GUI / CLI; composed HomepageDesignAgent facade |
| Agents | `resumeagent/agents/` | Planner, Generator and Refiner mixins |
| Quality | `resumeagent/agents/refiner.py`, `resumeagent/tools/filesystem.py` | Integrated evaluation and validation; no QualityAgent class |
| Runtime | `harness/` | Execution, state, context, budget, registry, traces, jobs |
| Storage | `storage/database.py` | SQLite schema; local runs and outputs are private |
| Model adapters | `resumeagent/llm/client.py`, `resumeagent/config.py` | Shared config, provider compatibility and usage observer |
| Tools | `resumeagent/tools/` | Browser, filesystem and helpers; registry provides controlled entry |
| Prompts | `resumeagent/prompts/` | Active English/Chinese templates, shared protocol and design references |
| GUI | `resumeagent/frontend/gui.py` | Active creative studio; `harness_tools.py` adapts managed GUI tools |
| MCP | `resumeagent/mcp_server.py`, `mcp/server.py` | Official SDK server and launch shim |
| Evals | `evals/` | Workflow, recovery, paired benchmark and blinded visual rubric |
| Regression suite | `tests/` | Protocol, adapters, safety, state, GUI and behavior checks |
| Presentation | `showcase/`, `docs/`, `scripts/` | Static website, diagrams, measured evidence and release tooling |

## Retained uncertain/historical source

`resumeagent/frontend/gui_old.py`, `gui_2.py` and `resumeagent/prompts/old/` are
retained. They are historical variants, not new supported execution paths.
Removing them without a separate compatibility review could discard useful prior
work. The private migration archive and old local debug reports also remain on
disk but are excluded from the reviewed public source archive.

The original GitHub main contains pre-modularization root modules and demo media.
Their public history is retained by the backup branch. Pre-modularization root
Python modules and root prompt variants are retained pending a separate migration
review; `main.py` and `resumeagent/` are the canonical release entry points. Old
demo media, generated pages, runtime catalogs, token logs and tracked configuration
are removed from released main rather than presented as a current demonstration.
They remain in the original workspace and original history.
