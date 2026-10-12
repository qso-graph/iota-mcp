"""Conformance with the Model Context Protocol, revision 2026-07-28.

Nothing in this project's documents required this until 2026-10-11 — not
CLAUDE.md, not .claude/rules/security.md, not MCP-SECURITY-FRAMEWORK.md, not
qso-graph-spec. We documented how to *publish* an MCP server in detail and
never wrote down what makes one *valid*, which is how a missing ``isError`` and
missing annotations reached all 22 servers in the fleet unnoticed.

So these are asserted rather than trusted. ``get_version_info`` is the
cautionary case: a fleet convention nobody tested, which drifted.

Follows ``adif-mcp``, ``solar-mcp``, ``pota-mcp`` and ``wspr-mcp``. What is
particular here is that this server answers from an index built in memory, so
whether a tool is open-world is not obvious from reading one function — see
``test_the_data_is_fetched_not_carried``.

Test IDs: IOTA-C01 onward.
"""

from __future__ import annotations

import asyncio
import pathlib
import re

import pytest
from fastmcp.exceptions import ToolError

from iota_mcp import server

ANNOTATION_HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

# The six that consult the IOTA data, and the one that does not.
READS_IOTA_WORLD = {
    "iota_lookup",
    "iota_search",
    "iota_islands",
    "iota_dxcc",
    "iota_stats",
    "iota_nearby",
}
ANSWERS_FROM_THE_PACKAGE = {"get_version_info"}


def _tools() -> dict[str, object]:
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


def _wire(tool: object) -> dict[str, object]:
    """The serialised annotations, which is what a client reads.

    Asserted on the wire form rather than the Python attributes: the SDK names
    its fields in snake_case and the protocol does not.
    """
    annotations = getattr(tool, "annotations", None)
    assert annotations is not None, "tool declares no annotations"
    return annotations.model_dump(by_alias=True, exclude_none=True)


def _call(name: str):
    """The underlying function of a registered tool."""
    tool = getattr(server, name)
    return getattr(tool, "fn", tool)


class TestToolAnnotations:
    def test_every_tool_declares_all_four_hints(self) -> None:
        """IOTA-C01: the defaults are pessimistic, so silence is the wrong answer.

        Omitting them advertises a read-only tool as ``destructiveHint: true``
        and ``openWorldHint: true``, and the specification tells clients to keep
        a human in the loop for operations like that — so a client may
        reasonably put a confirmation prompt in front of looking up an island
        group.
        """
        for name, tool in _tools().items():
            wire = _wire(tool)
            for hint in ANNOTATION_HINTS:
                assert hint in wire, f"{name} omits {hint} on the wire; got {sorted(wire)}"

    def test_every_tool_reads_and_none_writes(self) -> None:
        """IOTA-C02: the three hints that describe effect.

        Every tool here consults the programme data and reports. Nothing in
        this server writes anything, anywhere.
        """
        for name, tool in _tools().items():
            wire = _wire(tool)
            assert wire["readOnlyHint"] is True, name
            assert wire["destructiveHint"] is False, name
            assert wire["idempotentHint"] is True, name

    def test_open_world_is_read_per_tool(self) -> None:
        """IOTA-C03: the hint that is not the same for all of them."""
        tools = _tools()
        assert set(tools) == READS_IOTA_WORLD | ANSWERS_FROM_THE_PACKAGE
        for name in READS_IOTA_WORLD:
            assert _wire(tools[name])["openWorldHint"] is True, name
        for name in ANSWERS_FROM_THE_PACKAGE:
            assert _wire(tools[name])["openWorldHint"] is False, name

    def test_the_data_is_fetched_not_carried(self) -> None:
        """IOTA-C04: the control, and the one that is not obvious here.

        These tools answer from an index in memory, so a reader could fairly
        conclude they touch nothing outside. They do: the index is built from
        files downloaded from iota-world.org at first use and refreshed on a
        TTL, and none of it is shipped in the wheel. That is what makes
        ``openWorldHint: True`` honest — any of them can trigger a request.

        If the data ever *were* carried in the package, this test is where that
        should be noticed, because the hints would then be wrong.
        """
        src = pathlib.Path(server.__file__).parent
        outbound = re.compile(
            r"urllib\.request\.(urlopen|Request)|httpx\.|requests\.(get|post)"
        )
        reached = [p.name for p in src.rglob("*.py")
                   if outbound.search(p.read_text(encoding="utf-8", errors="replace"))]
        assert reached, "no outbound call found, so openWorldHint: True is not honest"
        shipped = [p.name for p in src.rglob("*") if p.suffix in (".json", ".csv", ".db")]
        assert not shipped, f"data is shipped in the package after all: {shipped}"


class TestToolErrorsAreFlagged:
    """A tool execution error belongs in the result with ``isError: true``.

    The specification states the cost of getting this wrong: otherwise "the LLM
    would not be able to see that an error occurred and self-correct". These
    returned ``{"error": "..."}`` as a *successful* result until #23, which a
    client cannot tell apart from an answer.
    """

    @pytest.fixture
    def broken(self, monkeypatch):
        """A client whose every call fails the way an unreachable source does."""
        class Broken:
            def __getattr__(self, _name):
                def fail(*_args, **_kwargs):
                    raise RuntimeError("iota-world.org request failed")
                return fail

        monkeypatch.setattr(server, "_get_client", lambda: Broken())

    UPSTREAM_CASES = [
        ("iota_lookup", {"refno": "OC-001"}),
        ("iota_search", {"query": "Hawaii"}),
        ("iota_islands", {"refno": "OC-001"}),
        ("iota_dxcc", {"dxcc_num": "110"}),
        ("iota_stats", {}),
        ("iota_nearby", {"latitude": 21.3, "longitude": -157.8}),
    ]

    def test_the_cases_cover_every_tool_that_reads(self) -> None:
        """IOTA-C09: the parametrisation below cannot silently miss one.

        A list written by hand beside a set is a list that falls behind it.
        """
        assert {name for name, _ in self.UPSTREAM_CASES} == READS_IOTA_WORLD

    @pytest.mark.parametrize("name,kwargs", UPSTREAM_CASES)
    def test_an_upstream_failure_is_flagged(self, broken, name, kwargs) -> None:
        """IOTA-C10: every tool that can fail, not a sample of them.

        Parametrised because the old shape was applied by copy and paste: a
        single example would pass while five others still returned a dict.
        """
        with pytest.raises(ToolError, match="iota-world.org request failed"):
            _call(name)(**kwargs)

    def test_an_unknown_reference_is_flagged(self) -> None:
        """IOTA-C11: a well-formed refno the programme has no group for.

        This was ``{"refno": ..., "error": "Not found"}`` — a successful result
        whose payload said it had failed, which a caller could not tell apart
        from the group's details.
        """
        with pytest.raises(ToolError, match="XX-999"):
            _call("iota_lookup")(refno="XX-999")

    def test_asking_for_both_or_neither_is_flagged(self) -> None:
        """IOTA-C12: input the caller can fix.

        ``iota_dxcc`` takes a DXCC number *or* a reference, not both and not
        neither, and saying so is the whole use of the message.
        """
        with pytest.raises(ToolError, match="either dxcc_num or refno"):
            _call("iota_dxcc")()


class TestAnEmptyAnswerIsNotAnError:
    """The distinction the specification draws, and the easy one to get wrong.

    "No group has that reference" and "that DXCC entity has no IOTA groups" read
    alike in English and are not alike at all: the first is a lookup that could
    not be answered, the second is the answer.
    """

    def test_a_dxcc_with_no_groups_is_a_successful_call(self) -> None:
        """IOTA-C20: zero is a count, not a failure."""
        answer = _call("iota_dxcc")(dxcc_num="9999")
        assert isinstance(answer, dict)
        assert answer["iota_count"] == 0

    def test_a_search_matching_nothing_is_a_successful_call(self) -> None:
        """IOTA-C21: the search ran; nothing matched."""
        answer = _call("iota_search")(query="zzzzzznotanisland")
        assert answer["total"] == 0
        assert answer["groups"] == []

    def test_a_normal_lookup_is_also_a_successful_call(self) -> None:
        """IOTA-C22: the control — the above refuses some things, not everything."""
        answer = _call("iota_lookup")(refno="OC-001")
        assert answer["refno"] == "OC-001"


class TestVersionInfoShape:
    def test_it_matches_the_shape_the_fleet_returns(self) -> None:
        """IOTA-C30: the convention that drifted because nobody asserted it."""
        info = _call("get_version_info")()
        assert info["service_name"] == "iota-mcp"
        assert info["service_version"]
        assert info["spec_version"]


class TestRegistration:
    def test_the_seven_tools_a_client_sees(self) -> None:
        """IOTA-C40: calling a function directly is not proof a client can."""
        assert set(_tools()) == READS_IOTA_WORLD | ANSWERS_FROM_THE_PACKAGE
