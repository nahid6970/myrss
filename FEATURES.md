# myRSS — Feature Plan

## A. Feed Organization
All three are additive and will be implemented together:
- [x] Flat list of all feeds (base sidebar view)
- [x] Folder/category grouping (collapsible headers, e.g. "Tech", "News")
- [x] Tags on feeds (multiple tags per feed for cross-cutting filtering)

## B. Article Filtering
- [x] Both search + read/unread state (keyword search bar + unread badge counts)

## C. Notifications
- [x] Desktop toast notification on new items

## D. Content Display
- [x] Split pane — list on left, content on right

## E. Export / Sharing
- [x] Copy article link to clipboard
- [x] Open in browser

## F. Extras
- [x] Favicon fetching for feeds
- [x] Article star/bookmark system
- [x] Article count per feed in sidebar

---

## Data Storage

All feeds and articles are persisted in a local `feeds.json` file in the project directory.

### JSON Structure
```json
{
  "feeds": [
    {
      "url": "https://...",
      "title": "The Verge",
      "category": "Tech",
      "tags": ["tech", "AI"],
      "favicon": "base64_or_path",
      "last_fetched": "2026-10-15T10:00:00",
      "fetch_error": null,
      "articles": [
        {
          "id": "guid_or_hash",
          "title": "...",
          "link": "...",
          "published": "2026-10-15T09:00:00",
          "read": false,
          "starred": false,
          "summary": "..."
        }
      ]
    }
  ]
}
```

### Article Retention
- Articles **accumulate over time** (not capped per feed).
- A configurable **retention period** (default: 7 days) auto-purges articles older than N days on startup.
- Starred articles are **exempt from auto-purge** regardless of age.
- Retention period is configurable via the Settings dialog.

---

## Settings Dialog
- Retention period (days) — default: 7
- Auto-refresh interval (minutes) — default: 30
- (extensible for future settings)
