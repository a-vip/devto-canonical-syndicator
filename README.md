# Dev.to Canonical Syndicator & SEO Authority Booster

Autonomous content syndicator for **[aviperera.com](https://aviperera.com)** that cross-publishes research dossiers and essays to Dev.to via the Forem/Dev.to REST API v1.

Every post published through this engine embeds an official **`canonical_url` pointing directly back to the origin publication on `aviperera.com`**. This instructs Google and Dev.to to channel **100% of the SEO backlink equity directly to your personal website**, preventing duplicate content penalties while expanding reach to thousands of tech readers.

---

## 🚀 Key Capabilities

1. **Native Canonical Attribution**:
   - Explicitly sets `canonical_url: https://aviperera.com/<post-slug>/` on every article.
   - Preserves complete SEO link equity and establishes your blog as the primary author source.
2. **HTML to Markdown Pipeline**:
   - Parses rich WordPress content into clean GitHub-flavored Markdown.
   - Formats headings, code blocks, lists, quotes, and links natively.
   - Automatically appends a canonical attribution citation at the bottom of each article.
3. **Smart Tag Sanitization**:
   - Converts categories into valid Dev.to tags (max 4, lowercase, alphanumeric, max 20 chars).
4. **Cover Image Integration**:
   - Maps featured article images to Dev.to's `main_image` header.
5. **Deduplication & Cadence**:
   - Tracks syndicated articles in `state/devto_history.json`.
   - Rates publications to 1 article per scheduled run to maximize algorithmic distribution.

---

## 🛠️ Configuration & Secrets

Add the following secret in your repository:  
**Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**:

| Secret Name | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `DEVTO_API_KEY` | **Yes** | — | Personal API key from Dev.to Settings. |
| `DEVTO_PUBLISHED` | *Optional* | `true` | Set to `true` for immediate publishing, or `false` to save as draft. |

---

## 📌 How to Obtain a Dev.to API Key

1. Log in to [dev.to](https://dev.to).
2. Go to [Settings ➔ Extensions](https://dev.to/settings/extensions).
3. Scroll down to the **DEV Community API Keys** section.
4. Enter a description (e.g. `Avi Devto Syndicator`) and click **Generate API Key**.
5. Copy the generated key and add it to your repository secrets as `DEVTO_API_KEY`.

---

## 🧪 Local Testing

```bash
python -m unittest discover tests
python devto_engine.py --dry-run
```
