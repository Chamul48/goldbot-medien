"""Tools the agent can call, plus their Shopify implementations.

Every tool that changes the store goes through `confirm(kind, summary)` first.
Interactively a human approves each write; in autopilot mode a policy decides
by `kind` (content, media, price, status, graphql) and anything it may not do
alone is recorded as an escalation for the owner.
"""

from __future__ import annotations

import datetime
import json
import re
import time
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
            "Update a product's title, description (HTML), tags, product type, SEO title/description "
            "or status. Pass null for fields to leave unchanged. Tags replace the existing tag list. "
            "SEO title max 70 characters, SEO description max 160. Requires approval."
        ),
        "input_schema": _schema(
            {
                "product_id": {"type": "string"},
                "title": {"type": ["string", "null"]},
                "description_html": {"type": ["string", "null"]},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                "status": {"type": ["string", "null"], "enum": ["ACTIVE", "DRAFT", "ARCHIVED", None]},
                "product_type": {"type": ["string", "null"]},
                "seo_title": {"type": ["string", "null"]},
                "seo_description": {"type": ["string", "null"]},
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
        "name": "set_media_alt",
        "description": (
            "Set the alt text of product images/videos (media ids from get_product). Describe what "
            "is visible, in German, max ~125 characters. Requires approval."
        ),
        "input_schema": _schema(
            {
                "items": {
                    "type": "array",
                    "items": _schema({"media_id": {"type": "string"}, "alt": {"type": "string"}}),
                }
            }
        ),
    },
    {
        "name": "list_collections",
        "description": "All collections with description, SEO, image and product count.",
        "input_schema": _schema({}),
    },
    {
        "name": "update_collection",
        "description": (
            "Update a collection's description (HTML) and/or SEO title/description. Pass null to "
            "leave a field unchanged. Requires approval."
        ),
        "input_schema": _schema(
            {
                "collection_id": {"type": "string"},
                "description_html": {"type": ["string", "null"]},
                "seo_title": {"type": ["string", "null"]},
                "seo_description": {"type": ["string", "null"]},
            }
        ),
    },
    {
        "name": "create_collection",
        "description": (
            "Create a new collection as a smart collection from tag/type rules, or a manual one with "
            "product ids. It is created unpublished; the owner decides about publishing. Requires approval."
        ),
        "input_schema": _schema(
            {
                "title": {"type": "string"},
                "description_html": {"type": "string"},
                "product_ids": {"type": ["array", "null"], "items": {"type": "string"}},
                "tag_rule": {"type": ["string", "null"], "description": "Products with this tag (smart collection)."},
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
    {
        "name": "escalate",
        "description": (
            "Hand something to the owner that needs a human decision: a price change, "
            "deleting/archiving, a customer problem, an unclear choice, or an error you cannot fix."
        ),
        "input_schema": _schema(
            {
                "topic": {"type": "string", "description": "Short title."},
                "details": {"type": "string", "description": "What you found and what you recommend."},
            }
        ),
    },
]

for _t in TOOLS:
    _t["strict"] = True

MEDIA_EXTS = {".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _edges(conn: dict[str, Any]) -> list[dict[str, Any]]:
    return [e["node"] for e in conn["edges"]]


def _seo(title: str | None, description: str | None) -> dict[str, str]:
    seo = {}
    if title is not None:
        if len(title) > 70:
            raise ValueError(f"SEO title is {len(title)} characters; keep it at 70 or fewer.")
        seo["title"] = title
    if description is not None:
        if len(description) > 160:
            raise ValueError(f"SEO description is {len(description)} characters; keep it at 160 or fewer.")
        seo["description"] = description
    return seo


def _clamp(n: int | None, lo: int = 1, hi: int = 50, default: int = 10) -> int:
    return max(lo, min(hi, n or default))


class Toolbox:
    def __init__(
        self,
        shop: ShopifyClient,
        media_dir: Path,
        confirm: Callable[[str, str], bool],
        state_file: Path | None = None,
    ) -> None:
        self.shop = shop
        self.media_dir = media_dir.resolve()
        self.confirm = confirm
        self.state_file = state_file
        self.state: dict[str, Any] = {"uploaded": {}}
        if state_file and state_file.is_file():
            self.state = json.loads(state_file.read_text())
            self.state.setdefault("uploaded", {})
        self.escalations: list[dict[str, str]] = []
        self.sleep = time.sleep
        self.ready_polls = 20
        self.ready_wait = 3.0

    def _save_state(self) -> None:
        if self.state_file:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=1))

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

    def _approve(self, kind: str, summary: str) -> None:
        if not self.confirm(kind, summary):
            raise ValueError(
                "Not approved. In chat: ask the owner what they want instead. "
                "In autopilot: this was recorded for the owner; do not retry it another way."
            )

    def _full_seo(self, kind: str, gid: str, title: str | None, description: str | None) -> dict[str, str]:
        """SEO input with both fields, so changing one never blanks the other."""
        seo = _seo(title, description)
        if len(seo) == 1:
            cur = self.shop.graphql(
                f"query($id: ID!) {{ {kind}(id: $id) {{ seo {{ title description }} }} }}", {"id": gid}
            )[kind]
            current = (cur or {}).get("seo") or {}
            seo = {"title": current.get("title") or "", "description": current.get("description") or "", **seo}
        return seo

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
            {
                "path": (rel := p.relative_to(self.media_dir).as_posix()),
                "bytes": p.stat().st_size,
                "already_uploaded": rel in self.state["uploaded"],
                "attach_pending": bool(self.state["uploaded"].get(rel, {}).get("attach_pending")),
            }
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
        product_type: str | None = None,
        seo_title: str | None = None,
        seo_description: str | None = None,
    ) -> Any:
        fields: dict[str, Any] = {
            "title": title,
            "descriptionHtml": description_html,
            "tags": tags,
            "status": status,
            "productType": product_type,
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        seo = self._full_seo("product", product_id, seo_title, seo_description)
        if seo:
            fields["seo"] = seo
        if not fields:
            raise ValueError("Nothing to update.")
        kind = "status" if status is not None else "content"
        self._approve(kind, f"Update product {product_id}:\n{json.dumps(fields, ensure_ascii=False, indent=1)}")
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
        self._approve("price", f"Set prices on {product_id}:\n{json.dumps(payload, indent=1)}")
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
        path = full.relative_to(self.media_dir).as_posix()
        done = self.state["uploaded"].get(path)
        if done and done.get("attach_pending") and product_id:
            return self._attach_when_ready(path, done["file_id"], product_id)
        if done:
            raise ValueError(f"{path} was already uploaded as {done['file_id']} on {done['date']}.")
        target = f" and attach to {product_id}" if product_id else ""
        self._approve("media", f"Upload {path} ({full.stat().st_size:,} bytes) to Shopify Files{target}")

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
        # Remember the upload immediately, so a later failure can never cause a second upload.
        self.state["uploaded"][path] = {
            "file_id": file["id"],
            "product_id": None,
            "attach_pending": bool(product_id),
            "date": datetime.date.today().isoformat(),
        }
        self._save_state()
        if product_id:
            return self._attach_when_ready(path, file["id"], product_id)
        file["note"] = "Videos are processed asynchronously; fileStatus may show UPLOADED/PROCESSING first."
        return file

    def _file_status(self, file_id: str) -> str | None:
        node = self.shop.graphql(
            "query($id: ID!) { node(id: $id) { ... on File { fileStatus } } }", {"id": file_id}
        )["node"]
        return (node or {}).get("fileStatus")

    def _attach_when_ready(self, path: str, file_id: str, product_id: str) -> Any:
        """Attach only once Shopify has processed the file; otherwise leave it pending."""
        status = None
        for i in range(self.ready_polls):
            status = self._file_status(file_id)
            if status in ("READY", "FAILED"):
                break
            if i + 1 < self.ready_polls:
                self.sleep(self.ready_wait)
        entry = self.state["uploaded"][path]
        if status == "FAILED":
            entry["attach_pending"] = False
            entry["failed"] = True
            self._save_state()
            raise ShopifyError(f"Shopify could not process {path} ({file_id}); not attached.")
        if status != "READY":
            return {"id": file_id, "fileStatus": status, "attachedTo": None,
                    "note": "Still processing. Call upload_media again with the same path and product later to attach it."}
        ref = self.shop.graphql(
            """
            mutation($files: [FileUpdateInput!]!) {
              fileUpdate(files: $files) {
                files { id }
                userErrors { field message }
              }
            }
            """,
            {"files": [{"id": file_id, "referencesToAdd": [product_id]}]},
        )["fileUpdate"]
        if ref["userErrors"]:
            raise ShopifyError(f"Uploaded {file_id} but attaching failed: {ref['userErrors']}")
        entry.update({"product_id": product_id, "attach_pending": False})
        self._save_state()
        return {"id": file_id, "fileStatus": status, "attachedTo": product_id}

    def t_set_media_alt(self, items: list[dict[str, str]]) -> Any:
        if not items:
            raise ValueError("No media given.")
        for it in items:
            if not it["alt"].strip():
                raise ValueError(f"Empty alt text for {it['media_id']}.")
            if len(it["alt"]) > 512:
                raise ValueError(f"Alt text for {it['media_id']} is too long (max 512).")
        lines = "\n".join(f"- {it['media_id']}: {it['alt']}" for it in items)
        self._approve("content", f"Set alt texts:\n{lines}")
        data = self.shop.graphql(
            """
            mutation($files: [FileUpdateInput!]!) {
              fileUpdate(files: $files) {
                files { id alt }
                userErrors { field message }
              }
            }
            """,
            {"files": [{"id": it["media_id"], "alt": it["alt"].strip()} for it in items]},
        )["fileUpdate"]
        if data["userErrors"]:
            raise ShopifyError(str(data["userErrors"]))
        return data["files"]

    def t_list_collections(self) -> Any:
        from .audit import snapshot_collections

        return snapshot_collections(self.shop)

    def t_update_collection(
        self,
        collection_id: str,
        description_html: str | None,
        seo_title: str | None,
        seo_description: str | None,
    ) -> Any:
        fields: dict[str, Any] = {}
        if description_html is not None:
            fields["descriptionHtml"] = description_html
        seo = self._full_seo("collection", collection_id, seo_title, seo_description)
        if seo:
            fields["seo"] = seo
        if not fields:
            raise ValueError("Nothing to update.")
        self._approve("content", f"Update collection {collection_id}:\n{json.dumps(fields, ensure_ascii=False, indent=1)}")
        data = self.shop.graphql(
            """
            mutation($input: CollectionInput!) {
              collectionUpdate(input: $input) {
                collection { id title }
                userErrors { field message }
              }
            }
            """,
            {"input": {"id": collection_id, **fields}},
        )["collectionUpdate"]
        if data["userErrors"]:
            raise ShopifyError(str(data["userErrors"]))
        return data["collection"]

    def t_create_collection(
        self,
        title: str,
        description_html: str,
        product_ids: list[str] | None,
        tag_rule: str | None,
    ) -> Any:
        if bool(product_ids) == bool(tag_rule):
            raise ValueError("Give either product_ids (manual) or tag_rule (smart), not both or neither.")
        col: dict[str, Any] = {"title": title, "descriptionHtml": description_html}
        if tag_rule:
            col["ruleSet"] = {
                "appliedDisjunctively": False,
                "rules": [{"column": "TAG", "relation": "EQUALS", "condition": tag_rule}],
            }
        else:
            col["products"] = product_ids
        what = f"tag = {tag_rule}" if tag_rule else f"{len(product_ids or [])} products"
        self._approve("content", f"Create unpublished collection '{title}' ({what})")
        data = self.shop.graphql(
            """
            mutation($input: CollectionInput!) {
              collectionCreate(input: $input) {
                collection { id title handle }
                userErrors { field message }
              }
            }
            """,
            {"input": col},
        )["collectionCreate"]
        if data["userErrors"]:
            raise ShopifyError(str(data["userErrors"]))
        return data["collection"]

    def t_escalate(self, topic: str, details: str) -> Any:
        self.escalations.append({"topic": topic, "details": details})
        return {"recorded": True}

    def t_graphql(self, query: str, variables_json: str) -> Any:
        variables = json.loads(variables_json or "{}")
        if not isinstance(variables, dict):
            raise ValueError("variables_json must be a JSON object")
        # Any "mutation" keyword counts, not just at the start ("{ a }, mutation { ... }").
        if re.search(r"\bmutation\b", query, re.IGNORECASE):
            self._approve("graphql", f"Run GraphQL mutation:\n{query}\nvariables: {variables_json}")
        return self.shop.graphql(query, variables)
