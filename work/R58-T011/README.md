# R58-T011 evidence

Run from the repository root:

```bash
python3 work/R58-T011/check.py
```

The checker copies the exercise, including dotfiles, into a temporary directory; substitutes the maintained reference only at the configured solution path; runs the Gradle wrapper there; and writes the tool versions, command, return code, test-report paths, and test counts to `latest-result.json`.

The exercise's learner solution is never modified. The current TOML audit records 20 canonical entries: 19 included and 1 excluded, both before and after this task. The excluded UUID is superseded by the included `reimplements` UUID; no inclusion flag is changed.

Execution status at authoring time: not run in this remote editing environment. Run the command locally and retain the generated `latest-result.json` as execution evidence before treating the check as passed.
