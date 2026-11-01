"""Minimal Shopify Admin GraphQL client."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

import requests


class ShopifyError(RuntimeError):
    pass


class ShopifyClient:
    def __init__(
        self,
        store: str | None = None,
        token: str | None = None,
        api_version: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        store = store or os.environ.get("SHOPIFY_STORE")
        token = token or os.environ.get("SHOPIFY_ACCESS_TOKEN")
        if not store or not token:
            raise ShopifyError(
                "SHOPIFY_STORE (e.g. mein-shop.myshopify.com) and SHOPIFY_ACCESS_TOKEN must be set."
            )
        store = store.removeprefix("https://").rstrip("/")
        self.api_version = api_version or os.environ.get("SHOPIFY_API_VERSION", "2026-10")
        self.endpoint = f"https://{store}/admin/api/{self.api_version}/graphql.json"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        )

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self.session.post(
            self.endpoint,
            json={"query": query, "variables": variables or {}},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise ShopifyError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        body = resp.json()
        if body.get("errors"):
            raise ShopifyError(f"GraphQL errors: {body['errors']}")
        return body["data"]

    # ---- Staged upload (videos / images / files) -------------------------

    def staged_upload(self, path: Path) -> tuple[str, str]:
        """Upload a local file to Shopify's staging storage.

        Returns (resource_url, content_type) where content_type is one of
        VIDEO / IMAGE / FILE, ready for fileCreate.
        """
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime.startswith("video/"):
            resource, content_type = "VIDEO", "VIDEO"
        elif mime.startswith("image/"):
            resource, content_type = "IMAGE", "IMAGE"
        else:
            resource, content_type = "FILE", "FILE"

        data = self.graphql(
            """
            mutation($input: [StagedUploadInput!]!) {
              stagedUploadsCreate(input: $input) {
                stagedTargets { url resourceUrl parameters { name value } }
                userErrors { field message }
              }
            }
            """,
            {
                "input": [
                    {
                        "filename": path.name,
                        "mimeType": mime,
                        "resource": resource,
                        "fileSize": str(path.stat().st_size),
                        "httpMethod": "POST",
                    }
                ]
            },
        )["stagedUploadsCreate"]
        if data["userErrors"]:
            raise ShopifyError(f"stagedUploadsCreate: {data['userErrors']}")
        target = data["stagedTargets"][0]

        form = {p["name"]: p["value"] for p in target["parameters"]}
        with path.open("rb") as fh:
            up = requests.post(
                target["url"], data=form, files={"file": (path.name, fh, mime)}, timeout=600
            )
        if up.status_code not in (200, 201, 204):
            raise ShopifyError(f"Staged upload failed: HTTP {up.status_code}: {up.text[:500]}")
        return target["resourceUrl"], content_type
