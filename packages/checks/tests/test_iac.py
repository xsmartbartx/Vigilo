from __future__ import annotations

from datetime import UTC, datetime

from vigilo_checks import IAC_REGISTRY, run_registry
from vigilo_core.evidence import EvidenceBundle, IacFile, IacObservation
from vigilo_core.models import Verdict


def _bundle(files: list[IacFile] | None = None) -> EvidenceBundle:
    iac = IacObservation(files=files or []) if files is not None else None
    return EvidenceBundle(
        bundle_id="b1",
        target_origin="local:/checkout",
        captured_at=datetime.now(UTC),
        iac=iac,
    )


def _findings_by_id(findings):
    return {f.check_id: f for f in findings}


def test_every_iac_check_runs_and_produces_one_finding_each():
    findings = run_registry(_bundle([]), IAC_REGISTRY)
    assert {c.manifest.check_id for c in IAC_REGISTRY} == {f.check_id for f in findings}


def test_checks_are_inconclusive_with_no_iac_evidence_at_all():
    findings = run_registry(_bundle(None), IAC_REGISTRY)
    assert all(f.verdict == Verdict.INCONCLUSIVE for f in findings)


def test_dockerfile_with_no_user_instruction_is_inconclusive_not_confirmed_root():
    # The base image may set its own non-root user, so "no USER" is not proof of root.
    files = [IacFile(path="Dockerfile", kind="dockerfile", content="FROM python:3.11-slim\n")]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.INCONCLUSIVE


def test_dockerfile_with_non_root_user_passes_default_root_check():
    files = [
        IacFile(path="Dockerfile", kind="dockerfile", content="FROM python:3.11-slim\nUSER app\n")
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.PASSED


def test_dockerfile_explicit_user_root_fails():
    files = [IacFile(path="Dockerfile", kind="dockerfile", content="FROM alpine\nUSER root\n")]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.FAILED


def test_unpinned_base_image_fails():
    files = [IacFile(path="Dockerfile", kind="dockerfile", content="FROM node\nUSER app\n")]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-002"].verdict == Verdict.FAILED


def test_pinned_base_image_passes():
    files = [
        IacFile(path="Dockerfile", kind="dockerfile", content="FROM node:20.11-slim\nUSER app\n")
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-002"].verdict == Verdict.PASSED


def test_dockerfile_hardcoded_secret_fails():
    files = [
        IacFile(
            path="Dockerfile",
            kind="dockerfile",
            content="FROM alpine\nUSER app\nENV API_KEY=sk_live_abcdef1234567890\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-003"].verdict == Verdict.FAILED


def test_dockerfile_secret_referencing_build_arg_does_not_fail():
    files = [
        IacFile(
            path="Dockerfile",
            kind="dockerfile",
            content="FROM alpine\nUSER app\nENV API_KEY=${API_KEY}\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-003"].verdict == Verdict.PASSED


def test_compose_privileged_service_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    privileged: true\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-004"].verdict == Verdict.FAILED


def test_compose_docker_socket_mount_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-005"].verdict == Verdict.FAILED


def test_compose_hardcoded_secret_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    environment:\n      DB_PASSWORD: hunter22\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-006"].verdict == Verdict.FAILED


def test_compose_host_network_fails():
    files = [
        IacFile(
            path="docker-compose.yml",
            kind="compose",
            content="services:\n  web:\n    network_mode: host\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-007"].verdict == Verdict.FAILED


def test_kubernetes_allow_privilege_escalation_fails():
    files = [
        IacFile(
            path="deploy.yaml",
            kind="kubernetes",
            content="apiVersion: apps/v1\nkind: Deployment\nsecurityContext:\n  allowPrivilegeEscalation: true\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-008"].verdict == Verdict.FAILED


def test_kubernetes_run_as_root_fails():
    files = [
        IacFile(
            path="deploy.yaml",
            kind="kubernetes",
            content="apiVersion: apps/v1\nkind: Deployment\nsecurityContext:\n  runAsUser: 0\n",
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-009"].verdict == Verdict.FAILED


def test_kubernetes_manifest_with_no_security_context_is_not_flagged_for_run_as_root():
    files = [
        IacFile(
            path="deploy.yaml", kind="kubernetes", content="apiVersion: apps/v1\nkind: Deployment\n"
        )
    ]
    findings = _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))
    assert findings["VG-IAC-009"].verdict == Verdict.PASSED


def test_no_matching_files_is_not_applicable():
    findings = _findings_by_id(run_registry(_bundle([]), IAC_REGISTRY))
    assert findings["VG-IAC-001"].verdict == Verdict.NOT_APPLICABLE
    assert findings["VG-IAC-004"].verdict == Verdict.NOT_APPLICABLE
    assert findings["VG-IAC-008"].verdict == Verdict.NOT_APPLICABLE


# --- review follow-ups: stages, FROM flags, comments, truncation -----------------------------


def _verdict(check_id: str, kind: str, content: str, **file_kwargs) -> Verdict:
    files = [IacFile(path="f", kind=kind, content=content, **file_kwargs)]
    return _findings_by_id(run_registry(_bundle(files), IAC_REGISTRY))[check_id].verdict


def test_from_with_a_platform_flag_is_still_checked_for_pinning():
    assert (
        _verdict("VG-IAC-002", "dockerfile", "FROM --platform=linux/amd64 ubuntu:latest\nUSER a\n")
        == Verdict.FAILED
    )
    assert (
        _verdict("VG-IAC-002", "dockerfile", "FROM --platform=linux/amd64 ubuntu:22.04\n")
        == Verdict.PASSED
    )


def test_a_stage_reference_is_not_mistaken_for_an_unpinned_image():
    content = "FROM python:3.12@sha256:" + "0" * 64 + " AS build\nFROM build\nUSER app\n"
    assert _verdict("VG-IAC-002", "dockerfile", content) == Verdict.PASSED


def test_an_image_set_through_a_build_argument_is_inconclusive():
    assert _verdict("VG-IAC-002", "dockerfile", "ARG BASE\nFROM ${BASE}\n") == Verdict.INCONCLUSIVE


def test_the_user_of_the_final_stage_decides_not_an_earlier_stage():
    # USER in the build stage does not protect the final stage.
    build_only = "FROM alpine:3.20 AS build\nUSER app\nFROM alpine:3.20\n"
    assert _verdict("VG-IAC-001", "dockerfile", build_only) == Verdict.INCONCLUSIVE
    # root in the build stage is harmless when the final stage drops it.
    root_then_app = "FROM alpine:3.20 AS build\nUSER root\nFROM alpine:3.20\nUSER app\n"
    assert _verdict("VG-IAC-001", "dockerfile", root_then_app) == Verdict.PASSED


def test_the_last_user_in_a_stage_wins():
    assert _verdict("VG-IAC-001", "dockerfile", "FROM a:1\nUSER root\nUSER app\n") == Verdict.PASSED
    assert _verdict("VG-IAC-001", "dockerfile", "FROM a:1\nUSER app\nUSER 0\n") == Verdict.FAILED


def test_a_stage_built_on_an_earlier_stage_inherits_its_user():
    inherits = "FROM a:1 AS base\nUSER app\nFROM base\n"
    assert _verdict("VG-IAC-001", "dockerfile", inherits) == Verdict.PASSED
    inherits_root = "FROM a:1 AS base\nUSER root\nFROM base\n"
    assert _verdict("VG-IAC-001", "dockerfile", inherits_root) == Verdict.FAILED


def test_a_commented_out_setting_is_not_reported():
    assert _verdict("VG-IAC-004", "compose", "services:\n  web:\n    # privileged: true\n") == (
        Verdict.PASSED
    )
    trailing = "services:\n  web:\n    privileged: false  # was privileged: true\n"
    assert _verdict("VG-IAC-004", "compose", trailing) == Verdict.PASSED
    k8s = "apiVersion: v1\nkind: Pod\n# allowPrivilegeEscalation: true\n"
    assert _verdict("VG-IAC-008", "kubernetes", k8s) == Verdict.PASSED


def test_an_active_setting_is_still_reported_next_to_comments():
    content = "services:\n  web:\n    # note\n    privileged: true  # needed for tests\n"
    assert _verdict("VG-IAC-004", "compose", content) == Verdict.FAILED


def test_a_hash_inside_a_quoted_value_is_not_a_comment():
    content = 'services:\n  web:\n    environment:\n      PASSWORD: "hunter2 #1"\n'
    assert _verdict("VG-IAC-006", "compose", content) == Verdict.FAILED


def test_a_dockerfile_hash_after_an_instruction_is_part_of_the_command():
    # Only whole-line comments are comments in a Dockerfile.
    content = "FROM a:1\nUSER app\nENV TOKEN=abcd1234 # not a comment\n"
    assert _verdict("VG-IAC-003", "dockerfile", content) == Verdict.FAILED


def test_a_truncated_file_never_passes_a_check():
    clean = "FROM alpine:3.20\nUSER app\n"
    assert _verdict("VG-IAC-002", "dockerfile", clean) == Verdict.PASSED
    assert _verdict("VG-IAC-002", "dockerfile", clean, truncated=True) == Verdict.INCONCLUSIVE


def test_a_truncated_file_still_fails_when_a_problem_was_seen_before_the_cut():
    content = "FROM node:latest\n"
    assert _verdict("VG-IAC-002", "dockerfile", content, truncated=True) == Verdict.FAILED
