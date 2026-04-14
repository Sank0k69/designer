"""
Asset Manager — manages exported assets, caching, and brand asset library.
Bridges Figma exports with local storage and IPC.
"""

from __future__ import annotations
import time
from pathlib import Path


class AssetManager:
    """Manages brand assets — Figma exports + local files."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.store = ctx.store

    async def save_export(self, name: str, url: str, source: str = "figma",
                          tags: list[str] | None = None) -> dict:
        """Save an exported asset reference to store."""
        asset = {
            "name": name,
            "url": url,
            "source": source,
            "tags": tags or [],
            "exported_at": time.time(),
        }
        key = f"assets/{name}"
        await self.store.set(key, asset)
        return asset

    async def get_asset(self, name: str) -> dict | None:
        """Get an asset by name."""
        return await self.store.get(f"assets/{name}")

    async def list_assets(self, tag: str = "") -> list[dict]:
        """List all saved assets, optionally filtered by tag."""
        keys = await self.store.list("assets/")
        assets = []
        for key in keys:
            asset = await self.store.get(key)
            if asset:
                if tag and tag not in asset.get("tags", []):
                    continue
                assets.append(asset)
        return assets

    async def get_brand_kit(self) -> dict:
        """Get the full brand kit — logos, colors, typography, icons."""
        return {
            "logos": await self.list_assets("logo"),
            "icons": await self.list_assets("icon"),
            "graphics": await self.list_assets("graphic"),
            "backgrounds": await self.list_assets("background"),
        }
