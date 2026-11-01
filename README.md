# goldbot-medien
Gold-Agent Videos und Reels

## Shopify Agent

A terminal agent that runs your Shopify store through Claude (Claude API with
tool use, Shopify Admin GraphQL API).

**What it can do**
- Show shop info, search products, show product details
- Change title, description, tags and status (`ACTIVE`/`DRAFT`/`ARCHIVED`)
- Change variant prices
- List recent orders
- Upload videos and images from `social/` to Shopify Files and attach them to a product
- Run any GraphQL query (mutations only with approval)

Every change to the store is shown first and needs approval with `y`
(`--yes` turns this off).

**Setup**
1. In Shopify: *Settings → Apps → Develop apps* → create an app, grant the Admin API scopes
   `read_products, write_products, read_orders, write_files, read_files`, install it and
   copy the Admin API access token (`shpat_...`).
2. `pip install -r requirements.txt`
3. Copy `.env.example`, fill in the values and export them (e.g. `set -a; . ./.env; set +a`).

**Run**
```bash
python -m shopify_agent                       # interactive chat
python -m shopify_agent "Which products are still drafts?"
python -m shopify_agent --media-dir social "Upload the newest reel and attach it to the gold bar product"
```
