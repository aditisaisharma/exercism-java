#!/usr/bin/env python3
"""Run all R58 task checks, push evidence, and submit PRs when GitHub CLI is ready."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE_REPO = "S-AI-Projects/exercism-java"
HEAD_REPO = "aditisaisharma/exercism-java"
REVIEWER = "ankushbisht01"
TASKS = [
    ("R58-T012", 12, "exercises/practice/ocr-numbers", "R58-T012: Document and verify OCR test metadata mapping"),
    ("R58-T013", 13, "exercises/practice/variable-length-quantity", "R58-T013: Prove the VLQ seven-bit boundary with mutation testing"),
    ("R58-T014", 14, "exercises/practice/connect", "R58-T014: Clarify Connect dimensions and winning-direction invariants"),
    ("R58-T015", 15, "exercises/practice/luhn", "R58-T015: Document Luhn complexity and reproducible scaling measurements"),
    ("R58-T016", 16, "exercises/practice/rotational-cipher", "R58-T016: Compare rotational-cipher arithmetic and alphabet lookup"),
    ("R58-T017", 17, "exercises/practice/raindrops", "R58-T017: Add Java modulo guidance for Raindrops"),
    ("R58-T018", 18, "exercises/practice/largest-series-product", "R58-T018: Validate Largest Series Product metadata file paths"),
    ("R58-T019", 19, "exercises/practice/run-length-encoding", "R58-T019: Add an isolated Run Length Encoding reference runner"),
    ("R58-T020", 20, "exercises/practice/circular-buffer", "R58-T020: Explain circular-buffer overwrite and clear contracts"),
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


def submit_with_gh(branch, issue, title, worktree):
    gh = shutil.which("gh")
    compare_url = f"https://github.com/{BASE_REPO}/compare/main...{HEAD_REPO.split('/')[0]}:{branch}?expand=1"
    if not gh:
        return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                "reason": "GitHub CLI (gh) is not installed"}
    auth = command([gh, "auth", "status"], cwd=worktree, check=False)
    if auth.returncode:
        return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                "reason": "GitHub CLI is not authenticated", "detail": auth.stdout[-1500:]}
    account = command([gh, "api", "user", "--jq", ".login"], cwd=worktree, check=False)
    if account.returncode or account.stdout.strip() != HEAD_REPO.split("/")[0]:
        return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                "reason": f"Authenticate gh as {HEAD_REPO.split('/')[0]} before PR creation",
                "detail": account.stdout[-1000:]}

    listing = command([gh, "pr", "list", "--repo", BASE_REPO, "--head",
                       f"{HEAD_REPO.split('/')[0]}:{branch}", "--state", "open",
                       "--json", "number,url"], cwd=worktree, check=False)
    if listing.returncode:
        return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                "reason": "Could not check for an existing PR", "detail": listing.stdout[-1500:]}
    existing = json.loads(listing.stdout or "[]")
    body_file = worktree / "work" / branch / "PR_DESCRIPTION.md"
    if not body_file.is_file():
        return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                "reason": f"Missing PR description file: {body_file}"}

    if existing:
        pr_number = existing[0]["number"]
        pr_url = existing[0]["url"]
        edit = command([gh, "pr", "edit", str(pr_number), "--repo", BASE_REPO,
                        "--title", title, "--body-file", str(body_file)], cwd=worktree, check=False)
        if edit.returncode:
            return {"status": "MANUAL_REQUIRED", "pr_url": pr_url,
                    "reason": "Could not update existing PR description", "detail": edit.stdout[-1500:]}
    else:
        created = command([gh, "pr", "create", "--repo", BASE_REPO,
                           "--head", f"{HEAD_REPO.split('/')[0]}:{branch}",
                           "--base", "main", "--title", title,
                           "--body-file", str(body_file)], cwd=worktree, check=False)
        if created.returncode:
            return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                    "reason": "GitHub CLI could not create the PR", "detail": created.stdout[-1500:]}
        pr_url = next((line.strip() for line in created.stdout.splitlines()
                       if line.strip().startswith("https://github.com/")), "")
        if not pr_url:
            return {"status": "MANUAL_REQUIRED", "compare_url": compare_url,
                    "reason": "PR creation returned no URL", "detail": created.stdout[-1500:]}
        pr_number = int(pr_url.rstrip("/").split("/")[-1])

    review = command([gh, "pr", "edit", str(pr_number), "--repo", BASE_REPO,
                      "--add-reviewer", REVIEWER], cwd=worktree, check=False)
    review_status = "REQUESTED" if review.returncode == 0 else "MANUAL_REQUIRED"

    comments = command([gh, "issue", "view", str(issue), "--repo", BASE_REPO,
                        "--json", "comments"], cwd=worktree, check=False)
    comment_status = "PENDING"
    if comments.returncode == 0:
        try:
            known = json.loads(comments.stdout).get("comments", [])
            already_linked = any(pr_url in item.get("body", "") for item in known)
        except (ValueError, TypeError):
            already_linked = False
        if already_linked:
            comment_status = "ALREADY_LINKED"
        else:
            posted = command([gh, "issue", "comment", str(issue), "--repo", BASE_REPO,
                              "--body", f"Implementation and verification submitted: {pr_url}"],
                             cwd=worktree, check=False)
            comment_status = "POSTED" if posted.returncode == 0 else "MANUAL_REQUIRED"
    else:
        comment_status = "MANUAL_REQUIRED"

    return {"status": "PR_CREATED_OR_FOUND", "pr_number": pr_number, "pr_url": pr_url,
            "review_request": review_status, "issue_link": comment_status,
            "compare_url": compare_url}


def main():
    old_summary = ROOT / "work" / "batch-verification-summary.json"
    if old_summary.exists():
        old_summary.unlink()
    status = command(["git", "status", "--porcelain"]).stdout.strip()
    if status:
        raise RuntimeError("Your working tree is not clean. Commit or stash changes before running the batch verifier.")
    remote = command(["git", "remote", "get-url", "origin"]).stdout.strip()
    if HEAD_REPO not in remote:
        raise RuntimeError(f"Expected origin to be your fork {HEAD_REPO}, got: {remote}")

    results = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="r58-batch-worktrees-") as temporary:
        temp_root = Path(temporary)
        for branch, issue, exercise, title in TASKS:
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

                submission = submit_with_gh(branch, issue, title, worktree)
                task_result = {"task": branch, "status": "PASS",
                               "evidence": relative, "submission": submission}
                results.append(task_result)
                print(f"RESULT: {branch} PASS; evidence pushed; submission={submission['status']}.",
                      flush=True)
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
    print("ALL NINE TASK CHECKS PASSED. Evidence was pushed to each task branch.")
    if shutil.which("gh"):
        print("GitHub CLI submission actions are included above. Check any MANUAL_REQUIRED statuses.")
    else:
        print("GitHub CLI was not available. Use the compare URLs and PR_DESCRIPTION.md files to submit the nine PRs.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FATAL: {error}", file=sys.stderr)
        raise SystemExit(1)
