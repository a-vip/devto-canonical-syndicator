#!/usr/bin/env python3
"""
devto_engine.py
Autonomous Dev.to Canonical Syndicator & SEO Authority Booster for aviperera.com.
Syndicates newly published research and essays to Dev.to via the Forem/Dev.to REST API v1.
Always embeds canonical_url pointing back to aviperera.com so 100% of the SEO backlink equity
flows directly to your personal domain.
"""

import os
import sys
import json
import html
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEVTO_API_ENDPOINT = "https://dev.to/api/articles"
RSS_FEED_URL = "https://aviperera.com/feed/"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "devto_history.json")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*"
}

DEFAULT_DEVTO_TAGS = ["ai", "ethics", "tech", "governance"]

class HTMLToMarkdownParser(HTMLParser):
    """Converts HTML markup from WordPress into clean GitHub-flavored Markdown for Dev.to."""
    def __init__(self):
        super().__init__()
        self.output = []
        self.href_stack = []
        self.tag_stack = []
        self.in_pre = False

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attrs_dict = dict(attrs)

        if tag in ("h1", "h2", "h3", "h4"):
            level = {"h1": "## ", "h2": "## ", "h3": "### ", "h4": "#### "}[tag]
            self.output.append(f"\n\n{level}")
        elif tag == "p":
            self.output.append("\n\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "a":
            href = attrs_dict.get("href", "")
            self.href_stack.append(href)
            self.output.append("[")
        elif tag == "blockquote":
            self.output.append("\n\n> ")
        elif tag == "li":
            self.output.append("\n- ")
        elif tag == "code":
            if not self.in_pre:
                self.output.append("`")
        elif tag == "pre":
            self.in_pre = True
            self.output.append("\n\n```text\n")
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "image")
            if src:
                self.output.append(f"\n\n![{alt}]({src})\n\n")

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

        if tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "a":
            href = self.href_stack.pop() if self.href_stack else ""
            self.output.append(f"]({href})")
        elif tag == "code":
            if not self.in_pre:
                self.output.append("`")
        elif tag == "pre":
            self.in_pre = False
            self.output.append("\n```\n\n")

    def handle_data(self, data):
        self.output.append(data)

    def get_markdown(self) -> str:
        text = "".join(self.output)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

def html_to_markdown(html_content: str) -> str:
    if not html_content:
        return ""
    parser = HTMLToMarkdownParser()
    try:
        parser.feed(html_content)
        return parser.get_markdown()
    except Exception:
        # Fallback to stripped text
        clean = re.sub(r"<[^>]+>", " ", html_content)
        return html.unescape(clean).strip()

def clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def sanitize_devto_tags(categories: List[str]) -> List[str]:
    """Sanitizes categories into valid Dev.to tags: lowercase alphanumeric, max 4 tags, max 20 chars."""
    tags = []
    for cat in categories:
        tag = re.sub(r"[^a-zA-Z0-9]", "", cat).lower()
        if tag and len(tag) <= 20 and tag not in tags:
            tags.append(tag)
            if len(tags) >= 4:
                break

    for d in DEFAULT_DEVTO_TAGS:
        if len(tags) >= 4:
            break
        if d not in tags:
            tags.append(d)
    return tags[:4]

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "syndicated" not in data:
                    data["syndicated"] = {}
                return data
        except Exception as e:
            print(f"[!] Warning reading state ({e}). Starting clean.")
    return {"syndicated": {}, "last_run": None}

def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def fetch_from_rss() -> List[Dict[str, Any]]:
    """Primary ingestion: Fetches publication content from RSS feed (WAF-immune)."""
    try:
        req = urllib.request.Request(RSS_FEED_URL, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_xml = resp.read().decode("utf-8", errors="replace")
            clean_xml = re.sub(r"</?([a-zA-Z0-9_-]+):", lambda m: "</" if m.group(0).startswith("</") else "<", raw_xml)
            root = ET.fromstring(clean_xml)
            posts = []
            for item in root.findall(".//item"):
                guid_el = item.find("guid")
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                content_el = item.find("encoded")

                guid = guid_el.text.strip() if guid_el is not None and guid_el.text else ""
                title = clean_text(title_el.text) if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                desc = desc_el.text if desc_el is not None and desc_el.text else ""
                content = content_el.text if content_el is not None and content_el.text else ""

                categories = []
                for cat in item.findall("category"):
                    if cat.text:
                        categories.append(clean_text(cat.text))

                image_url = ""
                enclosure = item.find("enclosure")
                if enclosure is not None and "image" in enclosure.get("type", ""):
                    image_url = enclosure.get("url", "").strip()

                post_id = guid if guid else link
                if title and link:
                    posts.append({
                        "id": post_id,
                        "title": title,
                        "link": link,
                        "description": desc,
                        "content_html": content if content else desc,
                        "categories": categories,
                        "image_url": image_url
                    })
            return posts
    except Exception as e:
        print(f"[!] Primary RSS discovery notice: {e}")
        return []

def build_devto_payload(post: dict, published: bool = True) -> dict:
    """Constructs Dev.to article payload with canonical link and markdown formatting."""
    title = post["title"][:120]
    canonical_url = post["link"].split("?")[0].rstrip("/") + "/"
    raw_html = post.get("content_html", "")
    markdown_body = html_to_markdown(raw_html)

    # Append canonical citation
    citation_footer = (
        f"\n\n---\n\n"
        f"*This research dossier was originally published on "
        f"[**aviperera.com**]({canonical_url}) by Avi Perera. "
        f"All canonical attribution and primary indexing belong to the origin domain.*"
    )
    full_markdown = f"{markdown_body}\n\n{citation_footer}"
    tags = sanitize_devto_tags(post.get("categories", []))

    article_payload = {
        "title": title,
        "published": published,
        "body_markdown": full_markdown,
        "canonical_url": canonical_url,
        "tags": tags,
        "description": clean_text(post.get("description", ""))[:150]
    }

    if post.get("image_url"):
        article_payload["main_image"] = post["image_url"]

    return {"article": article_payload}

def publish_to_devto(api_key: str, payload: dict) -> Tuple[bool, Optional[str], Optional[str]]:
    """Submits article to Dev.to REST API."""
    headers = {
        "api-key": api_key.strip(),
        "Content-Type": "application/json",
        "Accept": "application/vnd.forem.api-v1+json",
        "User-Agent": "AviDevtoSyndicator/1.0"
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(DEVTO_API_ENDPOINT, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            article_id = str(res_data.get("id", ""))
            article_url = res_data.get("url", "")
            print(f"[OK] Successfully syndicated to Dev.to: {article_url} (ID: {article_id})")
            return True, article_id, article_url
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[!] Dev.to API Error {e.code}: {err}")
        return False, None, err
    except Exception as e:
        print(f"[!] Dev.to Exception: {e}")
        return False, None, str(e)

def main() -> int:
    print("=== Autonomous Dev.to Canonical Syndicator & SEO Authority Booster ===")
    state = load_state()
    posts = fetch_from_rss()
    print(f"Retrieved {len(posts)} publications from aviperera.com")

    api_key = os.getenv("DEVTO_API_KEY", "").strip()
    published_mode = os.getenv("DEVTO_PUBLISHED", "true").strip().lower() != "false"

    force_dry_run = "--dry-run" in sys.argv
    has_credentials = bool(api_key)
    dry_run = force_dry_run or not has_credentials

    if dry_run:
        print("[!] Running in PREVIEW / DRY-RUN mode.")
        if not has_credentials:
            print("    Reason: Missing DEVTO_API_KEY repository secret.")

    unsyndicated = [p for p in posts if p["id"] not in state["syndicated"] and p["link"] not in state["syndicated"]]
    print(f"Publications pending Dev.to canonical syndication: {len(unsyndicated)}")

    processed_items = []

    # Syndicate 1 article per scheduled run for optimal pacing
    for post in unsyndicated[:1]:
        title = post["title"]
        pid = post["id"]
        canonical_url = post["link"]
        payload = build_devto_payload(post, published=published_mode)

        item_summary = {
            "title": title,
            "canonical_url": canonical_url,
            "tags": payload["article"]["tags"],
            "status": "Dry-Run Preview",
            "devto_url": None
        }

        if dry_run:
            print(f"\n[DRY-RUN DEV.TO PREVIEW]")
            print(f"Title: {payload['article']['title']}")
            print(f"Canonical URL: {payload['article']['canonical_url']}")
            print(f"Tags: {', '.join(payload['article']['tags'])}")
            print(f"Published: {payload['article']['published']}")
            print(f"Markdown Content length: {len(payload['article']['body_markdown'])} chars")
            processed_items.append(item_summary)
            continue

        # Live Submission
        success, devto_id, devto_url = publish_to_devto(api_key, payload)
        if success:
            state["syndicated"][pid] = {
                "title": title,
                "canonical_url": canonical_url,
                "devto_id": devto_id,
                "devto_url": devto_url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            save_state(state)
            item_summary["status"] = "Syndicated"
            item_summary["devto_url"] = devto_url
            processed_items.append(item_summary)
        else:
            item_summary["status"] = f"Failed ({devto_url})"
            processed_items.append(item_summary)

    output_step_summary(processed_items, dry_run=dry_run, has_credentials=has_credentials)
    return 0

def output_step_summary(items: list, dry_run: bool, has_credentials: bool):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("## 🚀 Dev.to Canonical Syndicator & SEO Authority Booster\n\n")
        mode_badge = "🟡 *DRY-RUN / PREVIEW*" if dry_run else "🟢 *LIVE DEV.TO SYNDICATION SUCCESS*"
        f.write(f"**Execution Mode:** {mode_badge}\n\n")
        f.write(f"- **Dev.to Credentials:** {'✅ Configured' if has_credentials else '❌ Missing DEVTO_API_KEY'}\n\n")

        if not items:
            f.write("✅ All recent publications are already syndicated to Dev.to. Zero pending items.\n")
            return

        f.write(f"### Processed Publication ({len(items)} item):\n\n")
        f.write("| Title | Canonical Origin | Dev.to URL | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for it in items:
            dev_link = f"[View on Dev.to]({it['devto_url']})" if it.get("devto_url") else "`N/A`"
            f.write(f"| {it['title']} | [{it['canonical_url']}]({it['canonical_url']}) | {dev_link} | `{it['status']}` |\n")

if __name__ == "__main__":
    sys.exit(main())
