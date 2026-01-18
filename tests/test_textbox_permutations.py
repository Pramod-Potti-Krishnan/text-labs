#!/usr/bin/env python3
"""
TEXT_BOX API Permutation Tests
==============================

Backend-only test runner for TEXT_BOX atomic endpoint permutations.
Calls Text Service v1.2 Railway endpoint directly via httpx.
Generates markdown report with results.

Usage:
    python test_textbox_permutations.py
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


# Configuration
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "textbox_test_configs.json"
RESULTS_FILE = SCRIPT_DIR / "TEST_RESULTS.md"
TIMEOUT_SECONDS = 60.0


class TestResult:
    """Result of a single test."""

    def __init__(
        self,
        test_id: int,
        name: str,
        description: str,
        passed: bool,
        response_time_ms: float,
        html_chars: int = 0,
        instance_count: int = 0,
        arrangement: str = "",
        error: Optional[str] = None,
        html_preview: str = "",
        config: Optional[Dict] = None
    ):
        self.test_id = test_id
        self.name = name
        self.description = description
        self.passed = passed
        self.response_time_ms = response_time_ms
        self.html_chars = html_chars
        self.instance_count = instance_count
        self.arrangement = arrangement
        self.error = error
        self.html_preview = html_preview
        self.config = config or {}


async def run_test(
    client: httpx.AsyncClient,
    api_url: str,
    test_config: Dict,
    default_config: Dict
) -> TestResult:
    """Run a single test and return the result."""

    test_id = test_config["id"]
    name = test_config["name"]
    description = test_config["description"]
    placeholder_mode = test_config.get("placeholder_mode", True)
    config = test_config["config"]

    # Build request data
    request_data = {
        "prompt": default_config["prompt"],
        "count": test_config.get("count", default_config["count"]),
        "items_per_box": test_config.get("items_per_box", default_config["items_per_box"]),
        "gridWidth": default_config["gridWidth"],
        "gridHeight": default_config["gridHeight"],
        "title_max_chars": default_config["title_max_chars"],
        "item_max_chars": default_config["item_max_chars"],
        "placeholder_mode": placeholder_mode,
        "use_lorem_ipsum": placeholder_mode,
        **config
    }

    start_time = time.perf_counter()

    try:
        response = await client.post(api_url, json=request_data)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code != 200:
            return TestResult(
                test_id=test_id,
                name=name,
                description=description,
                passed=False,
                response_time_ms=elapsed_ms,
                error=f"HTTP {response.status_code}: {response.text[:200]}",
                config=config
            )

        data = response.json()

        if not data.get("success"):
            return TestResult(
                test_id=test_id,
                name=name,
                description=description,
                passed=False,
                response_time_ms=elapsed_ms,
                error=data.get("error", "Unknown error - success=false"),
                config=config
            )

        html = data.get("html", "")
        html_preview = html[:500] if html else ""

        return TestResult(
            test_id=test_id,
            name=name,
            description=description,
            passed=True,
            response_time_ms=elapsed_ms,
            html_chars=len(html),
            instance_count=data.get("instance_count", 0),
            arrangement=data.get("arrangement", ""),
            html_preview=html_preview,
            config=config
        )

    except httpx.TimeoutException:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return TestResult(
            test_id=test_id,
            name=name,
            description=description,
            passed=False,
            response_time_ms=elapsed_ms,
            error="Request timed out",
            config=config
        )

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return TestResult(
            test_id=test_id,
            name=name,
            description=description,
            passed=False,
            response_time_ms=elapsed_ms,
            error=f"{type(e).__name__}: {str(e)}",
            config=config
        )


def generate_markdown_report(results: List[TestResult], api_url: str) -> str:
    """Generate markdown report from test results."""

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    lines = [
        "# TEXT_BOX API Test Results",
        "",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Endpoint**: {api_url}",
        f"**Total Tests**: {total} | **Passed**: {passed} | **Failed**: {failed}",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| # | Test Name | Status | Time (ms) | HTML Chars | Instances | Arrangement |",
        "|---|-----------|--------|-----------|------------|-----------|-------------|",
    ]

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        status_emoji = "+" if r.passed else "x"
        lines.append(
            f"| {r.test_id} | {r.name} | {status} | {r.response_time_ms:.0f} | "
            f"{r.html_chars} | {r.instance_count} | {r.arrangement} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Detailed Results",
        "",
    ])

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.extend([
            f"### Test {r.test_id}: {r.name}",
            "",
            f"- **Status**: {status}",
            f"- **Description**: {r.description}",
            f"- **Response Time**: {r.response_time_ms:.0f}ms",
        ])

        if r.passed:
            lines.extend([
                f"- **HTML Characters**: {r.html_chars}",
                f"- **Instance Count**: {r.instance_count}",
                f"- **Arrangement**: {r.arrangement}",
            ])
        else:
            lines.append(f"- **Error**: {r.error}")

        # Config summary
        config_items = [f"{k}={v}" for k, v in r.config.items()]
        lines.append(f"- **Config**: {', '.join(config_items)}")

        if r.passed and r.html_preview:
            lines.extend([
                "",
                "**HTML Preview** (first 500 chars):",
                "```html",
                r.html_preview,
                "```",
            ])

        lines.append("")

    # Failures section
    failures = [r for r in results if not r.passed]
    if failures:
        lines.extend([
            "---",
            "",
            "## Failures Summary",
            "",
        ])
        for r in failures:
            lines.append(f"- **Test {r.test_id} ({r.name})**: {r.error}")
        lines.append("")

    return "\n".join(lines)


async def main():
    """Main test runner."""

    print("=" * 60)
    print("TEXT_BOX API Permutation Tests")
    print("=" * 60)
    print()

    # Load configuration
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found: {CONFIG_FILE}")
        return

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    api_url = config["api_url"]
    default_config = config["default_config"]
    tests = config["tests"]

    print(f"API URL: {api_url}")
    print(f"Total tests: {len(tests)}")
    print()

    results: List[TestResult] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for i, test_config in enumerate(tests, 1):
            test_id = test_config["id"]
            name = test_config["name"]
            mode = "LLM" if not test_config.get("placeholder_mode", True) else "FAST"

            print(f"[{i:2d}/{len(tests)}] Test {test_id}: {name} ({mode})...", end=" ", flush=True)

            result = await run_test(client, api_url, test_config, default_config)
            results.append(result)

            if result.passed:
                print(f"PASS ({result.response_time_ms:.0f}ms, {result.html_chars} chars)")
            else:
                print(f"FAIL: {result.error}")

    print()
    print("=" * 60)
    print("Generating markdown report...")

    report = generate_markdown_report(results, api_url)

    with open(RESULTS_FILE, "w") as f:
        f.write(report)

    print(f"Report saved to: {RESULTS_FILE}")
    print()

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print("=" * 60)
    print(f"SUMMARY: {passed}/{len(results)} tests passed")
    if failed > 0:
        print(f"         {failed} tests FAILED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
