<div align="center">

# Designer

### Figma-powered design agent for Imperal Cloud.

**Brand assets. Design tokens. Component export. IPC for other extensions.**

[![Imperal SDK](https://img.shields.io/badge/imperal--sdk-%E2%89%A51.5.0-blue)](https://pypi.org/project/imperal-sdk/)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)

[Features](#-features) | [Quick Start](#-quick-start) | [Architecture](#-architecture) | [IPC API](#-ipc-api) | [Imperal Platform](https://imperal.io)

</div>

---

## What is Designer?

Designer is an **Imperal Cloud extension** that connects your Figma brand files to the platform. It provides brand assets, logos, icons, design tokens, and component exports — both through a chat interface and as an IPC service for other extensions.

When Video Creator needs a logo for a thumbnail, or Content Pipeline needs brand colors for a template — they call Designer via IPC. One source of truth for all visual assets.

```python
# From any other Imperal extension:
logo = await ctx.extensions.call("designer", "get_logo", format="png")
kit  = await ctx.extensions.call("designer", "get_brand_assets")
tokens = await ctx.extensions.call("designer", "get_design_tokens")
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Figma Integration** | Full Figma API client — list components, search, export at any scale/format |
| **Brand Asset Kit** | One-call access to all logos, icons, graphics, backgrounds |
| **Design Tokens** | Extract colors, typography, spacing from Figma files |
| **Component Export** | Export any Figma component as PNG, SVG, PDF at custom scale |
| **Asset Search** | Search saved assets by name or tag, with Figma fallback |
| **Local Caching** | Exports cached locally — fast repeat access, reduced API calls |
| **6 IPC Methods** | `get_brand_assets`, `export_component`, `list_components`, `get_design_tokens`, `search_assets`, `get_logo` |
| **Chat Interface** | Direct user interaction for browsing and exporting assets |
| **Per-Action Pricing** | Pay per export or AI generation — no flat subscription |

---

## Quick Start

```bash
pip install imperal-sdk
git clone https://github.com/Sank0k69/designer.git
cd designer
pip install -e ".[dev]"
```

Configure in the Imperal platform settings or `manifest.json`:

| Setting | Description |
|---------|-------------|
| `figma_token` | Your Figma API token (Personal Access Token) |
| `figma_team_id` | Figma team ID for team-level queries |
| `brand_file_key` | File key of your main brand file in Figma |
| `cache_ttl` | Cache duration in seconds (default: 3600) |

---

## Architecture

```
Other Extensions (Video Creator, Content Pipeline, ...)
     |
     | ctx.extensions.call("designer", "get_logo")
     v
main.py — Extension with 6 @ext.expose() IPC methods + ChatExtension
     |
     +--- FigmaClient
     |       list_components()
     |       search_components()
     |       export_component()
     |       get_design_tokens()
     |
     +--- AssetManager
             get_brand_kit()
             list_assets()
             save_export()
```

### Design Principles

- **IPC-first** — designed as a service for other extensions, not just standalone
- **Cache aggressively** — Figma exports are cached locally to minimize API calls
- **Fallback chain** — local cache first, then Figma API
- **Per-action billing** — exports and AI generations metered separately

---

## IPC API

Every method is callable from other Imperal extensions via `ctx.extensions.call()`.

### `get_brand_assets`

Returns the full brand asset kit (logos, icons, graphics, backgrounds).

```python
kit = await ctx.extensions.call("designer", "get_brand_assets")
# kit.data = {"logos": [...], "icons": [...], "graphics": [...], "backgrounds": [...]}
```

### `get_logo`

Get the company logo. Searches Figma brand file for components named "logo".

```python
logo = await ctx.extensions.call("designer", "get_logo", format="png", scale=2.0)
# logo.data = {"url": "https://...", "name": "Logo Primary"}
```

### `list_components`

List Figma components, optionally filtered by name.

```python
components = await ctx.extensions.call("designer", "list_components", query="icon")
# components.data = {"components": [...], "count": 12}
```

### `export_component`

Export a specific Figma component as an image.

```python
asset = await ctx.extensions.call("designer", "export_component",
                                   component_id="1:234", format="svg", scale=2.0)
# asset.data = {"url": "https://..."}
```

### `search_assets`

Search saved assets by query and/or tag. Falls back to Figma if nothing local.

```python
icons = await ctx.extensions.call("designer", "search_assets",
                                   query="hosting", tag="icon")
# icons.data = {"assets": [...], "count": 5}
```

### `get_design_tokens`

Extract design tokens (colors, typography) from a Figma file.

```python
tokens = await ctx.extensions.call("designer", "get_design_tokens")
# tokens.data = {"colors": {...}, "typography": {...}}
```

---

## Chat Interface

Users can interact with Designer directly through the Imperal chat:

| Function | Description |
|----------|-------------|
| `list_figma_components` | Browse components in a Figma file |
| `export_asset` | Export a component as PNG/SVG |
| `brand_kit` | View the full brand asset kit |
| `design_tokens` | Show brand colors and typography |
| `search` | Search for assets by name or tag |

---

## Configuration

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `figma_token` | string | Yes | Figma Personal Access Token |
| `figma_team_id` | string | No | Team ID for team-level operations |
| `brand_file_key` | string | Yes | File key of main brand file |
| `cache_ttl` | integer | No | Cache TTL in seconds (default: 3600) |

---

## Links

- **Imperal Platform:** [imperal.io](https://imperal.io)
- **Imperal SDK:** [github.com/imperalcloud/imperal-sdk](https://github.com/imperalcloud/imperal-sdk)
- **License:** [AGPL-3.0](LICENSE)

---

<div align="center">

**Built for [Imperal Cloud](https://imperal.io)**

</div>
