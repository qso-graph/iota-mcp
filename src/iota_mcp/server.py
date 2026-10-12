"""iota-mcp: MCP server for Islands on the Air — all public, no auth required."""

from __future__ import annotations

import sys
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from . import __spec_version__, __version__
from .client import IOTAClient

mcp = FastMCP(
    "iota-mcp",
    version=__version__,
    instructions=(
        "MCP server for Islands on the Air (IOTA) — group lookup, island search, "
        "DXCC mapping, nearby groups, and programme statistics. "
        "All data is public from iota-world.org, no authentication required."
    ),
)

_client: IOTAClient | None = None


def _get_client() -> IOTAClient:
    """Get or create the shared IOTA client."""
    global _client
    if _client is None:
        _client = IOTAClient()
    return _client


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

# MCP 2026-07-28 tool annotations. The defaults are pessimistic — a tool that
# declares nothing is advertised as destructive, non-idempotent and open-world,
# and the specification tells a client to keep a human in the loop for an
# operation like that. So a client would be entitled to put a confirmation
# prompt in front of looking up an island group. Every tool here reads and none
# writes, so the three effect hints are the same for all of them; only
# openWorldHint differs, and it is read per tool.
#
# The IOTA data is downloaded from iota-world.org at first use and refreshed on
# a TTL — it is not carried in the wheel — so every tool that consults it can
# cause an outbound request and is open-world, even when it answers from the
# index already in memory.
#
# They are a client's UX hint and never a security control: the specification
# requires clients to treat them as untrusted, so none of this replaces the
# reference validation in client.py.
_READS_IOTA_WORLD = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}
_ANSWERS_FROM_THE_PACKAGE = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    # Reports versions carried in the wheel. It opens no connection.
    "openWorldHint": False,
}




def _version_info_payload() -> dict[str, Any]:
    """Build the version info envelope. Pulled into a helper so tests can
    call it directly without going through the FastMCP wrapper."""
    return {
        "service_name": "iota-mcp",
        "service_version": __version__,
        "spec_version": __spec_version__,
    }


@mcp.tool(annotations=_ANSWERS_FROM_THE_PACKAGE)
def get_version_info() -> dict[str, Any]:
    """Get iota-mcp service version and upstream programme data version.

    Returns the running PyPI version of iota-mcp and the IOTA programme
    data revision in use. Use this to confirm fleet alignment across MCP
    deployments — agents can compare service_version and spec_version
    across servers to detect drift without going outside the MCP protocol.

    Returns:
        service_name, service_version (PyPI), and spec_version (IOTA programme data).
    """
    return _version_info_payload()


@mcp.tool(annotations=_READS_IOTA_WORLD)
def iota_lookup(refno: str) -> dict[str, Any]:
    """Look up an IOTA group by reference number.

    Returns group details including name, DXCC entity, bounding box,
    center coordinates, credit percentage, and island count.

    Args:
        refno: IOTA reference number (e.g., NA-005, EU-005, AF-001).

    Returns:
        Group details with coordinates, DXCC mapping, and island count.
    """
    try:
        return _get_client().lookup(refno)
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=_READS_IOTA_WORLD)
def iota_search(query: str, limit: int | None = 25) -> dict[str, Any]:
    """Search IOTA groups and islands by name.

    Searches both group names and individual island names.
    Results are deduplicated by IOTA reference number.

    Args:
        query: Search text (e.g., Hawaii, Shetland, Comoro).
        limit: Maximum results to return (default 25).

    Returns:
        List of matching IOTA groups with details.
    """
    try:
        limit = limit if limit is not None else 25
        results = _get_client().search(query, limit=limit)
        return {"query": query, "total": len(results), "groups": results}
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=_READS_IOTA_WORLD)
def iota_islands(refno: str) -> dict[str, Any]:
    """List all islands and subgroups in an IOTA group.

    Returns the full hierarchy: subgroups containing individual islands.

    Args:
        refno: IOTA reference number (e.g., NA-005, EU-005).

    Returns:
        Subgroup hierarchy with island names and IDs.
    """
    try:
        return _get_client().islands(refno)
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=_READS_IOTA_WORLD)
def iota_dxcc(dxcc_num: str | None = "", refno: str | None = "") -> dict[str, Any]:
    """Bidirectional DXCC-to-IOTA mapping.

    Provide either dxcc_num to find all IOTA groups for a DXCC entity,
    or refno to find which DXCC entities an IOTA group belongs to.

    Args:
        dxcc_num: DXCC entity number (e.g., 291 for USA, 223 for England).
        refno: IOTA reference number (e.g., EU-005).

    Returns:
        Mapping between DXCC entities and IOTA groups.
    """
    try:
        dxcc_num = dxcc_num or ""
        refno = refno or ""
        return _get_client().dxcc_lookup(dxcc_num=dxcc_num, refno=refno)
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=_READS_IOTA_WORLD)
def iota_stats() -> dict[str, Any]:
    """Get IOTA programme summary statistics.

    Returns total groups and islands, breakdown by continent,
    DXCC entity count, and most/least credited groups.

    Returns:
        Programme-wide statistics and summaries.
    """
    try:
        return _get_client().stats()
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=_READS_IOTA_WORLD)
def iota_nearby(
    latitude: float,
    longitude: float,
    limit: int | None = 20,
) -> dict[str, Any]:
    """Find IOTA groups nearest to a location.

    Computes great-circle distance from the given coordinates to
    the center of each IOTA group's bounding box.

    Args:
        latitude: Latitude in decimal degrees (e.g., 43.6 for Boise).
        longitude: Longitude in decimal degrees (e.g., -116.2 for Boise).
        limit: Maximum results to return (default 20).

    Returns:
        List of nearest IOTA groups sorted by distance in km.
    """
    try:
        limit = limit if limit is not None else 20
        results = _get_client().nearby(latitude, longitude, limit=limit)
        return {
            "latitude": latitude,
            "longitude": longitude,
            "total": len(results),
            "groups": results,
        }
    except Exception as e:
        raise ToolError(str(e)) from e


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the iota-mcp server."""
    transport = "stdio"
    port = 8010
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--transport" and i < len(sys.argv) - 1:
            transport = sys.argv[i + 1]
        if arg == "--port" and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])

    # Written out rather than passed through: fastmcp takes a literal, and a
    # str that happens to hold the right word is not the same thing.
    if transport == "streamable-http":
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
