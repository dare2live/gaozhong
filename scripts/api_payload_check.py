#!/usr/bin/env python3
"""M5 API payload gate.

HTTP 200 is not enough for operations smoke. This gate validates the JSON shape
and a few business invariants for the core M5 routes.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any, Callable


Failure = tuple[str, str]


def fetch_json(base_url: str, path: str) -> tuple[int, Any]:
    with urllib.request.urlopen(base_url + path, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


def fail_if_error(path: str, payload: Any) -> str | None:
    if isinstance(payload, dict) and payload.get("error"):
        return f"{path}: error payload: {payload['error']}"
    return None


def check_stats(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return "stats payload is not an object"
    err = fail_if_error("/api/stats", payload)
    if err:
        return err
    if int(payload.get("courses", 0)) < 40:
        return f"courses < 40: {payload.get('courses')}"
    sev = payload.get("audit_by_severity") or {}
    if int(sev.get("FAIL", 0)) != 0 or int(sev.get("WARN", 0)) != 0:
        return f"audit severity not clean: {sev}"
    return None


def check_course_list(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return "course list payload is not an object"
    err = fail_if_error("/api/course/list", payload)
    if err:
        return err
    courses = payload.get("courses")
    if not isinstance(courses, list) or len(courses) < 40:
        return f"course list too small: {len(courses) if isinstance(courses, list) else 'not-list'}"
    if int(payload.get("count", 0)) < 40:
        return f"course count < 40: {payload.get('count')}"
    return None


def check_students_list(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return "students list payload is not an object"
    err = fail_if_error("/api/students/list", payload)
    if err:
        return err
    students = payload.get("students")
    if not isinstance(students, list) or not students:
        return "students list empty or not a list"
    first = students[0]
    if not isinstance(first, dict) or not first.get("student_id"):
        return "first student has no student_id"
    return None


def check_student_get(payload: Any, expected_student_id: str) -> str | None:
    if not isinstance(payload, dict):
        return "student get payload is not an object"
    err = fail_if_error("/api/students/get", payload)
    if err:
        return err
    student = payload.get("student")
    if not isinstance(student, dict):
        return "student object missing"
    if student.get("student_id") != expected_student_id:
        return f"student_id mismatch: expected={expected_student_id} got={student.get('student_id')}"
    answers = payload.get("answers")
    if not isinstance(answers, dict) or "total" not in answers or "correct" not in answers:
        return "answers summary missing"
    return None


def run_named_check(
    base_url: str,
    label: str,
    path: str,
    predicate: Callable[[Any], str | None],
) -> tuple[Any, Failure | None]:
    try:
        status, payload = fetch_json(base_url, path)
    except Exception as exc:  # network/JSON failure should fail the gate
        return None, (label, f"{path}: request failed: {type(exc).__name__}: {exc}")
    if status != 200:
        return payload, (label, f"{path}: HTTP {status}")
    err = predicate(payload)
    if err:
        return payload, (label, err)
    return payload, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    failures: list[Failure] = []

    for label, path, predicate in [
        ("api /api/stats payload", "/api/stats", check_stats),
        ("api /api/course/list payload", "/api/course/list", check_course_list),
        ("api /api/students/list payload", "/api/students/list", check_students_list),
    ]:
        _, failure = run_named_check(base_url, label, path, predicate)
        if failure:
            failures.append(failure)
        else:
            print(f"[OK] {label}")

    students_payload, failure = run_named_check(
        base_url,
        "api /api/students/list sample",
        "/api/students/list",
        check_students_list,
    )
    if failure:
        failures.append(failure)
    else:
        sample_id = students_payload["students"][0]["student_id"]
        encoded_id = urllib.parse.quote(str(sample_id), safe="")
        _, failure = run_named_check(
            base_url,
            f"api /api/students/get?id={sample_id} payload",
            f"/api/students/get?id={encoded_id}",
            lambda payload: check_student_get(payload, str(sample_id)),
        )
        if failure:
            failures.append(failure)
        else:
            print(f"[OK] api /api/students/get?id={sample_id} payload")

    if failures:
        print("[FAIL] API payload gate failed", file=sys.stderr)
        for label, detail in failures:
            print(f"- {label}: {detail}", file=sys.stderr)
        return 1

    print("[OK] API payload gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
