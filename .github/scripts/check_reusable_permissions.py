#!/usr/bin/env python3
"""Fail when a reusable workflow asks for more permission than its caller grants.

GitHub validates this only when the workflow starts, so a mismatch in a
release-only path stays invisible until a release actually runs and dies with
a startup failure. This catches it in CI instead.
"""

from __future__ import annotations

import pathlib
import sys

import yaml

RANK = {"none": 0, "read": 1, "write": 2}
WORKFLOWS = pathlib.Path(".github/workflows")


def permissions_of(job: dict, workflow: dict) -> dict[str, str] | str:
    """The permissions a job ends up with, falling back to the workflow default."""
    declared = job.get("permissions", workflow.get("permissions"))
    return declared if declared is not None else {}


def main() -> int:
    problems: list[str] = []

    for caller_path in sorted(WORKFLOWS.glob("*.yml")):
        caller = yaml.safe_load(caller_path.read_text())
        for caller_job_id, caller_job in (caller.get("jobs") or {}).items():
            target = caller_job.get("uses", "")
            if not target.startswith("./"):
                continue

            granted = permissions_of(caller_job, caller)
            if isinstance(granted, str):
                # 'read-all' / 'write-all' grant everything at that level.
                continue

            called_path = pathlib.Path(target.removeprefix("./"))
            called = yaml.safe_load(called_path.read_text())

            for called_job_id, called_job in (called.get("jobs") or {}).items():
                requested = permissions_of(called_job, called)
                if isinstance(requested, str):
                    continue

                for scope, level in requested.items():
                    have = RANK.get(granted.get(scope, "none"), 0)
                    want = RANK.get(level, 0)
                    if want > have:
                        problems.append(
                            f"{caller_path}: job '{caller_job_id}' calls {called_path} but grants "
                            f"'{scope}: {granted.get(scope, 'none')}', while its nested job "
                            f"'{called_job_id}' requests '{scope}: {level}'."
                        )

    for problem in problems:
        print(f"::error::{problem}")

    if problems:
        print(f"\n{len(problems)} reusable-workflow permission mismatch(es).")
        return 1

    print("Reusable workflow permissions are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
