#!/usr/bin/env python3
"""Run R58-T012..T020 checks in isolated worktrees and push their result evidence."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TASKS = [
    ("R58-T012", "exercises/practice/ocr-numbers"),
    ("R58-T013", "exercises/practice/variable-length-quantity"),
    ("R58-T014", "exercises/practice/connect"),
    ("R58-T015", "exercises/practice/luhn"),
    ("R58-T016", "exercises/practice/rotational-cipher"),
    ("R58-T017", "exercises/practice/raindrops"),
    ("R58-T018", "exercises/practice/largest-series-product"),
    ("R58-T019", "exercises/practice/run-length-encoding"),
    ("R58-T020", "exercises/practice/circular-buffer"),
]

ROOT = Path(__file__).resolve().parents[1]


def command(args, cwd=ROOT, check=True):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(map(str, args))}\n{result.stdout}")
    return result


def tool_version(args, cwd):
    result = command(args, cwd=cwd, check=False)
    return result.stdout.strip() or f"exit code {result.returncode}"


def main():
    old_summary = ROOT / "work" / "batch-verification-summary.json"
    if old_summary.exists():
        old_summary.unlink()
    status = command(["git", "status", "--porcelain"]).stdout.strip()
    if status:
        raise RuntimeError("Your working tree is not clean. Commit or stash changes before running the batch verifier.")
    remote = command(["git", "remote", "get-url", "origin"]).stdout.strip()
    if "aditisaisharma/exercism-java" not in remote:
        raise RuntimeError(f"Expected origin to be your fork aditisaisharma/exercism-java, got: {remote}")

    results = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="r58-batch-worktrees-") as temporary:
        temp_root = Path(temporary)
        for branch, exercise in TASKS:
            worktree = temp_root / branch
            print(f"\n===== {branch} =====", flush=True)
            try:
                command(["git", "fetch", "origin", branch])
                sha = command(["git", "rev-parse", "FETCH_HEAD"]).stdout.strip()
                command(["git", "worktree", "add", "--detach", str(worktree), sha])
                checker = worktree / "work" / branch / "check.py"
                if not checker.is_file():
                    raise FileNotFoundError(f"Missing checker: {checker}")
                run = command([sys.executable, str(checker)], cwd=worktree, check=False)
                print(run.stdout, end="" if run.stdout.endswith("\n") else "\n")
                if run.returncode:
                    raise RuntimeError(f"{branch} check exited with {run.returncode}")

                result_path = worktree / "work" / branch / "latest-result.json"
                if not result_path.is_file():
                    raise FileNotFoundError(f"Checker did not create {result_path}")
                evidence = json.loads(result_path.read_text())
                evidence["tool_versions"] = {
                    "python": sys.version.splitlines()[0],
                    "java": tool_version(["java", "-version"], worktree),
                    "gradle": tool_version(["./gradlew", "--version"], worktree / exercise),
                    "platform": platform.platform(),
                }
                if branch == "R58-T012" and (worktree / "bin/configlet").is_file():
                    evidence["tool_versions"]["configlet"] = tool_version(
                        ["bin/configlet", "--version"], worktree
                    )
                evidence["batch_verified_at_unix"] = int(time.time())
                result_path.write_text(json.dumps(evidence, indent=2) + "\n")

                relative = f"work/{branch}/latest-result.json"
                command(["git", "add", relative], cwd=worktree)
                staged = command(["git", "diff", "--cached", "--quiet"], cwd=worktree, check=False)
                if staged.returncode == 0:
                    raise RuntimeError(f"{branch} produced no new verification evidence to commit")
                command(["git", "commit", "-m", f"Record {branch} verification evidence"], cwd=worktree)
                command(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], cwd=worktree)
                results.append({"task": branch, "status": "PASS", "evidence": relative})
                print(f"RESULT: {branch} PASS and evidence pushed.", flush=True)
            except Exception as error:
                failures.append({"task": branch, "error": str(error)})
                print(f"RESULT: {branch} FAILED: {error}", file=sys.stderr, flush=True)
            finally:
                if worktree.exists():
                    command(["git", "worktree", "remove", "--force", str(worktree)], check=False)
        command(["git", "worktree", "prune"], check=False)

    summary = {"verified_at_unix": int(time.time()), "passed": results, "failed": failures}
    summary_path = ROOT / "work" / "batch-verification-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print("\n===== BATCH SUMMARY =====")
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit(1)
    print("ALL NINE TASK CHECKS PASSED. Verification evidence was committed and pushed to each task branch.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FATAL: {error}", file=sys.stderr)
        raise SystemExit(1)
