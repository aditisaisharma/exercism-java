# Batch verification and submission instructions

This branch is a local orchestration utility only. Do not open a coursework PR from it.

From your existing clone, with a clean working tree and `origin` pointing to `aditisaisharma/exercism-java`, run:

```bash
git fetch origin R58-BATCH-VERIFY
git checkout -B R58-BATCH-VERIFY origin/R58-BATCH-VERIFY
python3 work/verify-all.py
```

The script fetches each task branch, creates a temporary detached worktree, runs that task's checker, adds Java/Gradle/Python/Configlet version information to the result, commits `work/R58-Txxx/latest-result.json` on the corresponding task branch, and pushes that evidence commit to your fork. It continues through all nine tasks if one check fails, then prints a consolidated pass/fail summary.

If GitHub CLI (`gh`) is installed and authenticated with permission to create PRs in `S-AI-Projects/exercism-java`, the script also creates or updates each PR, requests review from `ankushbisht01`, and links the PR in its corresponding issue. The required PR body is read from each task branch's `work/R58-Txxx/PR_DESCRIPTION.md`.

If GitHub CLI is missing or cannot perform one of those actions, the script still completes verification and evidence pushes, then prints the compare URL and the exact PR-description file for each manual submission.

Requirements: Python 3.11 or later, Git, a working JDK, network access for Gradle/Configlet downloads if needed, and permission to push to your fork. The task branches remain separate; this script does not merge them.

If any task fails, the script exits non-zero and prints the failing task and diagnostic output. Do not treat a failed task as submitted; its checker must pass before its PR is considered ready.
