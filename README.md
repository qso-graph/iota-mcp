<!-- mcp-name: io.github.qso-graph/iota-mcp -->
# iota-mcp

[![PyPI](https://img.shields.io/pypi/v/iota-mcp?label=PyPI&color=blue)](https://pypi.org/project/iota-mcp/)
[![MCP Registry](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fregistry.modelcontextprotocol.io%2Fv0%2Fservers%3Fsearch%3Dio.github.qso-graph%2Fiota-mcp%26version%3Dlatest&query=%24.servers%5B0%5D.server.version&label=MCP%20Registry&color=blue)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.qso-graph/iota-mcp&version=latest)

MCP server for [Islands on the Air (IOTA)](https://www.iota-world.org/) — group lookup, island search, DXCC mapping, nearby groups, and programme statistics through any MCP-compatible AI assistant.

Part of the [qso-graph](https://qso-graph.io/) project. **No authentication required** — all IOTA data is public.

## Install

```bash
uvx iota-mcp            # run it; nothing to install
pip install iota-mcp    # or install it into your own environment
```

## Tools

| Tool | Description |
|------|-------------|
| `iota_lookup` | Look up an IOTA group by reference number (e.g., NA-005) |
| `iota_search` | Search groups and islands by name (e.g., Hawaii, Shetland) |
| `iota_islands` | List all islands and subgroups in an IOTA group |
| `iota_dxcc` | Bidirectional DXCC-to-IOTA mapping |
| `iota_stats` | Programme summary — totals by continent, most/least credited |
| `iota_nearby` | Find IOTA groups nearest to a lat/lon location |
| `get_version_info` | Service version + upstream programme data version (fleet identity attestation) |

## Quick Start

No credentials needed — just install and configure your MCP client.

### Configure your MCP client

iota-mcp works with any MCP-compatible client. Add the server config and restart — tools appear automatically.

#### Claude Desktop

Add to `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude\` on Windows):

```json
{
  "mcpServers": {
    "iota": {
      "command": "uvx",
      "args": ["iota-mcp"]
    }
  }
}
```

#### Claude Code

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "iota": {
      "command": "uvx",
      "args": ["iota-mcp"]
    }
  }
}
```

#### ChatGPT Desktop

```json
{
  "mcpServers": {
    "iota": {
      "command": "uvx",
      "args": ["iota-mcp"]
    }
  }
}
```

#### Cursor

Add to `.cursor/mcp.json` (project-level) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "iota": {
      "command": "uvx",
      "args": ["iota-mcp"]
    }
  }
}
```

#### VS Code / GitHub Copilot

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "iota": {
      "command": "uvx",
      "args": ["iota-mcp"]
    }
  }
}
```

#### Gemini CLI

Add to `~/.gemini/settings.json` (global) or `.gemini/settings.json` (project):

```json
{
  "mcpServers": {
    "iota": {
      "command": "uvx",
      "args": ["iota-mcp"]
    }
  }
}
```

Installed with pip instead? Use `"command": "iota-mcp"` in any config above.

### Ask questions

> "Look up IOTA group NA-005"

> "Search for islands named Shetland"

> "What IOTA groups are near Boise, Idaho?"

> "Show me all islands in EU-005"

> "What IOTA references map to DXCC 291?"

> "Give me IOTA programme statistics"


## Data Source

Data comes from the official [IOTA website](https://www.iota-world.org/) JSON downloads:

- **fulllist.json** — complete group/subgroup/island hierarchy (~1.3 MB)
- **dxcc_matches_one_iota.json** — 1:1 DXCC-to-IOTA mapping (~3.5 KB)

Data is downloaded once and cached for 24 hours (IOTA refreshes daily at 00:00 UTC).

## Testing Without Network

```bash
IOTA_MCP_MOCK=1 iota-mcp
```

## MCP Inspector

```bash
iota-mcp --transport streamable-http --port 8010
```

Then open the MCP Inspector at `http://localhost:8010`.

## Development

```bash
git clone https://github.com/qso-graph/iota-mcp.git
cd iota-mcp
uv sync --group dev
uv run pytest
```

## License

GPL-3.0-or-later
