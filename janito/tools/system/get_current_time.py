#!/usr/bin/env python3
"""
GetCurrentTime Tool - Returns the current date and time.

This tool returns the current local and UTC date/time using the popular
ISO 8601 format (e.g. ``2024-01-15T14:30:00+00:00``), which is the most
widely used standard for representing date and time together.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.get_current_time [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
from datetime import datetime, timezone
from typing import Any

from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="r")
class GetCurrentTime(BaseTool):
    """
    Tool for retrieving the current date and time.

    Returns the current time in the popular ISO 8601 format
    (e.g. ``2024-01-15T14:30:00+00:00``), along with both local and
    UTC representations and the active timezone information.
    """

    def run(self, utc: bool = False) -> dict[str, Any]:
        """
        Return the current date and time in ISO 8601 format.

        Args:
            utc (bool): If True, return the time in UTC instead of local time
                (default: False). Both local and UTC values are always
                included in the result regardless of this flag.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating the time was retrieved
                - 'iso_time': the primary time in ISO 8601 format (respects ``utc``)
                - 'local_time': current local time in ISO 8601 format
                - 'utc_time': current UTC time in ISO 8601 format
                - 'date': current date (YYYY-MM-DD)
                - 'timezone': name/offset of the local timezone
                - 'timestamp': Unix timestamp (seconds since epoch)
                - 'error': error message (only present if success is False)
        """
        try:
            self.report_start("🕐 Retrieving current time", end="")

            now_local = datetime.now().astimezone()
            now_utc = datetime.now(timezone.utc)

            local_iso = now_local.isoformat()
            utc_iso = now_utc.isoformat()

            # Primary value respects the `utc` flag.
            iso_time = utc_iso if utc else local_iso

            # Human readable timezone description, e.g. "UTC+02:00" or "UTC".
            offset = now_local.utcoffset()
            if offset is None or offset.total_seconds() == 0:
                tz_name = "UTC"
            else:
                total_seconds = int(offset.total_seconds())
                sign = "+" if total_seconds >= 0 else "-"
                total_seconds = abs(total_seconds)
                hours, remainder = divmod(total_seconds, 3600)
                minutes = remainder // 60
                tz_name = f"UTC{sign}{hours:02d}:{minutes:02d}"

            result = {
                "success": True,
                "iso_time": iso_time,
                "local_time": local_iso,
                "utc_time": utc_iso,
                "date": now_local.strftime("%Y-%m-%d"),
                "timezone": tz_name,
                "timestamp": now_local.timestamp(),
            }

            self.report_result(f"Current time: {iso_time}")
            return result

        except Exception as e:
            self.report_error(f"Error: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# ── CLI testing harness ─────────────────────────────────────────────────
def main():
    """Command line interface for testing the GetCurrentTime tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Return the current date and time in ISO 8601 format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --utc
  %(prog)s --json
        """,
    )

    parser.add_argument(
        "--utc",
        "-u",
        action="store_true",
        help="Return the time in UTC instead of local time",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    result = GetCurrentTime().run(utc=args.utc)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print("  ✅ Current time retrieved")
            print(f"  ISO time : {result['iso_time']}")
            print(f"  Local    : {result['local_time']}")
            print(f"  UTC      : {result['utc_time']}")
            print(f"  Date     : {result['date']}")
            print(f"  Timezone : {result['timezone']}")
            print(f"  Timestamp: {result['timestamp']}")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
