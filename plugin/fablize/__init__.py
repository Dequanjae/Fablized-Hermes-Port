"""Hermes-native hooks for fablize's verified workflow disciplines."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("FABLIZE_ROOT", Path.home() / ".hermes" / "extensions" / "fablize")).expanduser()
GATE = ROOT / "scripts" / "gate"
sys.path.insert(0, str(GATE))

from ledger import add_unique, load_ledger, save_ledger, update_ledger  # noqa: E402
from classify_task import classify_prompt, context_for_mode  # noqa: E402
from parse_tool_result import changed_kinds, detect_failure, repeated_failure, verification_record  # noqa: E402
from verify_state import should_block_stop  # noqa: E402


def _prompt_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(part.get("text", "")) for part in value if isinstance(part, dict))
    return ""


def _router_context(prompt: str) -> list[str]:
    low = prompt.lower()
    out: list[str] = []
    if any(word in low for word in ("debug", "bug", "error", "traceback", "stack trace", "crash", "failing", "not working")):
        p = ROOT / "packs" / "investigation-protocol.txt"
        out.append("[fablize:investigation]\n" + p.read_text(encoding="utf-8"))
    if any(word in low for word in ("html", "svg", "game", "canvas", "chart", "render", "website", "webpage")):
        p = ROOT / "packs" / "verification-grounding-pack.txt"
        out.append("[fablize:grounding]\n" + p.read_text(encoding="utf-8"))
    return out


def _ledger_identity(session_id: str = "", **kwargs: Any) -> dict[str, Any]:
    return {"session_id": session_id or "no-session", "cwd": kwargs.get("cwd") or os.getcwd()}


def pre_llm_call(session_id: str = "", user_message: Any = "", **kwargs: Any) -> dict[str, str] | None:
    prompt = _prompt_text(user_message)
    identity = _ledger_identity(session_id, **kwargs)
    mode, risks = classify_prompt(prompt)

    def reset(ledger: dict[str, Any]) -> None:
        ledger.update(task_mode=mode, changed_files_seen=False, change_kinds=[],
                      risk_flags=[], verification_commands=[], verification_results=[],
                      failures=[], stop_blocks=0)
        add_unique(ledger, "risk_flags", risks)

    update_ledger(identity, reset)
    context = [context_for_mode(mode, risks), *_router_context(prompt)]
    return {"context": "\n\n".join(context)} if context else None


def post_tool_call(tool_name: str = "", args: dict[str, Any] | None = None,
                   result: Any = "", session_id: str = "", **kwargs: Any) -> None:
    args = args if isinstance(args, dict) else {}
    raw_result = result
    if isinstance(result, str):
        try:
            raw_result = json.loads(result)
        except json.JSONDecodeError:
            pass
    mapped_name = {"terminal": "Bash", "write_file": "Write", "patch": "Edit"}.get(tool_name, tool_name)
    mapped_args = dict(args)
    if mapped_name in {"Write", "Edit"}:
        mapped_args["file_path"] = args.get("file_path") or args.get("path") or ""
    elif mapped_name == "Bash":
        mapped_args["command"] = args.get("command") or ""
    event = {"session_id": session_id or "no-session", "cwd": kwargs.get("cwd") or os.getcwd(),
             "tool_name": mapped_name, "tool_input": mapped_args, "tool_response": raw_result}
    kinds = changed_kinds(event)
    failure = detect_failure(event)
    verification = verification_record(event)

    def record(ledger: dict[str, Any]) -> None:
        if kinds:
            ledger["changed_files_seen"] = True
            add_unique(ledger, "change_kinds", kinds)
        if verification:
            ledger["verification_results"].append(verification)
            ledger["verification_commands"].append(verification["command"])
        if failure:
            ledger["failures"].append(failure)

    ledger = update_ledger({"session_id": session_id or "no-session", "cwd": event["cwd"]}, record)
    repeat = repeated_failure(ledger.get("failures", [])) if failure else None
    if repeat:
        return


def pre_verify(session_id: str = "", attempt: int = 0, **kwargs: Any) -> dict[str, str] | None:
    identity = _ledger_identity(session_id, **kwargs)
    ledger = load_ledger(identity)
    block, reason = should_block_stop(ledger)
    if not block:
        return None
    ledger["stop_blocks"] = int(ledger.get("stop_blocks") or 0) + 1
    save_ledger(identity, ledger)
    return {"action": "continue", "message": reason}


def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", pre_llm_call)
    ctx.register_hook("post_tool_call", post_tool_call)
    ctx.register_hook("pre_verify", pre_verify)
