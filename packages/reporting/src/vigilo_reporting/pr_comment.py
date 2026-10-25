"""build_pr_comment_markdown(): a GitHub PR-comment rendering of a scan's
findings, for `.github/actions/scan`'s optional `post-comment` input. Pure
function, same convention as `build_report()`/`build_sarif_report()` — no
I/O, no self-fetching, every input already fetched by the caller.

A marker HTML comment (`_COMMENT_MARKER`) is prefixed to the output so the
action's upsert step can find and edit its own prior comment on a PR
instead of piling up a new one on every push — the same identity the
marker gives `build_sarif_report`'s SARIF upload for free (GitHub replaces
prior Code Scanning results for the same rule/location automatically); a
plain markdown comment has no such built-in identity, so this module has
to provide one.

Only `FAILED` findings get a table row — `PASSED`/`NOT_APPLICABLE` add no
information a reviewer needs, matching `build_sarif_report`'s own
reportable-findings filter. `INCONCLUSIVE` findings are still surfaced (as
a one-line count), never silently dropped, for the same reason
`build_sarif_report` keeps them as a `note`.
"""

from __future__ import annotations

from vigilo_core.models import CheckManifest, Finding, Score, Severity, Verdict

_COMMENT_MARKER = "<!-- vigilo-scan-comment -->"

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


def _finding_row(finding: Finding, manifest: CheckManifest) -> str:
    remediation = (
        f"<details><summary>Fix</summary>\n\n{manifest.remediation_template}\n\n</details>"
    )
    return (
        f"| {finding.severity.value.upper()} | {finding.title} | {finding.summary} "
        f"| {remediation} |"
    )


def build_pr_comment_markdown(
    target_origin: str,
    findings: list[Finding],
    manifests_by_check_id: dict[str, CheckManifest],
    score: Score,
) -> str:
    failed = sorted(
        (f for f in findings if f.verdict == Verdict.FAILED),
        key=lambda f: _SEVERITY_ORDER.get(f.severity, 99),
    )
    inconclusive_count = sum(1 for f in findings if f.verdict == Verdict.INCONCLUSIVE)

    lines = [
        _COMMENT_MARKER,
        f"### Vigilo security scan — {target_origin}",
        "",
        f"**Score:** {score.value:.1f} ({score.grade})",
        "",
    ]

    if failed:
        lines.extend(
            [
                f"{len(failed)} failed check(s):",
                "",
                "| Severity | Check | Summary | |",
                "|---|---|---|---|",
            ]
        )
        lines.extend(_finding_row(f, manifests_by_check_id[f.check_id]) for f in failed)
    else:
        lines.append("No failed checks.")

    if inconclusive_count:
        lines.append("")
        lines.append(f"_{inconclusive_count} check(s) inconclusive (insufficient evidence)._")

    return "\n".join(lines) + "\n"
