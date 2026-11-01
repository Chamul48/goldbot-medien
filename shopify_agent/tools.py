"""Tools the agent can call, plus their Shopify implementations.

Every tool that changes the store goes through `confirm()` first, so a human
approves each write unless the agent runs with --yes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from .shopify import ShopifyClient, ShopifyError


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required if required is not None else list(properties),
        "additionalProperties": False,
    }


TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_shop_info",
        "description": "Basic facts about the connected store: name, domain, currency.",
        "input_schema": _schema({}),
    },
    {
        "name": "search_products",
        "description": (
            "Search products using Shopify's product search syntax, e.g. 'title:*gold*', "
            "'status:active', 'tag:reel', or '' for all. Returns ids, titles, status, "
            "tags and variants with prices."
        ),
        "input_schema": _schema(
            {
                "query": {"type": "string", "description": "Shopify search query; '' for all."},
                "limit": {"type": "integer", "description": "Max products, 1-50."},
            }
        ),
    },
    {
        "name": "get_product",
        "description": "Full details of one product, including description HTML and media.",
        "input_schema": _schema(
            {"product_id": {"type": "string", "description": "gid://shopify/Product/..."}}
        ),
    },
    {
        "name": "update_product",
        "description": (
            "Update a product's title, description (HTML), tags, or status. Pass null for "
            "fields to leave unchanged. Tags replace the existing tag list. Requires approval."
        ),
        "input_schema": _schema(
            {
                "product_id": {"type": "string"},
                "title": {"type": ["string", "null"]},
                "description_html": {"type": ["string", "null"]},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                "status": {"type": ["string", "null"], "enum": ["ACTIVE", "DRAFT", "ARCHIVED", None]},
            }
        ),
    },
    {
        "name": "update_variant_prices",
        "description": "Set price (and optionally compare-at price) on variants of one product. Requires approval.",
        "input_schema": _schema(
            {
                "product_id": {"type": "string"},
                "variants": {
                    "type": "array",
                    "items": _schema(
                        {
                            "variant_id": {"type": "string"},
                            "price": {"type": "string", "description": "Decimal, e.g. '49.90'"},
                            "compare_at_price": {"type": ["string", "null"]},
                        }
                    ),
                },
            }
        ),
    },
    {
        "name": "list_orders",
        "description": (
            "Recent orders, newest first. Optional Shopify order search query, e.g. "
            "'financial_status:paid', 'created_at:>2026-10-01'."
        ),
        "input_schema": _schema(
            {"query": {"type": "string"}, "limit": {"type": "integer", "description": "1-50"}}
        ),
    },
    {
        "name": "list_local_media",
        "description": "List video/image files in the local media folder that can be uploaded.",
        "input_schema": _schema({}),
    },
    {
        "name": "upload_media",
        "description": (
            "Upload a local video or image (path relative to the media folder) to the store's "
            "Files library, optionally attaching it to a product. Requires approval."
        ),
        "input_schema": _schema(
            {
                "path": {"type": "string"},
                "alt": {"type": "string", "description": "Alt text / description."},
                "product_id": {"type": ["string", "null"], "description": "Attach to this product, or null."},
            }
        ),
    },
    {
        "name": "graphql",
        "description": (
            "Run any Shopify Admin GraphQL query for data the other tools do not cover. "
            "Mutations are allowed but require approval."
        ),
        "input_schema": _schema(
            {
                "query": {"type": "string"},
                "variables_json": {"type": "string", "description": "JSON object of variables, or '{}'."},
            }
        ),
    },
]

for _t in TOOLS:
    _t["strict"] = True

MEDIA_EXTS = {".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _edges(conn: dict[str, Any]) -> list[dict[str, Any]]:
    return [e["node"] for e in conn["edges"]]


def _clamp(n: int | None, lo: int = 1, hi: int = 50, default: int = 10) -> int:
    return max(lo, min(hi, n or default))


class Toolbox:
    def __init__(
        self,
        shop: ShopifyClient,
        media_dir: Path,
        confirm: Callable[[str], bool],
    ) -> None:
        self.shop = shop
        self.media_dir = media_dir.resolve()
        self.confirm = confirm

    def run(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Execute a tool. Returns (result_text, is_error)."""
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            return f"Unknown tool: {name}", True
        try:
            result = fn(**args)
        except (ShopifyError, ValueError, OSError, TypeError) as exc:
            return f"Error: {exc}", True
        return json.dumps(result, ensure_ascii=False, indent=1), False

    def _approve(self, summary: str) -> None:
        if not self.confirm(summary):
            raise ValueError("The user declined this change. Ask what they want instead.")

    # ---- read tools ------------------------------------------------------

    def t_get_shop_info(self) -> Any:
        return self.shop.graphql("{ shop { name myshopifyDomain primaryDomain { url } currencyCode } }")["shop"]

    def t_search_products(self, query: str, limit: int) -> Any:
        data = self.shop.graphql(
            """
            query($q: String, $n: Int!) {
              products(first: $n, query: $q) {
                edges { node {
                  id title handle status vendor productType tags totalInventory
                  variants(first: 20) { edges { node { id title sku price compareAtPrice inventoryQuantity } } }
                } }
              }
            }
            """,
            {"q": query or None, "n": _clamp(limit)},
        )
        products = _edges(data["products"])
        for p in products:
            p["variants"] = _edges(p["variants"])
        return products

    def t_get_product(self, product_id: str) -> Any:
        data = self.shop.graphql(
            """
            query($id: ID!) {
              product(id: $id) {
                id title handle status vendor productType tags descriptionHtml onlineStoreUrl
                seo { title description }
                variants(first: 50) { edges { node { id title sku price compareAtPrice inventoryQuantity } } }
                media(first: 20) { edges { node { id alt mediaContentType status } } }
              }
            }
            """,
            {"id": product_id},
        )
        p = data["product"]
        if p is None:
            raise ValueError(f"No product {product_id}")
        p["variants"] = _edges(p["variants"])
        p["media"] = _edges(p["media"])
        return p

    def t_list_orders(self, query: str, limit: int) -> Any:
        data = self.shop.graphql(
            """
            query($q: String, $n: Int!) {
              orders(first: $n, query: $q, sortKey: CREATED_AT, reverse: true) {
                edges { node {
                  id name createdAt displayFinancialStatus displayFulfillmentStatus
                  totalPriceSet { shopMoney { amount currencyCode } }
                  customer { displayName }
                  lineItems(first: 10) { edges { node { title quantity } } }
                } }
              }
            }
            """,
            {"q": query or None, "n": _clamp(limit)},
        )
        orders = _edges(data["orders"])
        for o in orders:
            o["lineItems"] = _edges(o["lineItems"])
        return orders

    def t_list_local_media(self) -> Any:
        if not self.media_dir.is_dir():
            return []
        return [
            {"path": str(p.relative_to(self.media_dir)), "bytes": p.stat().st_size}
            for p in sorted(self.media_dir.rglob("*"))
            if p.is_file() and p.suffix.lower() in MEDIA_EXTS
        ]

    # ---- write tools -----------------------------------------------------

    def t_update_product(
        self,
        product_id: str,
        title: str | None,
        description_html: str | None,
        tags: list[str] | None,
        status: str | None,
    ) -> Any:
        fields = {
            "title": title,
            "descriptionHtml": description_html,
            "tags": tags,
            "status": status,
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            raise ValueError("Nothing to update.")
        self._approve(f"Update product {product_id}:\n{json.dumps(fields, ensure_ascii=False, indent=1)}")
        data = self.shop.graphql(
            """
            mutation($product: ProductUpdateInput!) {
              productUpdate(product: $product) {
                product { id title status tags }
                userErrors { field message }
              }
            }
            """,
            {"product": {"id": product_id, **fields}},
        )["productUpdate"]
        if data["userErrors"]:
            raise ShopifyError(str(data["userErrors"]))
        return data["product"]

    def t_update_variant_prices(self, product_id: str, variants: list[dict[str, Any]]) -> Any:
        payload = []
        for v in variants:
            item = {"id": v["variant_id"], "price": v["price"]}
            if v.get("compare_at_price") is not None:
                item["compareAtPrice"] = v["compare_at_price"]
            payload.append(item)
        self._approve(f"Set prices on {product_id}:\n{json.dumps(payload, indent=1)}")
        data = self.shop.graphql(
            """
            mutation($pid: ID!, $v: [ProductVariantsBulkInput!]!) {
              productVariantsBulkUpdate(productId: $pid, variants: $v) {
                productVariants { id title price compareAtPrice }
                userErrors { field message }
              }
            }
            """,
            {"pid": product_id, "v": payload},
        )["productVariantsBulkUpdate"]
        if data["userErrors"]:
            raise ShopifyError(str(data["userErrors"]))
        return data["productVariants"]

    def t_upload_media(self, path: str, alt: str, product_id: str | None) -> Any:
        full = (self.media_dir / path).resolve()
        if not full.is_relative_to(self.media_dir) or not full.is_file():
            raise ValueError(f"{path} is not a file inside {self.media_dir}")
        target = f" and attach to {product_id}" if product_id else ""
        self._approve(f"Upload {path} ({full.stat().st_size:,} bytes) to Shopify Files{target}")

        resource_url, content_type = self.shop.staged_upload(full)
        data = self.shop.graphql(
            """
            mutation($files: [FileCreateInput!]!) {
              fileCreate(files: $files) {
                files { id fileStatus alt }
                userErrors { field message }
              }
            }
            """,
            {"files": [{"originalSource": resource_url, "contentType": content_type, "alt": alt}]},
        )["fileCreate"]
        if data["userErrors"]:
            raise ShopifyError(str(data["userErrors"]))
        file = data["files"][0]

        if product_id:
            ref = self.shop.graphql(
                """
                mutation($files: [FileUpdateInput!]!) {
                  fileUpdate(files: $files) {
                    files { id }
                    userErrors { field message }
                  }
                }
                """,
                {"files": [{"id": file["id"], "referencesToAdd": [product_id]}]},
            )["fileUpdate"]
            if ref["userErrors"]:
                raise ShopifyError(f"Uploaded {file['id']} but attaching failed: {ref['userErrors']}")
            file["attachedTo"] = product_id
        file["note"] = "Videos are processed asynchronously; fileStatus may show UPLOADED/PROCESSING first."
        return file

    def t_graphql(self, query: str, variables_json: str) -> Any:
        variables = json.loads(variables_json or "{}")
        if not isinstance(variables, dict):
            raise ValueError("variables_json must be a JSON object")
        if re.search(r"^\s*mutation\b", query, re.IGNORECASE | re.MULTILINE):
            self._approve(f"Run GraphQL mutation:\n{query}\nvariables: {variables_json}")
        return self.shop.graphql(query, variables)
