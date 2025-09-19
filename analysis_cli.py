"""Command line interface for the analysis engine."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable

from analysis_engine import AnalysisError, AnalysisResult, analyze_website


def _print_list(label: str, items: Iterable[str]) -> None:
    items = [item for item in items if item]
    if not items:
        return
    print(f"\n{label}:")
    for entry in items:
        print(f"  - {entry}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a website redesign opportunity.")
    parser.add_argument("url", help="Website URL to analyze")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the analysis as JSON for downstream tooling.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print the narrative summary instead of the full breakdown.",
    )
    args = parser.parse_args(argv)

    try:
        result: AnalysisResult = analyze_website(args.url)
    except AnalysisError as exc:
        parser.error(str(exc))

    if args.json:
        json.dump(result.to_dict(), sys.stdout, indent=2)
        print()
        return 0

    print(f"Analysis summary for {result.normalized_url}")
    print("=" * 60)
    print(result.summary)

    if args.summary_only:
        return 0

    print("\nKey metrics")
    print("-" * 60)
    print(f"Design score: {result.design_score}/100")
    print(f"Response time: {result.response_time_ms/1000:.2f} s")
    print(f"Page weight: {result.page_size_kb:.0f} KB")
    print(f"HTTP status code: {result.status_code}")
    print(f"Mobile friendly: {'Yes' if result.mobile_friendly else 'No'}")
    if result.last_refresh_years is not None:
        print(f"Last significant refresh: {result.last_refresh_years:.1f} years")
    print("\nDesign breakdown")
    for category, score in result.design_breakdown.items():
        print(f"  - {category}: {score}/100")

    _print_list("Strengths", result.strengths)
    _print_list("Gaps", result.gaps)
    _print_list("Recommended actions", result.recommended_actions)
    _print_list("Evidence points", result.evidence_points)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
