"""DeviantArt publishing options: description HTML, tags and publish settings.

The browser builds the description (bold, links, headings, separators, emoji) and the
publish options; everything is validated here before it goes to DeviantArt's
``stash/submit`` and ``stash/publish`` endpoints.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

TITLE_MAX = 50
DESCRIPTION_MAX = 20000
TAG_MAX = 30
TAG_LENGTH = 50
MATURE_LEVELS = {"strict", "moderate"}
MATURE_CLASSES = {"nudity", "sexual", "gore", "language", "ideology"}
UUID = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")

# DeviantArt's description accepts a small HTML subset; everything else is dropped.
ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "s", "strike", "a", "br", "p", "h1", "h2", "h3", "h4",
                "ul", "ol", "li", "sub", "sup", "small", "code", "blockquote", "hr"}
VOID_TAGS = {"br", "hr"}
RENAME = {"div": "p"}
PLACEHOLDER = re.compile(r"^\{[a-z_]{2,20}\}$")
OUTGOING = re.compile(r"^https?://(?:www\.)?deviantart\.com/users/outgoing\?(.+)$", re.I)


def unwrap_link(href: str) -> str:
    """DeviantArt wraps external links in /users/outgoing?<url>; keep the real target."""
    match = OUTGOING.match(href or "")
    return unquote(match.group(1)) if match else (href or "")


def safe_href(href: str) -> str:
    href = unwrap_link(str(href or "").strip())
    parsed = urlparse(href)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return href


class _Cleaner(HTMLParser):
    def __init__(self, placeholders: bool = False):
        super().__init__(convert_charrefs=True)
        self.placeholders = placeholders
        self.out: list[str] = []
        self.stack: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = RENAME.get(tag, tag)
        if tag in ("script", "style", "iframe", "object", "template"):
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            raw_href = str(dict(attrs).get("href") or "").strip()
            # Presets may keep {link}; the browser fills it in before uploading.
            href = raw_href if self.placeholders and PLACEHOLDER.match(raw_href) else safe_href(raw_href)
            if not href:
                self.stack.append("")  # keep text, drop the link
                return
            self.out.append(f'<a href="{html.escape(href, quote=True)}">')
            self.stack.append("a")
            return
        if tag in VOID_TAGS:
            self.out.append(f"<{tag}>")
            return
        self.out.append(f"<{tag}>")
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        tag = RENAME.get(tag, tag)
        if not self.skip and tag in VOID_TAGS:
            self.out.append(f"<{tag}>")

    def handle_endtag(self, tag):
        tag = RENAME.get(tag, tag)
        if tag in ("script", "style", "iframe", "object", "template"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID_TAGS or tag not in ALLOWED_TAGS:
            return
        # close up to the matching open tag (browsers' contenteditable output is not always tidy)
        if tag == "a" and "" in self.stack and "a" not in self.stack:
            self.stack.remove("")
            return
        if tag in self.stack:
            while self.stack:
                top = self.stack.pop()
                if top:
                    self.out.append(f"</{top}>")
                if top == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            top = self.stack.pop()
            if top:
                self.out.append(f"</{top}>")
        return "".join(self.out)


def clean_description(raw: str, placeholders: bool = False) -> str:
    """Whitelisted HTML for ``artist_comments``; plain text keeps its line breaks."""
    raw = str(raw or "")[:DESCRIPTION_MAX * 2]
    if not re.search(r"</?(?:" + "|".join(sorted(ALLOWED_TAGS | set(RENAME))) + r")\b", raw, re.I):
        raw = html.escape(raw, quote=False).replace("\r\n", "\n").replace("\n", "<br>")
    cleaner = _Cleaner(placeholders)
    cleaner.feed(raw)
    cleaner.close()
    text = cleaner.result()
    text = re.sub(r"(<br>\s*){3,}", "<br><br>", text).strip()
    return text[:DESCRIPTION_MAX]



# DeviantArt keeps artist comments in its classic markup: plain text where a new line is a
# line break, with only inline tags inside (b, i, u, s, a href, sub, sup, small, code).
# Block HTML (p, h4, lists) without new lines made DeviantArt drop every tag and glue the
# text into one line (owner report 2026-10-01), so the editor's HTML is converted here.
INLINE_RENAME = {"strong": "b", "em": "i", "strike": "s"}
INLINE_KEEP = {"b", "i", "u", "s", "sub", "sup", "small", "code"}
BLOCKS = {"p", "h1", "h2", "h3", "h4", "li", "blockquote", "ul", "ol"}


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.block_text = False
        self.links: list[tuple[str, int]] = []  # (href, position of the link text)

    def _newline(self):
        self.out.append("\n")
        self.block_text = False

    def handle_starttag(self, tag, attrs):
        tag = INLINE_RENAME.get(tag, tag)
        if tag in ("br", "hr"):
            self._newline()
            return
        if tag in BLOCKS:
            if self.block_text:
                self._newline()
            if tag == "li":
                self.out.append("• ")
            if tag in ("h1", "h2", "h3", "h4"):
                self.out.append("<b>")
                self.open.append("b")
            return
        if tag == "a":
            # DeviantArt drops <a> from artist comments sent through the API (owner check
            # 2026-10-01), so the address goes right after the link text, where DeviantArt
            # turns it into a clickable link itself.
            self.links.append((safe_href(dict(attrs).get("href") or ""), len(self.out)))
            return
        if tag not in INLINE_KEEP:
            return
        self.out.append(f"<{tag}>")
        self.open.append(tag)

    def handle_endtag(self, tag):
        tag = INLINE_RENAME.get(tag, tag)
        if tag in BLOCKS:
            if tag in ("h1", "h2", "h3", "h4") and "b" in self.open:
                self._close("b")
            if self.block_text or tag in ("p", "li", "h1", "h2", "h3", "h4", "blockquote"):
                self._newline()
            return
        if tag == "a":
            if self.links:
                href, start = self.links.pop()
                label = re.sub(r"<[^>]+>", "", "".join(self.out[start:])).strip()
                if href and html.unescape(label) != href:
                    self.out.append(" " + html.escape(href, quote=False))
                elif href and not label:
                    self.out.append(html.escape(href, quote=False))
            return
        if tag in INLINE_KEEP:
            self._close(tag)

    def _close(self, tag):
        if tag in self.open:
            while self.open:
                top = self.open.pop()
                if top:
                    self.out.append(f"</{top}>")
                if top == tag:
                    break

    def handle_data(self, data):
        if data.strip() or self.block_text:
            self.out.append(html.escape(data, quote=False))
            if data.strip():
                self.block_text = True

    def result(self) -> str:
        while self.open:
            top = self.open.pop()
            if top:
                self.out.append(f"</{top}>")
        text = "".join(self.out)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip("\n")


def to_da_markup(clean_html: str) -> str:
    """Cleaned editor HTML -> DeviantArt's classic artist-comments markup."""
    parser = _Markup()
    parser.feed(clean_html or "")
    parser.close()
    return parser.result()[:DESCRIPTION_MAX]


def clean_tags(raw) -> list[str]:
    """Letters, numbers and underscore only (DeviantArt's rule), lower case, no duplicates."""
    if isinstance(raw, str):
        raw = re.split(r"[,\s#]+", raw)
    out: list[str] = []
    for item in raw or []:
        tag = re.sub(r"[^\w]", "", str(item or ""), flags=re.UNICODE).lower()[:TAG_LENGTH]
        if tag and tag not in out:
            out.append(tag)
        if len(out) >= TAG_MAX:
            break
    return out


def clean_title(raw: str, fallback: str = "Untitled") -> str:
    title = re.sub(r"\s+", " ", str(raw or "")).strip()[:TITLE_MAX].strip()
    return title or fallback[:TITLE_MAX]


def _flag(value) -> bool:
    return value in (True, 1, "1", "true", "True", "on", "yes")


def clean_settings(raw: dict | None, placeholders: bool = False) -> dict:
    """Publish options from the browser, clamped to what DeviantArt accepts."""
    raw = raw if isinstance(raw, dict) else {}
    mature = _flag(raw.get("is_mature"))
    level = str(raw.get("mature_level") or "moderate")
    classes = [c for c in (raw.get("mature_classification") or []) if c in MATURE_CLASSES]
    try:
        resolution = max(0, min(8, int(raw.get("display_resolution") or 0)))
    except (TypeError, ValueError):
        resolution = 0
    galleries = [g for g in (raw.get("galleryids") or []) if isinstance(g, str) and UUID.match(g)][:10]
    return {
        "mode": "publish" if raw.get("mode") == "publish" else "stash",
        "description": clean_description(raw.get("description") or "", placeholders),
        "tags": clean_tags(raw.get("tags") or []),
        "is_mature": mature,
        "mature_level": level if level in MATURE_LEVELS else "moderate",
        "mature_classification": classes if mature else [],
        "is_ai_generated": _flag(raw.get("is_ai_generated")),
        "noai": _flag(raw.get("noai")),
        "galleryids": galleries,
        "display_resolution": resolution,
        "add_watermark": _flag(raw.get("add_watermark")) and resolution > 0,
        "allow_free_download": _flag(raw.get("allow_free_download")),
        "allow_comments": raw.get("allow_comments") is None or _flag(raw.get("allow_comments")),
        "feature": raw.get("feature") is None or _flag(raw.get("feature")),
    }


def _bool(value: bool) -> str:
    return "true" if value else "false"


def submit_fields(title: str, settings: dict) -> list[tuple[str, str]]:
    """Form fields for stash/submit (lists are sent as name[] entries)."""
    fields = [("title", title), ("artist_comments", to_da_markup(settings["description"])),
              ("is_ai_generated", _bool(settings["is_ai_generated"])), ("noai", _bool(settings["noai"]))]
    fields += [("tags[]", tag) for tag in settings["tags"]]
    return fields


def publish_fields(itemid, settings: dict) -> list[tuple[str, str]]:
    fields = [
        ("itemid", str(itemid)),
        ("is_mature", _bool(settings["is_mature"])),
        ("feature", _bool(settings["feature"])),
        ("allow_comments", _bool(settings["allow_comments"])),
        ("allow_free_download", _bool(settings["allow_free_download"])),
        ("is_ai_generated", _bool(settings["is_ai_generated"])),
        ("noai", _bool(settings["noai"])),
        ("agree_submission", "true"),
        ("agree_tos", "true"),
    ]
    if settings["is_mature"]:
        fields.append(("mature_level", settings["mature_level"]))
        fields += [("mature_classification[]", c) for c in settings["mature_classification"]]
    if settings["display_resolution"]:
        fields.append(("display_resolution", str(settings["display_resolution"])))
        fields.append(("add_watermark", _bool(settings["add_watermark"])))
    fields += [("galleryids[]", g) for g in settings["galleryids"]]
    fields += [("tags[]", tag) for tag in settings["tags"]]
    return fields
