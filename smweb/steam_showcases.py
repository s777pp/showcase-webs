"""Structured parser for Steam profile showcases.

Steam renders every showcase as ``div.profile_customization`` with a header and
a ``profile_customization_block`` whose first child names the family
(``customtext_showcase``, ``trade_showcase``, ``screenshot_showcase`` ...).
Headers are user-editable (a Custom Info Box can be titled "ABOUT ME"), so the
family is read from those inner classes, never from the title.

Both import paths use this module: the server browser import feeds the whole
profile page, the extension sends the outerHTML of the showcase area.  The
result is plain JSON the Steam mock-up renders with Steam's own layout.
"""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
MAX_SHOWCASES = 20
MAX_RICH = 900


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict, parent: "Node | None" = None):
        self.tag = tag
        self.attrs = attrs
        self.children: list = []
        self.parent = parent

    @property
    def classes(self) -> set:
        return set((self.attrs.get("class") or "").split())

    def has(self, cls: str) -> bool:
        return cls in self.classes

    def iter(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.iter()

    def find_all(self, cls: str = "", tag: str = "") -> list:
        return [n for n in self.iter() if (not cls or n.has(cls)) and (not tag or n.tag == tag)]

    def find(self, cls: str = "", tag: str = ""):
        for n in self.iter():
            if (not cls or n.has(cls)) and (not tag or n.tag == tag):
                return n
        return None

    def elements(self) -> list:
        return [c for c in self.children if isinstance(c, Node)]

    def text(self) -> str:
        parts = []
        for child in self.children:
            parts.append(child.text() if isinstance(child, Node) else child)
        return re.sub(r"\s+", " ", " ".join(parts)).strip()


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {str(k).lower(): (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {str(k).lower(): (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        if data:
            self.cur.children.append(data)


def parse_tree(page_html: str) -> Node:
    builder = _TreeBuilder()
    try:
        builder.feed(page_html or "")
        builder.close()
    except Exception:
        pass
    return builder.root


# ------------------------------------------------------------------ helpers

def _clean_text(value: str, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()[:limit]


def _url(value: str) -> str:
    value = unescape(str(value or "")).strip()
    if value.startswith("//"):
        value = "https:" + value
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    return value[:2048] if parts.scheme in ("http", "https") and parts.hostname else ""


def _img_src(node) -> str:
    if node is None:
        return ""
    for key in ("data-src", "src"):
        src = _url(node.attrs.get(key))
        if src:
            return src
    srcset = (node.attrs.get("srcset") or "").split(",")
    return _url(srcset[0].split()[0]) if srcset and srcset[0].strip() else ""


def _is_noise(url: str) -> bool:
    low = url.lower()
    host = (urlsplit(url).hostname or "").lower()
    return host.startswith("avatars.") or any(x in low for x in (
        "/avatars/", "blank.gif", "pixel.gif", "trans.gif", "/public/images/skin", "/economy/emoticon/",
    ))


def _style_value(style: str, prop: str) -> str:
    m = re.search(r"(?:^|;)\s*" + re.escape(prop) + r"\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]{0,40}\))", style or "")
    return m.group(1) if m else ""


def _stats(block: Node) -> list:
    out = []
    for stat in block.find_all("showcase_stat"):
        if stat.find("showcase_stat") is not None:
            continue  # Steam nests <a class="showcase_stat"> inside a tooltip div
        value, label = stat.find("value"), stat.find("label")
        if value is None and label is None:
            continue
        item = {"value": _clean_text(value.text() if value else "", 40),
                "label": _clean_text(label.text() if label else "", 60)}
        tone = next((c.split("_", 1)[1] for c in stat.classes if c in ("favoritegroup_ingame", "favoritegroup_online", "favoritegroup_inchat")), "")
        if tone:
            item["tone"] = tone
        out.append(item)
    return out[:8]


def _rich(node: Node | None) -> list:
    """Flatten Steam BBCode HTML into safe segments the renderer rebuilds."""
    out: list = []
    if node is None:
        return out

    def push(seg):
        if len(out) < MAX_RICH:
            out.append(seg)

    def walk(n: Node, style: str):
        for child in n.children:
            if len(out) >= MAX_RICH:
                return
            if isinstance(child, str):
                text = re.sub(r"[ \t\r\n]+", " ", child)
                if text.strip() or (text == " " and out and out[-1].get("t") != "br"):
                    seg = {"t": "text", "v": text[:2000]}
                    if style:
                        seg["s"] = style
                    push(seg)
                continue
            tag, cls = child.tag, child.classes
            if tag == "br":
                push({"t": "br"})
            elif tag == "hr":
                push({"t": "hr"})
            elif tag == "img":
                src = _img_src(child)
                if src:
                    kind = "emoticon" if "emoticon" in cls or "/emoticon/" in src else "image"
                    push({"t": kind, "src": src, "alt": _clean_text(child.attrs.get("alt"), 80)})
            elif tag == "a":
                href = _url(child.attrs.get("href"))
                text = child.text()
                if href and text:
                    push({"t": "link", "href": href, "v": text[:300]})
                else:
                    walk(child, style)
            elif "bb_link_host" in cls:
                push({"t": "text", "v": " " + child.text()[:120], "s": "host"})
            elif tag in ("b", "strong"):
                walk(child, "b")
            elif tag in ("i", "em"):
                walk(child, "i")
            elif tag == "u":
                walk(child, "u")
            elif tag in ("s", "strike") or "bb_strike" in cls:
                walk(child, "strike")
            elif "bb_spoiler" in cls:
                walk(child, "spoiler")
            elif tag in ("h1", "h2", "h3") or cls & {"bb_h1", "bb_h2", "bb_h3"}:
                level = tag if tag in ("h1", "h2", "h3") else next(c[3:] for c in ("bb_h1", "bb_h2", "bb_h3") if c in cls)
                if out and out[-1].get("t") != "br":
                    push({"t": "br"})
                walk(child, level)
                push({"t": "br"})
            elif tag == "li":
                if out and out[-1].get("t") != "br":
                    push({"t": "br"})
                push({"t": "text", "v": "• "})
                walk(child, style)
            elif tag in ("div", "p", "blockquote", "ul", "ol") and out and out[-1].get("t") != "br":
                walk(child, "quote" if tag == "blockquote" or "bb_quote" in cls else style)
                push({"t": "br"})
            else:
                walk(child, style)

    walk(node, "")
    while out and out[-1].get("t") == "br":
        out.pop()
    return out


def _rich_plain(segments: list) -> str:
    parts = []
    for seg in segments:
        if seg.get("t") in ("text", "link"):
            parts.append(seg.get("v") or "")
        elif seg.get("t") == "br":
            parts.append("\n")
    return re.sub(r"[ \t]+", " ", "".join(parts)).strip()[:4000]


def _family(block: Node) -> tuple[str, Node]:
    for child in block.elements():
        cls = child.classes
        for name in cls:
            if name.endswith("_showcase") or name in ("recent_games",):
                return name, child
    return "", block


FAMILY_TYPES = {
    "myworkshop_showcase": "workshop",
    "workshop_showcase": "workshop_item",
    "customtext_showcase": "info",
    "trade_showcase": "trade",
    "item_showcase": "items",
    "gamecollector_showcase": "gamecollector",
    "favoriteguide_showcase": "guide",
    "myguides_showcase": "guides",
    "achievement_showcase": "achievements",
    "badge_showcase": "badges",
    "favoritegame_showcase": "favoritegame",
    "recommendation_showcase": "review",
    "favoritegroup_showcase": "group",
    "achievementscompletionist_showcase": "completionist",
    "awards_showcase": "awards",
    "recent_games": "activity",
}


def _screenshot(section: Node, customization: Node, header: str) -> dict:
    primary = section.find("screenshot_showcase_primary")
    single = bool(primary and primary.has("single"))
    is_art = customization.has("myart")
    kind = ("featured" if single else "artwork") if is_art else "screenshots"
    images = []
    if primary is not None:
        src = _img_src(primary.find(tag="img"))
        if src:
            images.append(src)
    for small in section.find_all("screenshot_showcase_smallscreenshot"):
        if small.has("screenshot_count"):
            continue
        src = _img_src(small.find(tag="img"))
        if src:
            images.append(src)
    count = section.find("screenshot_count")
    name = primary.find("screenshot_showcase_itemname") if primary is not None else None
    fav = ""
    shot_stats = []
    for stat in section.find_all("screenshot_showcase_stat"):
        fav = _clean_text(stat.text(), 20)
        icon = stat.find(tag="img")
        shot_stats.append({"value": fav, "title": _clean_text(stat.attrs.get("title"), 40),
                           "icon": _img_src(icon) if icon is not None else ""})
    return {
        "type": kind,
        "title": header or ("Featured Artwork Showcase" if kind == "featured" else "Artwork Showcase" if kind == "artwork" else "Screenshot Showcase"),
        "images": images[:5],
        "caption": _clean_text(name.text() if name else "", 200),
        "favorites": fav,
        "shot_stats": shot_stats[:4] if kind == "screenshots" else [],
        "more": _clean_text(count.text() if count else "", 20),
    }


def _item_slots(section: Node) -> list:
    slots = []
    for slot in section.find_all("item_showcase_item"):
        style = slot.attrs.get("style") or ""
        slots.append({
            "image": _img_src(slot.find(tag="img")),
            "border": _style_value(style, "border-color"),
            "bg": _style_value(style, "background-color"),
            "name": _clean_text(slot.attrs.get("title") or "", 120),
        })
    return slots[:24]


def _guide(section: Node) -> dict:
    title = section.find("showcase_item_detail_title")
    contributors = section.find("guide_showcase_contributors")
    app = section.find("workshop_showcase_app")
    desc = section.find("guide_showcase_item_description")
    stars = section.find("workshop_showcase_stars")
    app_icon = _img_src(app.find(tag="img")) if app is not None else ""
    return {
        "title": _clean_text(title.text() if title else "", 200),
        "author": _clean_text(contributors.text() if contributors else "", 120),
        "app": _clean_text(app.text() if app else "", 120),
        "app_icon": app_icon,
        "stars": _img_src(stars.find(tag="img")) if stars is not None else "",
        "ratings": _clean_text(stars.text() if stars is not None else "", 40),
        "description": _clean_text(desc.text() if desc else "", 600),
    }


def _tooltip(node) -> str:
    raw = unescape((node.attrs.get("data-tooltip-html") or node.attrs.get("data-tooltip-text") or node.attrs.get("title") or "")) if node is not None else ""
    return _clean_text(re.sub(r"<br\s*/?>", " - ", re.sub(r"<(?!br)[^>]+>", "", raw, flags=re.I), flags=re.I), 200)


def _game_info(node: Node) -> dict:
    """Recent-activity / favourite-game card: capsule, name, hours, achievements."""
    cap = node.find("game_info_cap") or node.find("favorite_game_cap")
    name = node.find("game_name") or node.find("showcase_item_detail_title")
    details = node.find("game_info_details")
    lines = []
    if details is not None:
        buf = []
        for child in details.children:
            if isinstance(child, Node) and child.tag == "br":
                lines.append(" ".join(buf)); buf = []
            else:
                buf.append(child.text() if isinstance(child, Node) else child)
        lines.append(" ".join(buf))
    summary = node.find("game_info_achievement_summary")
    count = summary.find("ellipsis") if summary is not None else None
    bar = node.find("progress_bar")
    pct = re.search(r"width:\s*([\d.]+)%", bar.attrs.get("style") or "") if bar is not None else None
    icons, more = [], ""
    for ach in node.find_all("game_info_achievement"):
        if ach.has("plus_more"):
            more = _clean_text(ach.text(), 20)
            continue
        src = _img_src(ach.find(tag="img"))
        if src:
            icons.append({"image": src, "title": _tooltip(ach)})
    files = [_clean_text(a.text(), 60) for a in node.find_all("published_file_link")]
    return {
        "image": _img_src(cap.find(tag="img")) if cap is not None else "",
        "name": _clean_text(name.text() if name else "", 160),
        "details": [x for x in (_clean_text(l, 120) for l in lines) if x][:3],
        "progress": {"text": _clean_text(count.text(), 40), "pct": min(100.0, float(pct.group(1))) if pct else 0.0} if count is not None else None,
        "achievements": icons[:8], "more": more, "files": files[:6],
    }


def _type_from_title(title: str) -> str:
    """Last resort for markup without a known family class (old snapshots, tests)."""
    low = title.lower()
    for words, kind in ((("workshop", "мастерск"), "workshop"), (("guide", "руковод"), "guide"),
                        (("featured artwork", "избранная иллюстрац"), "featured"),
                        (("artwork", "иллюстра"), "artwork"), (("screenshot", "скриншот"), "screenshots")):
        if any(w in low for w in words):
            return kind
    return "unknown"


def parse_customization(customization: Node) -> dict | None:
    header_node = customization.find("profile_customization_header")
    header = _clean_text(header_node.text() if header_node else "", 120)
    block = customization.find("profile_customization_block") or customization
    family, section = _family(block)
    links = []
    for a in customization.find_all(tag="a"):
        href = _url(a.attrs.get("href"))
        if href and ("sharedfiles" in href or "filedetails" in href) and href not in links:
            links.append(href)
    base = {"title": header, "links": links[:30], "stats": _stats(block), "text": ""}

    if family == "screenshot_showcase":
        base.update(_screenshot(section, customization, header))
        return base
    kind = FAMILY_TYPES.get(family, "")
    if kind == "activity" or customization.find("recent_games") is not None:
        head = customization.find("profile_recentgame_header")
        playtime = customization.find("recentgame_recentplaytime")
        title_node = head.elements()[0] if head is not None and head.elements() else None
        return {"type": "activity", "title": _clean_text(title_node.text() if title_node else "Recent Activity", 80),
                "playtime": _clean_text(playtime.text() if playtime else "", 60),
                "games": [_game_info(g) for g in customization.find_all("recent_game")][:3],
                "quicklinks": [_clean_text(a.text(), 40) for q in customization.find_all("recentgame_quicklinks")
                               if not q.has("recentgame_recentplaytime") for a in q.find_all(tag="a")][:4],
                "images": [], "links": [], "stats": [], "text": ""}
    notes = section.find("showcase_notes")
    if kind == "info":
        rich = _rich(notes or section)
        base.update({"type": "info", "title": header or "Custom Info Box", "rich": rich,
                     "text": _rich_plain(rich), "images": []})
        return base
    if kind in ("trade", "items"):
        rich = _rich(notes)
        slots = _item_slots(section)
        base.update({"type": kind, "title": header or ("Items Up For Trade" if kind == "trade" else "Item Showcase"),
                     "slots": slots, "images": [s["image"] for s in slots if s["image"]],
                     "rich": rich, "text": _rich_plain(rich)})
        return base
    if kind == "workshop":
        wheader = customization.find("myworkshop_showcase_header")
        name = wheader.find("myworkshop_playerName") if wheader is not None else None
        avatar = _img_src(wheader.find(tag="img")) if wheader is not None else ""
        images = [_img_src(img) for img in section.find_all("workshop_showcase_item_image")]
        base.update({"type": "workshop", "title": header or "Workshop Showcase",
                     "workshopName": _clean_text(name.text() if name else "", 120),
                     "avatar": avatar, "images": [u for u in images if u][:15]})
        return base
    if kind in ("guide", "workshop_item"):
        img = section.find("workshop_showcase_item_image")
        base.update({"type": "guide" if kind == "guide" else "workshop_item",
                     "title": header or ("Favorite Guide" if kind == "guide" else "Favorite Workshop Item"),
                     "images": [u for u in [_img_src(img)] if u], "guide": _guide(section)})
        base["text"] = base["guide"]["description"]
        return base
    if kind == "gamecollector":
        label = section.find("showcase_bodylabel")
        games = []
        for slot in section.find_all("showcase_gamecollector_game"):
            src = _img_src(slot.find(tag="img"))
            if src:
                games.append(src)
        base.update({"type": "gamecollector", "title": header or "Game Collector",
                     "label": _clean_text(label.text() if label else "", 80), "images": games[:12]})
        return base

    if kind in ("achievements", "badges"):
        cells = section.find_all("showcase_achievement") if kind == "achievements" else section.find_all("showcase_badge")
        icons = []
        for cell in cells:
            if cell.has("openslot"):
                continue
            if cell.has("plus_more"):
                base["more"] = _clean_text(cell.text(), 20)
                continue
            src = _img_src(cell.find(tag="img"))
            if src:
                icons.append({"image": src, "title": _tooltip(cell)})
        base.update({"type": kind, "title": header or ("Achievement Showcase" if kind == "achievements" else "Badge Collector"),
                     "icons": icons[:40], "images": [i["image"] for i in icons][:40]})
        return base
    if kind == "favoritegame":
        game = _game_info(section)
        base.update({"type": "favoritegame", "title": header or "Favorite Game", "game": game,
                     "images": [game["image"]] if game["image"] else []})
        return base
    if kind == "group":
        name = section.find("favoritegroup_name")
        namerow = section.find("favoritegroup_namerow")
        desc = section.find("favoritegroup_description")
        avatar = section.find("favoritegroup_avatar")
        full = _clean_text(namerow.text() if namerow else "", 200)
        gname = _clean_text(name.text() if name else "", 120)
        base.update({"type": "group", "title": header or "Favorite Group", "group": {
            "name": gname, "kind": _clean_text(full[len(gname):].lstrip(" -"), 60) if full.startswith(gname) else "",
            "avatar": _img_src(avatar.find(tag="img")) if avatar is not None else "",
            "description": _clean_text(desc.text() if desc else "", 400)}, "images": []})
        return base

    # Achievements, badges, favourite game/group, reviews, completionist,
    # awards and anything Valve adds later: keep stats, body label, slot
    # images and notes so the renderer can draw Steam's generic layout.
    label = section.find("showcase_bodylabel")
    images = []
    for img in section.find_all(tag="img"):
        src = _img_src(img)
        if src and not _is_noise(src) and src not in images:
            images.append(src)
    rich = _rich(notes)
    base.update({"type": kind or _type_from_title(header), "title": header or "Steam Showcase",
                 "label": _clean_text(label.text() if label else "", 80),
                 "images": images[:16], "rich": rich, "text": _rich_plain(rich) or _clean_text(section.text(), 600)})
    if kind in ("favoritegame", "group", "review", "workshop_item"):
        name = section.find("showcase_item_detail_title") or section.find("favoritegroup_name")
        base["caption"] = _clean_text(name.text() if name else "", 200)
    return base


def parse_showcases(page_html: str) -> list:
    return parse_showcases_tree(parse_tree(page_html))


def parse_showcases_tree(root: Node) -> list:
    out = []
    for node in root.find_all("profile_customization"):
        # Skip nested matches (a customization never contains another one).
        parent, nested = node.parent, False
        while parent is not None:
            if isinstance(parent, Node) and parent.has("profile_customization"):
                nested = True
                break
            parent = parent.parent
        if nested:
            continue
        try:
            item = parse_customization(node)
        except Exception:
            item = None
        if item:
            item["images"] = [u for u in item.get("images") or [] if u and not _is_noise(u)] if item["type"] not in ("info",) else []
            out.append(item)
        if len(out) >= MAX_SHOWCASES:
            break
    return out


def sanitize(showcases: list, url_ok) -> list:
    """Bound untrusted showcase JSON and drop URLs ``url_ok`` rejects."""
    def u(value):
        return url_ok(value) if isinstance(value, str) and value else ""

    def t(value, limit):
        return _clean_text(value, limit) if value is not None else ""

    out = []
    for sc in (showcases if isinstance(showcases, list) else [])[:MAX_SHOWCASES]:
        if not isinstance(sc, dict):
            continue
        item = {
            "type": re.sub(r"[^a-z_]", "", str(sc.get("type") or "unknown").lower())[:40] or "unknown",
            "title": t(sc.get("title"), 120),
            "images": [x for x in (u(v) for v in (sc.get("images") or [])[:40]) if x],
            "links": [x for x in (u(v) for v in (sc.get("links") or [])[:30]) if x],
            "text": str(sc.get("text") or "")[:4000],
            "stats": [dict({"value": t(s.get("value"), 40), "label": t(s.get("label"), 60)},
                           **({"tone": s["tone"]} if s.get("tone") in ("ingame", "online", "inchat") else {}))
                      for s in (sc.get("stats") or [])[:8] if isinstance(s, dict)],
        }
        if isinstance(sc.get("icons"), list):
            item["icons"] = [{"image": u(i.get("image")), "title": t(i.get("title"), 200)}
                             for i in sc["icons"][:40] if isinstance(i, dict) and u(i.get("image"))]
        if isinstance(sc.get("shot_stats"), list):
            item["shot_stats"] = [{"value": t(i.get("value"), 20), "title": t(i.get("title"), 40), "icon": u(i.get("icon"))}
                                  for i in sc["shot_stats"][:4] if isinstance(i, dict)]
        if isinstance(sc.get("group"), dict):
            g = sc["group"]
            item["group"] = {"name": t(g.get("name"), 120), "kind": t(g.get("kind"), 60),
                             "avatar": u(g.get("avatar")), "description": t(g.get("description"), 400)}

        def game(g):
            g = g if isinstance(g, dict) else {}
            prog = g.get("progress") if isinstance(g.get("progress"), dict) else None
            try:
                pct = max(0.0, min(100.0, float(prog.get("pct")))) if prog else 0.0
            except (TypeError, ValueError):
                pct = 0.0
            return {"image": u(g.get("image")), "name": t(g.get("name"), 160),
                    "details": [t(d, 120) for d in (g.get("details") or [])[:3]],
                    "progress": {"text": t(prog.get("text"), 40), "pct": pct} if prog else None,
                    "achievements": [{"image": u(a.get("image")), "title": t(a.get("title"), 200)}
                                     for a in (g.get("achievements") or [])[:8] if isinstance(a, dict) and u(a.get("image"))],
                    "more": t(g.get("more"), 20), "files": [t(f, 60) for f in (g.get("files") or [])[:6]]}
        if isinstance(sc.get("game"), dict):
            item["game"] = game(sc["game"])
        if isinstance(sc.get("games"), list):
            item["games"] = [game(g) for g in sc["games"][:3]]
        if isinstance(sc.get("quicklinks"), list):
            item["quicklinks"] = [t(q, 40) for q in sc["quicklinks"][:4]]
        for key, limit in (("caption", 200), ("favorites", 20), ("more", 20), ("label", 80), ("workshopName", 120), ("playtime", 60)):
            if sc.get(key):
                item[key] = t(sc.get(key), limit)
        if sc.get("avatar"):
            item["avatar"] = u(sc.get("avatar"))
        if isinstance(sc.get("slots"), list):
            color = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([0-9.,\s%]{1,40}\))$")
            item["slots"] = [{
                "image": u(s.get("image")),
                "border": s.get("border") if color.match(str(s.get("border") or "")) else "",
                "bg": s.get("bg") if color.match(str(s.get("bg") or "")) else "",
                "name": t(s.get("name"), 120),
            } for s in sc["slots"][:24] if isinstance(s, dict)]
        if isinstance(sc.get("guide"), dict):
            g = sc["guide"]
            item["guide"] = {"title": t(g.get("title"), 200), "author": t(g.get("author"), 120),
                             "app": t(g.get("app"), 120), "app_icon": u(g.get("app_icon")),
                             "stars": u(g.get("stars")), "ratings": t(g.get("ratings"), 40), "description": t(g.get("description"), 600)}
        if isinstance(sc.get("rich"), list):
            rich = []
            for seg in sc["rich"][:MAX_RICH]:
                if not isinstance(seg, dict):
                    continue
                kind = seg.get("t")
                if kind in ("br", "hr"):
                    rich.append({"t": kind})
                elif kind == "text":
                    style = seg.get("s") if seg.get("s") in ("b", "i", "u", "strike", "spoiler", "h1", "h2", "h3", "quote", "host") else ""
                    rich.append({"t": "text", "v": str(seg.get("v") or "")[:2000], **({"s": style} if style else {})})
                elif kind in ("emoticon", "image") and u(seg.get("src")):
                    rich.append({"t": kind, "src": u(seg.get("src")), "alt": t(seg.get("alt"), 80)})
                elif kind == "link" and u(seg.get("href")):
                    rich.append({"t": "link", "href": u(seg.get("href")), "v": str(seg.get("v") or "")[:300]})
            item["rich"] = rich
        out.append(item)
    return out


# ---------------------------------------------------------- whole profile

def _count(node) -> int:
    total = node.find("profile_count_link_total") if node is not None else None
    digits = re.sub(r"[^\d]", "", total.text() if total is not None else "")
    return int(digits) if digits else 0


def _persona(node) -> str:
    classes = node.classes if node is not None else set()
    return next((c for c in ("in-game", "online", "offline") if c in classes), "offline")


def _sidebar(root: Node) -> dict:
    col = root.find("profile_rightcol")
    if col is None:
        return {}
    out: dict = {}
    status = col.find("profile_in_game_header")
    game = col.find("profile_in_game_name")
    out["status"] = _clean_text(status.text() if status else "", 80)
    out["status_game"] = _clean_text(game.text() if game else "", 120)
    for key, cls in (("awards", "profile_awards"), ("badges", "profile_badges")):
        box = col.find(cls)
        if box is None:
            continue
        items = []
        for badge in box.find_all("profile_badges_badge"):
            src = _img_src(badge.find(tag="img"))
            if src:
                items.append({"image": src, "title": _tooltip(badge)})
        out[key] = {"count": _count(box), "items": items[:8]}
    counts = []
    links = col.find("profile_item_links")
    if links is not None:
        for link in links.find_all("profile_count_link"):
            label = link.find("count_link_label")
            total = link.find("profile_count_link_total")
            if label is not None:
                counts.append({"label": _clean_text(label.text(), 40),
                               "value": _clean_text(total.text() if total else "", 20)})
    out["counts"] = counts[:12]
    groups = col.find("profile_group_links")
    if groups is not None:
        items = []
        for g in groups.find_all("profile_group"):
            name = next((a for a in g.find_all(tag="a") if a.has("whiteLink")), None)
            members = g.find("profile_group_membercount")
            items.append({"name": _clean_text(name.text() if name else "", 120),
                          "avatar": _img_src(g.find(tag="img")),
                          "members": _clean_text(members.text() if members else "", 40)})
        out["groups"] = {"count": _count(groups), "items": items[:6]}
    friends = col.find("profile_friend_links")
    if friends is not None:
        items = []
        for f in friends.find_all("friendBlock"):
            content = f.find("friendBlockContent")
            small = content.find("friendSmallText") if content is not None else None
            name_parts = [c for c in (content.children if content is not None else []) if isinstance(c, str)]
            level = f.find("friendPlayerLevelNum")
            avatar = f.find("playerAvatar")
            items.append({"name": _clean_text(" ".join(name_parts), 80),
                          "avatar": _img_src(avatar.find(tag="img")) if avatar is not None else "",
                          "level": _clean_text(level.text() if level else "", 8),
                          "status": _clean_text(small.text() if small else "", 60),
                          "persona": _persona(f)})
        out["friends"] = {"count": _count(friends), "items": items[:10]}
    return out


def _favorite_badge(root: Node) -> dict:
    fav = root.find("favorite_badge")
    if fav is None:
        return {}
    name, xp = fav.find("name"), fav.find("xp")
    return {"image": _img_src(fav.find(tag="img")), "title": _clean_text(name.text() if name else "", 120),
            "xp": _clean_text(xp.text() if xp else "", 40)}


def _comments(root: Node) -> dict:
    area = root.find("commentthread_area")
    if area is None:
        return {}
    total_node = next((n for n in area.iter() if (n.attrs.get("id") or "").endswith("_totalcount")), None)
    items = []
    for c in area.find_all("commentthread_comment"):
        author = c.find("commentthread_author_link")
        avatar = c.find("commentthread_comment_avatar")
        stamp = next((x for x in c.find_all("commentthread_comment_timestamp") if x.text()), None)
        text = c.find("commentthread_comment_text")
        items.append({"author": _clean_text(author.text() if author else "", 80),
                      "avatar": _img_src(avatar.find(tag="img")) if avatar is not None else "",
                      "persona": _persona(avatar),
                      "time": _clean_text(stamp.text() if stamp else "", 60),
                      "rich": _rich(text)[:200]})
    total = re.sub(r"[^\d]", "", total_node.text()) if total_node is not None else ""
    return {"total": int(total) if total else len(items), "items": items[:10]}


def parse_profile_page(page_html: str) -> dict:
    """Showcases plus the right column, favourite badge and first comment page."""
    root = parse_tree(page_html)
    return {
        "showcases": parse_showcases_tree(root),
        "sidebar": _sidebar(root),
        "favorite_badge": _favorite_badge(root),
        "comments": _comments(root),
    }


def _int(value) -> int:
    try:
        return max(0, min(int(value or 0), 100_000_000))
    except (TypeError, ValueError):
        return 0


def sanitize_extras(extras: dict, url_ok) -> dict:
    """Bound the sidebar/comments part of parse_profile_page for untrusted input."""
    def u(value):
        return url_ok(value) if isinstance(value, str) and value else ""

    def t(value, limit):
        return _clean_text(value, limit) if value is not None else ""

    extras = extras if isinstance(extras, dict) else {}
    side = extras.get("sidebar") if isinstance(extras.get("sidebar"), dict) else {}
    out_side: dict = {"status": t(side.get("status"), 80), "status_game": t(side.get("status_game"), 120)}
    for key in ("awards", "badges"):
        box = side.get(key) if isinstance(side.get(key), dict) else None
        if box:
            out_side[key] = {"count": _int(box.get("count")),
                             "items": [{"image": u(i.get("image")), "title": t(i.get("title"), 200)}
                                       for i in (box.get("items") or [])[:8] if isinstance(i, dict) and u(i.get("image"))]}
    out_side["counts"] = [{"label": t(c.get("label"), 40), "value": t(c.get("value"), 20)}
                          for c in (side.get("counts") or [])[:12] if isinstance(c, dict)]
    for key, fields in (("groups", ("name", "members")), ("friends", ("name", "level", "status", "persona"))):
        box = side.get(key) if isinstance(side.get(key), dict) else None
        if box:
            out_side[key] = {"count": _int(box.get("count")),
                             "items": [dict({f: t(i.get(f), 120) for f in fields}, avatar=u(i.get("avatar")))
                                       for i in (box.get("items") or [])[:10] if isinstance(i, dict)]}
    fav = extras.get("favorite_badge") if isinstance(extras.get("favorite_badge"), dict) else {}
    com = extras.get("comments") if isinstance(extras.get("comments"), dict) else {}
    comments = {"total": _int(com.get("total")), "items": []}
    for c in (com.get("items") or [])[:10]:
        if isinstance(c, dict):
            rich = sanitize([{"type": "info", "rich": c.get("rich") or []}], url_ok)[0]["rich"]
            comments["items"].append({"author": t(c.get("author"), 80), "avatar": u(c.get("avatar")),
                                      "persona": t(c.get("persona"), 12), "time": t(c.get("time"), 60),
                                      "rich": rich[:200]})
    return {"sidebar": out_side,
            "favorite_badge": {"image": u(fav.get("image")), "title": t(fav.get("title"), 120),
                               "xp": t(fav.get("xp"), 40)} if fav else {},
            "comments": comments}
