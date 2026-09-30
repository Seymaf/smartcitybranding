"""Runs the Smart City Branding pipeline for one city (Bremen by default).

1. Queries every configured source from the Smart City Components source map.
2. Scores the six smart city components, the three branding pillars and the
   democratic / participatory / innovative values — only from evidence that
   was actually obtained.
3. Runs the integrity (anti-greenwashing) checks.
4. Asks Claude for evidence-cited brand narratives (if ANTHROPIC_API_KEY is set).
5. Archives the day's snapshot to archive/<YYYY-MM-DD>.json.

Every API key is optional: sources without one are reported as
"not configured" and simply contribute no evidence.
"""
from __future__ import annotations

import argparse
import logging
import sys

from core.models import CityBrandPulse, SourceStatus
from engine.orchestrator import CityBrandOrchestrator, save_archive

STATUS_ICON = {
    SourceStatus.OK: "OK",
    SourceStatus.NOT_CONFIGURED: "--",
    SourceStatus.NO_DATA: "EMPTY",
    SourceStatus.ERROR: "FAIL",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate today's evidence-based city brand pulse.")
    parser.add_argument("--refresh", action="store_true", help="Regenerate positioning/identity even if the cache is fresh.")
    parser.add_argument("--no-narratives", action="store_true", help="Skip the Claude narrative step.")
    parser.add_argument("--no-archive", action="store_true", help="Don't write archive/<date>.json.")
    return parser.parse_args()


def fmt(score) -> str:
    return "  n/a" if score is None else f"{score:5.1f}"


def print_report(pulse: CityBrandPulse) -> None:
    line = "=" * 72
    print(line)
    print(f"SMART CITY BRAND PULSE — {pulse.city.name}, {pulse.timestamp[:10]}")
    print(line)

    print("\nSources:")
    for s in pulse.sources:
        detail = f"{s.metrics} metric(s)" if s.status == SourceStatus.OK else (s.error or "")[:90]
        print(f"  [{STATUS_ICON[s.status]:<5}] {s.name:<48} {detail}")
    print(f"\nEvidence coverage: {pulse.evidence_coverage:.0%} of sources returned data; "
          f"{pulse.measured_share:.0%} of evidence weight is live-measured")

    verdict = "verifiable" if pulse.headline_verifiable else "NOT VERIFIABLE — do not publish"
    print(f"\nVitality index: {fmt(pulse.vitality_index)}  ({verdict})")
    print("\nBranding pillars:")
    for p in pulse.pillars.values():
        print(f"  {p.display_name:<24} {fmt(p.score)}")
    print("\nSmart city components (score | share from live measurement):")
    for c in pulse.components.values():
        print(f"  {c.display_name:<24} {fmt(c.score)} | {c.measured_share:.0%} measured")
    print("\nCivic values:")
    for key, v in pulse.values.items():
        print(f"  {key:<24} {fmt(v.score)}  ({len(v.metrics)} metric(s))")

    print("\nIntegrity checks:")
    if not pulse.integrity_flags:
        print("  none")
    for f in pulse.integrity_flags:
        print(f"  [{f.severity.upper()}] {f.message}")

    for n in pulse.narratives.values():
        print(f"\n--- {n.narrative_type.upper()} ({n.status}) ---")
        print(n.text)
        print(f"  evidence: {', '.join(n.cited_metrics) or 'none'}")
        for warning in n.uncited_claims_warning:
            print(f"  WARNING: {warning}")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    orchestrator = CityBrandOrchestrator()
    if not args.no_narratives and not orchestrator.narrator.enabled:
        print("ANTHROPIC_API_KEY not set — skipping narratives.", file=sys.stderr)
    pulse, raw = orchestrator.run_pipeline(with_narratives=not args.no_narratives, force_refresh=args.refresh)
    print_report(pulse)
    if not args.no_archive:
        print(f"\nArchived to {save_archive(pulse, raw)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
