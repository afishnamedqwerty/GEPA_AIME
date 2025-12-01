from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict
from vllm import LLM, SamplingParams

# Allow running `python src/main.py` by adding project root to sys.path.
if __package__ is None:  # pragma: no cover - runtime convenience
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    __package__ = "src"

from src.core.actor_factory import ActorFactory
from src.core.dynamic_planner import DynamicPlanner
from src.core.progress_manager import ProgressManager
from src.optimizer.gepa_optimizer import LightweightOnlineGEPA
from src.optimizer.signatures import OptimizedDecomposition
from src.utils import helpers
from src.utils.llm import create_llm_client
from src.utils.logging import setup_logger
from src.utils.schemas import load_gepa_config, load_llm_config, load_tool_bundles
from src.workflows.aime_workflow import AIMEWorkflow, WorkflowReport

def load_model_runtime_config(path: str = "config/model_config.yaml") -> dict:
    defaults = {
        "model_id": "allenai/Olmo-3-7B-think",
        "llm": {
            "max_model_len": 16000,
            "gpu_memory_utilization": 0.9,
        },
        "sampling_params": {
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": 4096,
        },
    }
    return helpers.load_yaml_config(path, defaults=defaults)


runtime_config = load_model_runtime_config()
model_id = str(runtime_config.get("model_id", "allenai/Olmo-3-7B-think"))
llm_kwargs = helpers.ensure_dict(runtime_config.get("llm"))
sampling_kwargs = helpers.ensure_dict(runtime_config.get("sampling_params"))

default_llm = LLM(model=model_id, **llm_kwargs)
sampling_params = SamplingParams(**sampling_kwargs)


def build_workflow(default_llm, state_callback=None) -> AIMEWorkflow:
    llm_config = load_model_runtime_config() #load_llm_config()
    gepa_config = load_gepa_config()
    tool_bundles = load_tool_bundles()

    setup_logger(level="INFO", trace_format="text")
    progress_mgr = ProgressManager()
    llm = default_llm#create_llm_client(llm_config)
    planner = DynamicPlanner(llm, progress_mgr, helpers.load_initial_planner_prompt())
    factory = ActorFactory(tool_bundles, progress_mgr, llm)
    student = OptimizedDecomposition(llm)
    gepa = LightweightOnlineGEPA(
        student,
        window_size=gepa_config.max_rollouts,
        trace_path=gepa_config.trace_path,
    )
    return AIMEWorkflow(planner, factory, progress_mgr, gepa, on_update=state_callback)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chat with the configured LLM. Use /goal <text> to start the autonomous workflow."
    )
    parser.add_argument(
        "-viz",
        "--viz",
        action="store_true",
        help="Serve the local dashboard and stream workflow updates to it.",
    )
    parser.add_argument(
        "--viz-port",
        type=int,
        default=8765,
        help="Port for the local dashboard (default: 8765).",
    )
    args = parser.parse_args()

    setup_logger(level="INFO", trace_format="text")
    #llm = create_llm_client(load_llm_config())
    llm = default_llm
    dashboard_state = None
    dashboard_server = None
    state_callback = None
    stop_server = None
    if args.viz:
        from src.utils.viz_server import DashboardState, start_dashboard_server, stop_dashboard_server

        dashboard_state = DashboardState()
        state_callback = dashboard_state.set_state
        try:
            dashboard_server = start_dashboard_server(dashboard_state, port=args.viz_port)
            print(f"[viz] Dashboard running at http://127.0.0.1:{args.viz_port}")
            stop_server = stop_dashboard_server
        except OSError as exc:  # pragma: no cover - runtime safeguard
            print(f"[viz] Failed to start dashboard server: {exc}")
            dashboard_state = None
            state_callback = None
            stop_server = None

    print("Enter a question to chat with the model. Type /goal <text> to launch the workflow or /exit to quit.")
    try:
        while True:
            try:
                user_input = input("> ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in {"/exit", "/quit"}:
                break
            if user_input.startswith("/goal"):
                goal = user_input[len("/goal") :].strip()
                if not goal:
                    print("Please provide a goal after /goal.")
                    continue
                workflow = build_workflow(llm, state_callback=state_callback)
                if dashboard_state:
                    dashboard_state.set_state(
                        {
                            "tasks": [],
                            "gepa": {},
                            "history": [],
                            "tui": "Starting workflow...",
                            "rationale": "",
                        }
                    )
                report: WorkflowReport = workflow.run(goal)
                print(json.dumps(asdict(report), indent=2))
                continue

            try:
                raw_response = llm.generate(user_input, sampling_params=sampling_params)
                if isinstance(raw_response, str):
                    response_text = raw_response
                else:
                    first = raw_response[0]
                    if hasattr(first, "outputs") and first.outputs:
                        response_text = first.outputs[0].text
                    elif hasattr(first, "text"):
                        response_text = first.text
                    else:
                        response_text = str(first)
            except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
                print(f"[error] Failed to query model: {exc}")
                continue
            print(response_text.strip())
    finally:
        if stop_server:
            stop_server(dashboard_server)


if __name__ == "__main__":
    main()
