"""
Figma REST API client.

Handles: files, components, image exports, design tokens.
Auth: Personal Access Token or OAuth2 Bearer.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

FIGMA_API = "https://api.figma.com"

# Local cache dir for exported images
CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


class FigmaClient:
    """Figma API client with caching."""

    def __init__(self, token: str, cache_ttl: int = 3600):
        self.token = token
        self.cache_ttl = cache_ttl
        self._file_cache: dict[str, tuple[float, dict]] = {}

    def _headers(self) -> dict:
        return {"X-Figma-Token": self.token}

    async def _get(self, ctx, path: str) -> dict:
        """GET request to Figma API."""
        url = f"{FIGMA_API}{path}"
        resp = await ctx.http.get(url, headers=self._headers())
        if resp.status_code >= 400:
            return {"error": f"Figma API {resp.status_code}: {resp.text[:200]}"}
        return resp.json()

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    async def get_file(self, ctx, file_key: str) -> dict:
        """Get a Figma file (cached)."""
        now = time.time()
        if file_key in self._file_cache:
            cached_at, data = self._file_cache[file_key]
            if now - cached_at < self.cache_ttl:
                return data

        data = await self._get(ctx, f"/v1/files/{file_key}")
        if "error" not in data:
            self._file_cache[file_key] = (now, data)
        return data

    async def get_file_meta(self, ctx, file_key: str) -> dict:
        """Get file metadata."""
        return await self._get(ctx, f"/v1/files/{file_key}/meta")

    async def get_nodes(self, ctx, file_key: str, node_ids: list[str]) -> dict:
        """Get specific nodes from a file."""
        ids = ",".join(node_ids)
        return await self._get(ctx, f"/v1/files/{file_key}/nodes?ids={ids}")

    # ------------------------------------------------------------------
    # Components
    # ------------------------------------------------------------------

    async def list_components(self, ctx, file_key: str) -> list[dict]:
        """List all components in a Figma file."""
        data = await self.get_file(ctx, file_key)
        if "error" in data:
            return []

        components = []
        self._walk_tree(data.get("document", {}), components)
        return components

    def _walk_tree(self, node: dict, out: list, depth: int = 0):
        """Recursively walk Figma tree to find components."""
        node_type = node.get("type", "")
        if node_type in ("COMPONENT", "COMPONENT_SET", "INSTANCE"):
            out.append({
                "id": node.get("id", ""),
                "name": node.get("name", ""),
                "type": node_type,
                "description": node.get("description", ""),
                "width": node.get("absoluteBoundingBox", {}).get("width"),
                "height": node.get("absoluteBoundingBox", {}).get("height"),
            })
        for child in node.get("children", []):
            if depth < 10:  # prevent infinite recursion
                self._walk_tree(child, out, depth + 1)

    async def search_components(self, ctx, file_key: str, query: str) -> list[dict]:
        """Search components by name."""
        components = await self.list_components(ctx, file_key)
        q = query.lower()
        return [c for c in components if q in c["name"].lower()]

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    async def export_images(
        self,
        ctx,
        file_key: str,
        node_ids: list[str],
        format: str = "png",
        scale: float = 2.0,
    ) -> dict[str, str]:
        """
        Export nodes as images. Returns {node_id: image_url}.
        Formats: png, jpg, svg, pdf
        """
        ids = ",".join(node_ids)
        data = await self._get(
            ctx,
            f"/v1/images/{file_key}?ids={ids}&format={format}&scale={scale}"
        )
        if "error" in data:
            return {}
        return data.get("images", {})

    async def export_component(
        self,
        ctx,
        file_key: str,
        component_id: str,
        format: str = "png",
        scale: float = 2.0,
    ) -> str:
        """Export a single component. Returns image URL."""
        images = await self.export_images(ctx, file_key, [component_id], format, scale)
        return images.get(component_id, "")

    # ------------------------------------------------------------------
    # Design Tokens
    # ------------------------------------------------------------------

    async def get_design_tokens(self, ctx, file_key: str) -> dict:
        """Extract design tokens (colors, typography, spacing) from a file."""
        data = await self.get_file(ctx, file_key)
        if "error" in data:
            return data

        styles = data.get("styles", {})
        tokens = {"colors": [], "typography": [], "effects": []}

        for style_id, style in styles.items():
            style_type = style.get("styleType", "")
            entry = {
                "id": style_id,
                "name": style.get("name", ""),
                "description": style.get("description", ""),
            }
            if style_type == "FILL":
                tokens["colors"].append(entry)
            elif style_type == "TEXT":
                tokens["typography"].append(entry)
            elif style_type in ("EFFECT", "GRID"):
                tokens["effects"].append(entry)

        return tokens

    # ------------------------------------------------------------------
    # Teams & Projects (OAuth2 only)
    # ------------------------------------------------------------------

    async def list_projects(self, ctx, team_id: str) -> list[dict]:
        """List projects in a team."""
        data = await self._get(ctx, f"/v1/teams/{team_id}/projects")
        return data.get("projects", [])

    async def list_files(self, ctx, project_id: str) -> list[dict]:
        """List files in a project."""
        data = await self._get(ctx, f"/v1/projects/{project_id}/files")
        return data.get("files", [])
