# Firecrawl — Built into hermes-agent

**Status:** `firecrawl-py` is bundled with hermes-agent (since ~v0.9+). No extra install needed.

**What it does:**
- Full-site crawl → clean Markdown
- Handles JS-rendered pages (SPA/React/Vue)
- Structured output beyond raw HTML

**Verification:**
```python
from firecrawl import Firecrawl
# Works — library is present
```

**Limitation:** Requires a Firecrawl API key (cloud service, not free).
- Sign up: https://firecrawl.dev
- Free tier has rate limits
- Set `FIRECRAWL_API_KEY` in `.env` if you want to use it

**vs. existing tools:**
- `web_search` + `web_extract` handles most single-URL cases fine
- Firecrawl adds: recursive crawl, JS rendering, full-site export
- For our Feishu/GitHub/stock workflows, existing tools are sufficient unless a full-site scrape is needed
