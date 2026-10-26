"""`vigilo scan-iac <path>`: static container/IaC checks over a local path (no network)."""

import json

import pytest

from vigilo_cli.main import run

INSECURE_DOCKERFILE = "FROM node:latest\nENV API_KEY=abc12345secret\nUSER root\n"
CLEAN_DOCKERFILE = "FROM python:3.12-slim@sha256:" + "0" * 64 + "\nUSER app\n"


def _scan(*argv: str) -> int:
    with pytest.raises(SystemExit) as exc:
        run(["scan-iac", *argv])
    return exc.value.code


def test_reports_findings_in_a_readable_summary(tmp_path, capsys):
    (tmp_path / "Dockerfile").write_text(INSECURE_DOCKERFILE)

    assert _scan(str(tmp_path)) == 0  # no --fail-on: findings alone do not fail the run

    out = capsys.readouterr().out
    assert "VG-IAC-001" in out  # runs as root
    assert "VG-IAC-002" in out  # unpinned base image
    assert "VG-IAC-003" in out  # hardcoded secret


def test_fail_on_gates_the_exit_code_by_severity(tmp_path):
    (tmp_path / "Dockerfile").write_text(INSECURE_DOCKERFILE)

    assert _scan(str(tmp_path), "--fail-on", "high") == 1
    assert _scan(str(tmp_path), "--fail-on", "critical") == 1  # the hardcoded secret is critical


def test_a_clean_project_passes_the_gate(tmp_path, capsys):
    (tmp_path / "Dockerfile").write_text(CLEAN_DOCKERFILE)

    assert _scan(str(tmp_path), "--fail-on", "low") == 0
    assert "No failed checks." in capsys.readouterr().out


def test_json_output_lists_every_finding(tmp_path, capsys):
    (tmp_path / "Dockerfile").write_text(INSECURE_DOCKERFILE)

    _scan(str(tmp_path), "--json")

    payload = json.loads(capsys.readouterr().out)
    assert payload["target_path"] == str(tmp_path)
    failed = {f["check_id"] for f in payload["findings"] if f["verdict"] == "failed"}
    assert {"VG-IAC-001", "VG-IAC-002", "VG-IAC-003"} <= failed


def test_sarif_output_is_a_valid_2_1_0_report(tmp_path, capsys):
    (tmp_path / "Dockerfile").write_text(INSECURE_DOCKERFILE)

    _scan(str(tmp_path), "--sarif")

    report = json.loads(capsys.readouterr().out)
    assert report["version"] == "2.1.0"
    results = report["runs"][0]["results"]
    assert {r["ruleId"] for r in results} >= {"VG-IAC-001", "VG-IAC-003"}


def test_json_and_sarif_cannot_be_combined(tmp_path):
    with pytest.raises(SystemExit) as exc:
        run(["scan-iac", str(tmp_path), "--json", "--sarif"])
    assert exc.value.code == 2  # argparse usage error


def test_a_missing_path_is_an_error_not_a_clean_scan(tmp_path, capsys):
    code = _scan(str(tmp_path / "does-not-exist"), "--fail-on", "critical")

    assert code == 2
    assert "path not found" in capsys.readouterr().err
