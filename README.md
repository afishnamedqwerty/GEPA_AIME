# GEPA-AIME: Adaptive Iterative Multi-Agent Execution

GEPA-AIME is a reference implementation of ByteDance's AIME workflow (https://arxiv.org/pdf/2507.11988) for an adaptive, planner-driven multi-agent execution loop enhanced with online GEPA prompt optimization. The project stitches together deterministic components—planner, progress tracker, actor pool, toolbox, and optimizer—so you can plug in your own vLLM endpoint and domain tools while retaining a reproducible, testable workflow.

## Why This Project Exists

- **Deterministic skeleton for advanced agent workflows** – codifies initialization, hierarchical task decomposition, ReAct-style execution, progress updates, evaluation, and termination in one loop.
- **Drop-in vLLM support** – abstracts the language-model client to work with a local stub during development and a production vLLM HTTP endpoint in deployment.
- **Online GEPA optimization** – records execution traces and continuously tunes the planner prompt, persisting learned improvements across runs.
- **Extensible tool ecosystem** – ships with a curated bundle of filesystem and search primitives and a factory pattern for registering custom tools.

## Architecture at a Glance

```
                +--------------------+
                |  LLM Client (vLLM) |
                +----------+---------+
                           |
        +------------------v-----------------+
        |    Dynamic Planner (src/core)      |
        +------------------+-----------------+
                           |
        +------------------v-----------------+
        | ProgressManager (Markdown-backed)  |
        +------------------+-----------------+
                           |
        +------------------v-----------------+
        | ActorFactory -> DynamicActor        |
        |  (tool-aware ReAct execution)       |
        +------------------+-----------------+
                           |
        +------------------v-----------------+
        | LightweightOnlineGEPA Optimizer    |
        |  (prompt refinement + persistence) |
        +------------------+-----------------+
                           |
                +----------v----------+
                |  Workflow Orchestrator |
                |  (AIMEWorkflow.run)    |
                +-----------------------+
```

Each module is test covered via the `tests/` suite so the system remains verifiable even as you swap in real services.

## Getting Started

1. **Install dependencies**
   ```bash
   python3 -m venv ./.venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure your environment**
   - Edit `config/model_config.yaml` with your model name and endpoint details 
   - Review `config/tool_bundles.json` to tailor the tool inventory. (unfinished)

3. **Basic chat inferace or run the workflow**
   Chat with your vllm hosted model or utilize cli commands for workflow customization:
   ```bash
   python -m src.main "/goal Summarise the repository layout and propose next steps"
   ```

   The CLI prints a JSON report containing the goal, progress trace, planner rationale, and task ledger.

   ```bash
   /quit or /exit
   ```
   to terminate CLI session.

4. **Execute the test suite**
   ```bash
   python3 -m unittest discover -s tests -p 'test*.py' -v
   ```

### Live Dashboard (optional)

- Run `python3 src/main.py -viz` to start the local dashboard server (default port `8765`).
- Open `http://127.0.0.1:8765` to see the React dashboard that streams the ordered checklist, live GEPA metrics (composite + timeline), and a TUI-style live view of the markdown checklist that updates after each action.
- The dashboard is off by default; omit `-viz` to keep the CLI-only experience.

## LLM Integration

GEPA-AIME isolates language model dependencies inside `src/utils/llm.py` and `config/model_config.yaml`.

### Local Development

- The planner, actors, and tests depend only on the `generate(prompt)` interface; no network calls occur.

### vLLM Endpoint

Switch to vLLM (or any HTTP JSON API with a similar surface) by updating the config:

```yaml
model: qwen3-235b
provider: vllm
api_base: https://your-vllm-gateway.example.com
request_timeout: 60
extra_params:
  temperature: 0.5
  max_tokens: 2048
  top_p: 0.9
  endpoint: /v1/generate
```

## Tool Bundle and Actor Tooling (unfinished)

All tools live under `src/tools/` and are declaratively registered via `config/tool_bundles.json`. The default bundle includes:

| Tool         | Implementation                              | Purpose                                                     |
|--------------|----------------------------------------------|-------------------------------------------------------------|
| `web_search` | `src.tools.web_tools:WebSearchTool`          | Deterministic search stub synthesising knowledge snippets.  |
| `read_file`  | `src.tools.file_tools:ReadFileTool`          | Reads text files inside the workspace.                      |
| `list_dir`   | `src.tools.file_tools:ListDirectoryTool`     | Lists directory contents with metadata for tool chaining.   |
| `write_file` | `src.tools.file_tools:WriteFileTool`         | Safely writes text to files inside the repo tree.           |
| `update_progress` | `src.tools.update_progress:UpdateProgressTool` | Records structured status updates in `ProgressManager`. |

Highlights of the tooling system:

- **ActorFactory** (`src/core/actor_factory.py`) loads bundles, instantiates classes via `helpers.import_from_string`, and injects shared dependencies (e.g., progress manager for `update_progress`).
- **DynamicActor** (`src/core/dynamic_actor.py`) uses lightweight heuristics to pick tools based on task metadata. For example, if metadata contains `path` and `content` and the task description suggests writing, the actor automatically dispatches `write_file` so generated artifacts are persisted.
- Adding a new tool means implementing `BaseTool.run()`, registering it in `tool_bundles.json`, and optionally annotating task metadata so actors know when to call it.

## Workflow Loop Details

1. **Initialization** (`src/main.py`, `src/workflows/aime_workflow.py`)
   - Load configs (`llm`, `gepa`, tool bundles) via `schemas.py` for validation.
   - Instantiate planner, progress manager, actor factory, GEPA optimizer, and logger.

2. **Task Decomposition** (`src/core/dynamic_planner.py`)
   - `DynamicPlanner.initialize(goal)` splits the goal deterministically (`helpers.split_goal_into_tasks`) and seeds the `ProgressManager` with a Markdown-like checklist.
   - Planner rationale is generated through the configured LLM client, giving traceability for audits.

3. **Task Dispatch & ReAct Execution** (`src/core/dynamic_actor.py`)
   - Progress manager marks the task as `in_progress`.
   - Actor selects a tool (or none) and records `ActorStep(thought, action, observation)` entries, mirroring classic ReAct traces.
   - After tool execution, the actor issues a `finish` step, and the progress manager marks the task as complete while logging history events.

4. **Progress & Evaluation**
   - `ProgressManager` exposes structured history for analytics and human-readable Markdown snapshots.
   - Every outcome is passed to `LightweightOnlineGEPA.record()` along with the planner prompt that produced it.

5. **Iteration & Termination**
   - Planner recomputes task order (`refresh_plan`) after each execution, factoring in updated statuses.
   - Loop exits when all tasks are `complete` or iteration limits are reached; `AIMEWorkflow.run` returns a `WorkflowReport` consolidating goal status, history, tasks, and latest planner rationale.

## GEPA Traces and Prompt Persistence

The optimizer closes the loop between planner performance and prompt evolution:

- Each task outcome is converted into a `TraceExample` (prompt, response, binary score).
- A composite metric (`enhanced_decomp_metric`) balances completion rate and recency using a rolling window.
- When the score dips below 0.5, `OptimizedDecomposition.improve_prompt()` generates an augmented prompt (default behaviour injects a reminder referencing the failing observation).
- Traces are appended as JSON lines to the path configured via `gepa_config.yaml` (`traces/gepa_history.jsonl` by default). Each record captures the original prompt, observation summary, score, and any new prompt produced.
- On startup the optimizer loads the trace file, rebuilds the rolling deque, and restores the strongest prompt (preferring the latest explicit `new_prompt`). The planner warms up with `gepa_optimizer.current_prompt()` so prior learnings immediately influence the first iteration.

This design lets the system accumulate institutional knowledge over time while keeping the optimizer stateless between runs aside from the trace file.

## Configuration Reference

- `config/llm_config.yaml` – LLM provider, endpoint, temperature, and request parameters.
- `config/gepa_config.yaml` – GEPA window sizes, reflection controls, and `trace_path` for persisted history.
- `config/tool_bundles.json` – Declarative tool registry partitioned into bundles (e.g., `default`, `progress`).

All loaders reside in `src/utils/schemas.py`, which converts YAML/JSON into typed dataclasses (`LLMConfig`, `GEPAConfig`, and `ToolBundle`). Unknown keys in `llm_config.yaml` automatically flow into `extra_params`, giving you room for provider-specific tuning knobs without code changes.

## Testing & Quality

The project embraces unit coverage to ensure refactors remain safe:

- `tests/test_progress_manager.py` – Markdown round-tripping and status transitions.
- `tests/test_dynamic_planner.py` – Goal initialization, failure handling, and prompt updates.
- `tests/test_dynamic_actor.py` – Tool dispatch (including `write_file`) and completion semantics.
- `tests/test_gepa_optimizer.py` – Prompt updates, trace persistence, and warm-start recovery.
- `tests/test_end_to_end.py` – Smoke test ensuring the full workflow resolves a synthetic goal.

Run the suite with `python -m unittest discover -s tests -p 'test*.py' -v`.

## Extending the Framework

- **Custom Tools**: add subclasses under `src/tools/`, register them in `tool_bundles.json`, and enrich task metadata so actors know when to invoke them.
- **Multiple Actors / Parallelism**: extend `ActorFactory` to spawn different persona-specific LLM clients or integrate multiprocessing pools (stubs provided in `crush.md`).
- **Advanced Metrics**: plug in a different scoring function via the `metric` argument when constructing `LightweightOnlineGEPA` if you want multi-objective evaluation.
- **Analytics**: consume `traces/gepa_history.jsonl` with your preferred dashboarding tool to visualise prompt evolution and success rates.

### Scaling to Multiple Agents

The framework ships with the scaffolding needed to orchestrate more than one actor:

1. **Instantiate multiple LLM clients** – use `create_llm_client()` with different configs or temperatures to build persona-specific reasoning styles. Pass a custom `llm` argument into `ActorFactory.create_actor()` when you need diversity.
2. **Bundle-specific tools** – define new bundles in `config/tool_bundles.json` (e.g., `research`, `implementation`, `review`). When creating an actor, supply the bundle list so each agent receives only the tools it should operate.
3. **Parallel dispatch** – wrap `actor.execute()` calls inside a thread or process pool. `crush.md` describes spawning a `multiprocessing.Pool`; just make sure to guard shared state (e.g., `ProgressManager`) with locks or channel updates through dedicated tools like `update_progress`.
4. **Task routing logic** – implement a scheduler that inspects `TaskNode` metadata (persona, domain, priority) and decides which actor(s) to allocate. Because `ProgressManager.mark_in_progress()` is centralized, you can safely coordinate multiple workers.
5. **Cross-actor communication** – leverage the `history` log or persist intermediary artifacts via `write_file` so agents can build on each other’s output without loss of context.

These steps let you scale from the default single-agent loop to a fully collaborative team while keeping traceability, progress tracking, and GEPA optimization intact.

## Key Files

| Path | Description |
|------|-------------|
| `src/main.py` | CLI entry point wiring configs, components, and the workflow orchestration. |
| `src/workflows/aime_workflow.py` | Orchestrates initialization, iteration, and report generation. |
| `src/core/` | Planner, actor factory/actors, and progress manager implementations. |
| `src/utils/` | Helpers for config loading, logging, metrics, and LLM abstraction. |
| `src/optimizer/` | GEPA optimizer and signature shims. |
| `tests/` | Unit test coverage for all critical modules. |
| `config/` | YAML/JSON configuration inputs for LLMs, tools, and optimizer. |
| `traces/gepa_history.jsonl` | Persisted GEPA trace file storing prompts and outcomes. |

## Roadmap

1. Replace the placeholder `WebSearchTool` with a real retrieval augmentor (e.g., Tavily, Bing, or internal search).
2. Enrich GEPA trace records with tool usage stats to steer prompt updates more precisely.
3. Add concurrency controls and progress streaming to support long-running goals with multiple actors.
4. Integrate a front-end dashboard that visualises task checklists and GEPA metrics live.
5. Replicate synthetic data judge from Deepseek V3.2 speciale for data generation pipeline.

---
