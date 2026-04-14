"""
Designer Extension — Figma-powered design agent for Imperal Cloud.

Provides brand assets, icons, logos, and creative automation.
Other extensions (Video Creator, Content Pipeline, etc.) call via IPC.

IPC usage from another extension:
    # Get logo
    logo = await ctx.extensions.call("designer", "get_logo", format="png")

    # Search assets
    icons = await ctx.extensions.call("designer", "search_assets", query="hosting", tag="icon")

    # Export specific Figma component
    url = await ctx.extensions.call("designer", "export_component",
                                     component_id="1:234", format="svg")

    # Get full brand kit
    kit = await ctx.extensions.call("designer", "get_brand_assets")
"""

from __future__ import annotations

from imperal_sdk import Extension, ChatExtension, ActionResult
from modules.figma_client import FigmaClient
from modules.asset_manager import AssetManager


ext = Extension("designer")


def _get_figma(ctx) -> FigmaClient:
    token = ctx.config.get("figma_token", "")
    ttl = ctx.config.get("cache_ttl", 3600)
    return FigmaClient(token, cache_ttl=ttl)


def _get_file_key(ctx) -> str:
    return ctx.config.get("brand_file_key", "")


# ======================================================================
# IPC Exposed Methods — callable by other extensions
# ======================================================================


@ext.expose("get_brand_assets")
async def ipc_get_brand_assets(ctx) -> ActionResult:
    """
    IPC: Get full brand asset kit (logos, icons, graphics, backgrounds).
    Returns cached exports from Figma + locally saved assets.
    """
    manager = AssetManager(ctx)
    kit = await manager.get_brand_kit()
    return ActionResult.success(data=kit, summary=f"Brand kit: {sum(len(v) for v in kit.values())} assets")


@ext.expose("get_logo")
async def ipc_get_logo(ctx, format: str = "png", scale: float = 2.0) -> ActionResult:
    """
    IPC: Get the company logo as an image URL.
    Searches Figma brand file for components named 'logo'.
    """
    figma = _get_figma(ctx)
    file_key = _get_file_key(ctx)

    if not file_key:
        # Try local assets
        manager = AssetManager(ctx)
        logos = await manager.list_assets("logo")
        if logos:
            return ActionResult.success(data=logos[0])
        return ActionResult.error("No brand file configured. Set brand_file_key in Settings.")

    # Search for logo in Figma
    results = await figma.search_components(ctx, file_key, "logo")
    if not results:
        return ActionResult.error("No component named 'logo' found in brand file.")

    # Export the first logo match
    logo = results[0]
    url = await figma.export_component(ctx, file_key, logo["id"], format=format, scale=scale)
    if not url:
        return ActionResult.error("Failed to export logo from Figma.")

    # Cache it
    manager = AssetManager(ctx)
    asset = await manager.save_export(
        name=f"logo.{format}",
        url=url,
        source="figma",
        tags=["logo", "brand"],
    )

    return ActionResult.success(data={"url": url, "name": logo["name"], **asset})


@ext.expose("list_components")
async def ipc_list_components(ctx, file_key: str = "", query: str = "") -> ActionResult:
    """
    IPC: List Figma components. Optionally filter by name query.
    """
    figma = _get_figma(ctx)
    fk = file_key or _get_file_key(ctx)
    if not fk:
        return ActionResult.error("No file_key provided or configured.")

    if query:
        components = await figma.search_components(ctx, fk, query)
    else:
        components = await figma.list_components(ctx, fk)

    return ActionResult.success(
        data={"components": components, "count": len(components)},
        summary=f"Found {len(components)} components",
    )


@ext.expose("export_component")
async def ipc_export_component(
    ctx,
    component_id: str = "",
    file_key: str = "",
    format: str = "png",
    scale: float = 2.0,
    tag: str = "",
) -> ActionResult:
    """
    IPC: Export a Figma component as image. Returns URL.
    """
    figma = _get_figma(ctx)
    fk = file_key or _get_file_key(ctx)
    if not fk or not component_id:
        return ActionResult.error("file_key and component_id required.")

    url = await figma.export_component(ctx, fk, component_id, format=format, scale=scale)
    if not url:
        return ActionResult.error("Export failed.")

    # Cache locally
    manager = AssetManager(ctx)
    asset = await manager.save_export(
        name=f"{component_id}.{format}",
        url=url,
        source="figma",
        tags=[tag] if tag else ["export"],
    )

    return ActionResult.success(data={"url": url, **asset})


@ext.expose("search_assets")
async def ipc_search_assets(ctx, query: str = "", tag: str = "") -> ActionResult:
    """
    IPC: Search saved assets by query and/or tag.
    Checks local cache first, then Figma if not found.
    """
    manager = AssetManager(ctx)
    local = await manager.list_assets(tag)

    if query:
        q = query.lower()
        local = [a for a in local if q in a.get("name", "").lower()]

    # If nothing local and we have Figma, search there
    if not local and _get_file_key(ctx):
        figma = _get_figma(ctx)
        components = await figma.search_components(ctx, _get_file_key(ctx), query)
        return ActionResult.success(
            data={"assets": [], "figma_components": components},
            summary=f"No local assets, found {len(components)} Figma components matching '{query}'",
        )

    return ActionResult.success(
        data={"assets": local, "count": len(local)},
        summary=f"Found {len(local)} assets",
    )


@ext.expose("get_design_tokens")
async def ipc_get_design_tokens(ctx, file_key: str = "") -> ActionResult:
    """
    IPC: Extract design tokens (colors, typography) from Figma file.
    Useful for maintaining brand consistency across content.
    """
    figma = _get_figma(ctx)
    fk = file_key or _get_file_key(ctx)
    if not fk:
        return ActionResult.error("No file_key provided or configured.")

    tokens = await figma.get_design_tokens(ctx, fk)
    if "error" in tokens:
        return ActionResult.error(tokens["error"])

    return ActionResult.success(data=tokens)


# ======================================================================
# Chat Functions — for direct user interaction
# ======================================================================


@ext.chat("design")
class DesignChat(ChatExtension):
    """Chat interface for the Designer agent."""

    @ext.chat_function("list_figma_components")
    async def chat_list_components(self, ctx, file_key: str = "", query: str = ""):
        """List components from a Figma file."""
        result = await ipc_list_components(ctx, file_key=file_key, query=query)
        return result

    @ext.chat_function("export_asset")
    async def chat_export(self, ctx, component_id: str, format: str = "png"):
        """Export a Figma component as an image."""
        result = await ipc_export_component(ctx, component_id=component_id, format=format)
        return result

    @ext.chat_function("brand_kit")
    async def chat_brand_kit(self, ctx):
        """Show the full brand asset kit."""
        result = await ipc_get_brand_assets(ctx)
        return result

    @ext.chat_function("design_tokens")
    async def chat_tokens(self, ctx):
        """Show brand design tokens (colors, typography)."""
        result = await ipc_get_design_tokens(ctx)
        return result

    @ext.chat_function("search")
    async def chat_search(self, ctx, query: str, tag: str = ""):
        """Search for assets by name or tag."""
        result = await ipc_search_assets(ctx, query=query, tag=tag)
        return result
