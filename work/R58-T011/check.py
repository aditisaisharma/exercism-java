#!/usr/bin/env python3
"""Run the maintained D&D Character reference against the exercise tests in isolation."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[2]
EXERCISE_REL = Path("exercises/practice/dnd-character")
EXERCISE = REPO_ROOT / EXERCISE_REL
CONFIG_PATH = EXERCISE / ".meta" / "config.json"
REFERENCE = EXERCISE / ".meta" / "src" / "reference" / "java" / "DnDCharacter.java"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), f"(cwd={cwd})")
    return subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)


def main() -> int:
    if not CONFIG_PATH.is_file() or not REFERENCE.is_file():
        print(f"Required exercise metadata/reference not found under {REPO_ROOT}", file=sys.stderr)
        return 2

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    solution_paths = config["files"]["solution"]
    test_paths = config["files"]["test"]
    if not solution_paths or not test_paths:
        print("config.json must define at least one solution and test path", file=sys.stderr)
        return 2

    wrapper = REPO_ROOT / "gradlew"
    if not wrapper.is_file():
        wrapper = EXERCISE / "gradlew"
    if not wrapper.is_file():
        print("Gradle wrapper not found at repository root or exercise root; cannot run ./gradlew test.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="r58-t011-") as temp_name:
        temp_root = Path(temp_name)
        scratch = temp_root / "dnd-character"
        shutil.copytree(EXERCISE, scratch, ignore=shutil.ignore_patterns("build", ".gradle"))
        scratch_wrapper = scratch / "gradlew"
        shutil.copy2(wrapper, scratch_wrapper)
        wrapper_dir = wrapper.parent / "gradle" / "wrapper"
        if wrapper_dir.is_dir():
            shutil.copytree(wrapper_dir, scratch / "gradle" / "wrapper", dirs_exist_ok=True)
        scratch_wrapper.chmod(scratch_wrapper.stat().st_mode | 0o111)

        for relative_solution in solution_paths:
            destination = scratch / relative_solution
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REFERENCE, destination)

        result = run(["./gradlew", "test", "--no-daemon"], scratch)
        print(result.stdout)

        report_files = sorted((scratch / "build" / "test-results" / "test").glob("TEST-*.xml"))
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        for report in report_files:
            root = ET.parse(report).getroot()
            for key in totals:
                totals[key] += int(root.attrib.get(key, "0"))

        evidence = {
            "task": "R58-T011",
            "timestamp_unix": int(time.time()),
            "python": sys.version,
            "platform": platform.platform(),
            "command": "./gradlew test --no-daemon",
            "return_code": result.returncode,
            "test_reports": [str(p.relative_to(scratch)) for p in report_files],
            **totals,
        }
        evidence_path = REPO_ROOT / "work" / "R58-T011" / "latest-result.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2))

        if result.returncode != 0:
            print("FAIL: Gradle returned a non-zero exit code.", file=sys.stderr)
            return result.returncode or 1
        if totals["tests"] == 0:
            print("FAIL: Gradle reported zero executed tests.", file=sys.stderr)
            return 1
        if totals["failures"] or totals["errors"]:
            print("FAIL: one or more tests failed.", file=sys.stderr)
            return 1
        print(f"PASS: {totals['tests']} tests executed; no failures or errors.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
