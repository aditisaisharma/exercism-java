# Batch verification instructions

This branch is a local verification utility only. Do not open a coursework PR from it.

From your existing clone, with a clean working tree and `origin` pointing to `aditisaisharma/exercism-java`, run:

```bash
git fetch origin R58-BATCH-VERIFY
git checkout -B R58-BATCH-VERIFY origin/R58-BATCH-VERIFY
python3 work/verify-all.py
```

The script fetches each task branch, creates a temporary detached worktree, runs that task's checker, adds Java/Gradle/Python/Configlet version information to the result, commits `work/R58-Txxx/latest-result.json` on the corresponding task branch, and pushes that evidence commit to your fork. It continues through all nine tasks if one check fails, then prints a consolidated pass/fail summary.

Requirements: Python 3.11 or later, Git, a working JDK, network access for Gradle/Configlet downloads if needed, and permission to push to your fork. The task branches are not merged by this script. It does not create PRs or request reviews.

If any task fails, the script exits non-zero and prints the failing task and its diagnostic output. Do not treat a failed task as submitted; the checker must pass before its PR is marked ready.
