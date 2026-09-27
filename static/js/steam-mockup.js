/**
 * Steam-like profile mockup renderer (DOM + steam_profile.css classes).
 * Shared by /profile (editor) and /profile/{user} (public).
 */
(function (global) {
  var UI = {
    en: {steam_user:'Steam User',replace_media:'Replace media',replace:'Replace',upload:'＋ Upload',featured:'Featured Artwork Showcase',artwork:'Artwork Showcase',workshop:'Workshop Showcase',guide:'Favorite Guide',info:'Info',favorite_art:'Favorite Artwork',showcase:'Showcase',submissions:'Submissions',followers:'Followers',created_by:'Created by — ',ratings:' ratings',level:'Level',favorite_badge:'Favorite Badge',offline:'Currently Offline',online:'Currently Online',ingame:'Currently In-Game',awards:'Profile Awards',badges:'Badges',groups:'Groups',no_groups:'No groups',games:'Games',inventory:'Inventory',screenshots:'Screenshots',videos:'Videos',workshop_items:'Workshop Items',reviews:'Reviews',guides:'Guides',artwork_stat:'Artwork',friends:'Friends',comments:'Comments',view_all:'View all {n} comments',ach_progress:'Achievement Progress',view:'View'},
    ru: {steam_user:'Пользователь Steam',replace_media:'Заменить медиа',replace:'Заменить',upload:'＋ Загрузить',featured:'Избранная иллюстрация',artwork:'Витрина иллюстраций',workshop:'Витрина Workshop',guide:'Избранное руководство',info:'Информация',favorite_art:'Избранная иллюстрация',showcase:'Витрина',submissions:'Работы',followers:'Подписчики',created_by:'Автор — ',ratings:' оценок',level:'Уровень',favorite_badge:'Избранный значок',offline:'Не в сети',online:'В сети',ingame:'В игре',awards:'Награды профиля',badges:'Значки',groups:'Группы',no_groups:'Нет групп',games:'Игры',inventory:'Инвентарь',screenshots:'Скриншоты',videos:'Видео',workshop_items:'Работы Workshop',reviews:'Обзоры',guides:'Руководства',artwork_stat:'Иллюстрации',friends:'Друзья',comments:'Комментарии',view_all:'Все комментарии ({n})',ach_progress:'Прогресс достижений',view:'Смотреть'}
  };
  if (global.SMLang && SMLang.extend) SMLang.extend(UI);
  function tr(k) { var l='en'; try{l=global.SMLang&&SMLang.get?SMLang.get():'en'}catch(e){} return (UI[l]||UI.en)[k] || UI.en[k] || k; }
  function localizedKnown(s) {
    var map={'Steam User':'steam_user','Пользователь Steam':'steam_user','Featured Artwork Showcase':'featured','Artwork Showcase':'artwork','Workshop Showcase':'workshop','Favorite Guide':'guide','Info':'info','Favorite Artwork':'favorite_art','Favorite Badge':'favorite_badge','Currently Offline':'offline','Currently Online':'online','Currently In-Game':'ingame'};
    return map[String(s||'')] ? tr(map[String(s||'')]) : s;
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }
  function px(url) {
    if (!url) return "";
    if (/^(blob:|data:|\/)/i.test(url)) return url;
    return "/api/steam/proxy-image?url=" + encodeURIComponent(url);
  }
  function directMedia(url) {
    /* Video needs no canvas access, so Steam CDN files can load directly. */
    return /^https:\/\/[a-z0-9.-]*steamstatic\.com\//i.test(String(url || "")) ? url : px(url);
  }
  function isVideoUrl(url) {
    return /\.(webm|mp4)(\?|$)/i.test(String(url || ""));
  }
  function fullBackgroundUrl(url) {
    /* Steam Market returns a square 360px preview.  It contains the artwork
       lower in the canvas, which made the public profile look as if its
       background started halfway down the page.  Removing the resize suffix
       requests the original profile-background asset. */
    return String(url || "").replace(/\/(?:\d+f?x\d+f?|\d+x\d+)(?:\?.*)?$/i, "");
  }
  function mediaTag(url, cls, alt) {
    if (!url) {
      return '<div class="' + esc(cls) + ' sm-slot-empty" data-empty="1"></div>';
    }
    var src = px(url);
    if (isVideoUrl(url)) {
      return (
        '<video class="' +
        esc(cls) +
        '" src="' +
        esc(src) +
        '" autoplay muted loop playsinline preload="auto"></video>'
      );
    }
    return (
      '<img class="' +
      esc(cls) +
      '" src="' +
      esc(src) +
      '" alt="' +
      esc(alt || "") +
      // The avatar and favourite badge are at the very top: load them right away.
      (/profile_up_avatar|profile_right_achievement_icon/.test(cls) ? '" loading="eager" fetchpriority="high"/>' : '" loading="lazy"/>')
    );
  }
  function imgTag(url, cls, alt) {
    return mediaTag(url, cls, alt);
  }
  function slotTag(url, cls, alt, slot, index) {
    return '<button type="button" class="sm-media-slot" data-slot="' + esc(slot) + '" data-index="' +
      esc(index == null ? 0 : index) + '" aria-label="' + esc(tr('replace_media')) + '">' + mediaTag(url, cls, alt) +
      '<span class="sm-media-slot__action">' + (url ? tr('replace') : tr('upload')) + '</span></button>';
  }

  function defaultState() {
    return {
      name: "Steam User",
      realname: "",
      level: 1,
      status: "Currently Offline",
      summary: "",
      avatar: "",
      frame: "",
      background: "",
      backgroundMovie: "",
      favBadge: { image: "", title: "Favorite Badge", xp: "" },
      awards: [],
      badges: [],
      groups: [],
      stats: {
        games: 0,
        inventory: 0,
        screenshots: 0,
        videos: 0,
        workshop: 0,
        reviews: 0,
        guides: 0,
        artwork: 0,
      },
      showcases: [
        { type: "artwork", title: "Artwork Showcase", images: ["", ""] },
        {
          type: "workshop",
          title: "Workshop Showcase",
          images: ["", "", "", "", ""],
          subs: 0,
          followers: 0,
        },
        { type: "guide", title: "Favorite Guide", images: [""], author: "", ratings: 0 },
      ],
    };
  }

  /* ---- Steam-faithful showcases (imports parsed by smweb/steam_showcases.py) ----
     Markup follows Steam's own profile_customization structure; styles live in
     /static/steam-mockup/showcases.css under the .smsc namespace. */
  function safeHref(url) {
    return /^https:\/\/([a-z0-9-]+\.)*(steamcommunity\.com|steampowered\.com)\//i.test(String(url || "")) ? String(url) : "";
  }
  function richHtml(segments) {
    return (segments || []).map(function (seg) {
      if (!seg) return "";
      if (seg.t === "br") return "<br>";
      if (seg.t === "hr") return "<hr>";
      if (seg.t === "emoticon") return '<img class="smsc-emoticon" src="' + esc(px(seg.src)) + '" alt="' + esc(seg.alt || "") + '" title="' + esc(seg.alt || "") + '" loading="lazy">';
      if (seg.t === "image") return '<img class="smsc-inline-img" src="' + esc(px(seg.src)) + '" alt="" loading="lazy">';
      if (seg.t === "link") {
        var href = safeHref(seg.href);
        return href ? '<a class="smsc-bb-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' + esc(seg.v) + "</a>" : esc(seg.v);
      }
      var cls = seg.s ? ' class="smsc-bb-' + esc(seg.s) + '"' : "";
      return cls ? "<span" + cls + ">" + esc(seg.v) + "</span>" : esc(seg.v);
    }).join("");
  }
  function statsRow(stats, extraCls) {
    if (!stats || !stats.length) return "";
    return '<div class="smsc-stats' + (extraCls ? " " + extraCls : "") + '">' + stats.map(function (s) {
      return '<div class="' + ["smsc-stat", s.tone ? "smsc-stat--" + esc(s.tone) : ""].join(" ") + '"><div class="smsc-stat__value">' + esc(s.value) + '</div><div class="smsc-stat__label">' + esc(s.label) + "</div></div>";
    }).join("") + "</div>";
  }
  function shell(sc, idx, body, opts) {
    opts = opts || {};
    var cls = ["smsc", "smsc--" + sc.type, opts.art ? "smsc--art" : ""].join(" ");
    return '<div class="' + esc(cls) + '" data-sc="' + idx + '">' +
      (opts.art ? "" : '<div class="smsc-header">' + esc(localizedKnown(sc.title || tr("showcase"))) + "</div>") +
      (opts.before || "") + '<div class="smsc-block">' + body + "</div></div>";
  }
  function screenshotShowcase(sc, idx) {
    var imgs = sc.images || [];
    var single = sc.type === "featured";
    var main = '<div class="smsc-shot-primary' + (single ? " is-single" : "") + '">' +
      '<div class="smsc-shot">' + slotTag(imgs[0] || "", "smsc-shot__img", "showcase", "showcase", idx + ":0") + "</div>" +
      (sc.caption && sc.caption.replace(/[\s᠌⠀]+/g, "") ? '<div class="smsc-shot-name">' + esc(sc.caption) + "</div>" : "") +
      (sc.shot_stats && sc.shot_stats.length
        ? '<div class="smsc-shot-stats">' + sc.shot_stats.map(function (st) {
            return '<span class="smsc-shot-stat" title="' + esc(st.title) + '">' + (st.icon ? '<img src="' + esc(px(st.icon)) + '" alt="">' : "") + " " + esc(st.value) + "</span>";
          }).join("") + "</div>"
        : sc.favorites ? '<div class="smsc-shot-stats"><span class="smsc-fav" aria-hidden="true">★</span> ' + esc(sc.favorites) + "</div>" : "") +
      "</div>";
    if (single) return shell(sc, idx, main, { art: sc.type !== "screenshots" });
    var side = "";
    var smallCount = sc.type === "screenshots" ? 4 : 1;
    for (var i = 1; i <= smallCount; i++) {
      if (i > 1 && !imgs[i]) break;
      side += '<div class="smsc-shot smsc-shot--small">' + slotTag(imgs[i] || "", "smsc-shot__img", "showcase", "showcase", idx + ":" + i) + "</div>";
    }
    if (sc.more) side += '<div class="smsc-shot-count">' + esc(sc.more) + "</div>";
    return shell(sc, idx, main + '<div class="smsc-shot-rightcol">' + side + "</div>", { art: sc.type !== "screenshots" });
  }
  function iconImg(item, cls) {
    return item && item.image ? '<img class="' + cls + '" src="' + esc(px(item.image)) + '" alt="" title="' + esc(item.title || "") + '" loading="lazy">' : "";
  }
  /* Recent activity / favourite game card: capsule, name, hours, achievement progress. */
  function gameInfoHtml(g, opts) {
    g = g || {};
    opts = opts || {};
    var ach = "";
    if (g.progress || (g.achievements && g.achievements.length)) {
      ach = '<div class="smsc-gi-ach">' +
        (g.progress ? '<div class="smsc-gi-summary"><span class="smsc-gi-summary__label">' + tr("ach_progress") + '</span> <span>' + esc(g.progress.text) + '</span>' +
          '<span class="smsc-gi-bar"><span style="width:' + esc(Math.max(0, Math.min(100, +g.progress.pct || 0))) + '%"></span></span></div>' : "") +
        '<div class="smsc-gi-icons">' + (g.achievements || []).map(function (a) { return iconImg(a, "smsc-gi-icon"); }).join("") +
        (g.more ? '<span class="smsc-gi-more">' + esc(g.more) + "</span>" : "") + "</div></div>";
    }
    var files = (g.files || []).length ? (ach ? '<div class="smsc-gi-rule"></div>' : "") + '<div class="smsc-gi-files">' + g.files.map(function (f) { return "<span>" + esc(f) + "</span>"; }).join("") + "</div>" : "";
    var head = opts.favorite
      ? '<div class="smsc-fg"><div class="smsc-fg__cap">' + (g.image ? '<img src="' + esc(px(g.image)) + '" alt="">' : "") + '</div><div class="smsc-guide__title">' + esc(g.name) + "</div></div>"
      : '<div class="smsc-gi"><div class="smsc-gi__cap">' + (g.image ? '<img src="' + esc(px(g.image)) + '" alt="">' : "") + '</div>' +
        '<div class="smsc-gi__name">' + esc(g.name) + '</div><div class="smsc-gi__details">' + (g.details || []).map(esc).join("<br>") + "</div></div>";
    return { head: head, stats: ach || files ? '<div class="smsc-gi-stats">' + ach + files + "</div>" : "" };
  }
  function hasSidebar(state) {
    var s = state.sidebar;
    return !!(s && ((s.counts && s.counts.length) || s.badges || s.friends || s.groups));
  }
  function sidebarHtml(state) {
    var s = state.sidebar || {};
    var status = s.status || state.status || "Currently Offline";
    var tone = /in-game|в игре/i.test(status) ? "ingame" : /online|в сети/i.test(status) ? "online" : "offline";
    function count(label, value) {
      return '<div class="smsb-count"><span class="smsb-count__label">' + esc(label) + '</span> <span class="smsb-count__total">' + esc(value) + "</span></div>";
    }
    function iconRow(box, cls) {
      return box && box.items && box.items.length ? '<div class="smsb-icons">' + box.items.slice(0, 4).map(function (i) { return iconImg(i, cls); }).join("") + "</div>" : "";
    }
    var html = '<div class="smsb">' +
      '<div class="smsb-status smsb-status--' + tone + '">' + esc(localizedKnown(status)) + (s.status_game ? '<div class="smsb-status__game">' + esc(s.status_game) + "</div>" : "") + "</div>";
    if (s.awards) html += '<div class="smsb-section">' + count(tr("awards"), s.awards.count) + iconRow(s.awards, "smsb-award") + "</div>";
    if (s.badges) html += '<div class="smsb-section">' + count(tr("badges"), s.badges.count) + iconRow(s.badges, "smsb-badge") + "</div>";
    if (s.counts && s.counts.length) html += '<div class="smsb-section">' + s.counts.map(function (c) { return count(c.label, c.value); }).join("") + "</div>";
    if (s.groups) {
      html += '<div class="smsb-section">' + count(tr("groups"), s.groups.count) + (s.groups.items || []).map(function (g, n) {
        return '<div class="smsb-group' + (n === 0 ? " is-primary" : "") + '">' + (g.avatar ? '<img src="' + esc(px(g.avatar)) + '" alt="">' : "<span></span>") +
          '<div class="smsb-group__text"><span class="smsb-group__name">' + esc(g.name) + "</span>" + (g.members ? '<span class="smsb-group__members">' + esc(g.members) + "</span>" : "") + "</div></div>";
      }).join("") + "</div>";
    }
    if (s.friends) {
      html += '<div class="smsb-section">' + count(tr("friends"), s.friends.count) + (s.friends.items || []).map(function (f) {
        return '<div class="smsb-friend smsb-friend--' + esc(f.persona || "offline") + '">' + (f.avatar ? '<img src="' + esc(px(f.avatar)) + '" alt="">' : "<span></span>") +
          '<div class="smsb-friend__text"><span class="smsb-friend__name">' + esc(f.name) + '</span><span class="smsb-friend__status">' + esc(f.status) + "</span></div>" +
          (f.level ? '<span class="smsb-level">' + esc(f.level) + "</span>" : "") + "</div>";
      }).join("") + "</div>";
    }
    return html + "</div>";
  }
  function commentsHtml(c) {
    if (!c || !(c.items && c.items.length)) return "";
    return '<div class="smcm"><div class="smcm-header"><span>' + tr("comments") + "</span>" +
      (c.total > c.items.length ? '<span class="smcm-all">' + esc(tr("view_all").replace("{n}", c.total)) + "</span>" : "") + "</div>" +
      '<div class="smcm-list">' + c.items.map(function (m) {
        return '<div class="smcm-comment"><span class="smcm-avatar smcm-avatar--' + esc(m.persona || "offline") + '">' +
          (m.avatar ? '<img src="' + esc(px(m.avatar)) + '" alt="">' : "") + '</span><div class="smcm-body"><div class="smcm-name">' + esc(m.author) + "</div>" +
          '<div class="smcm-time">' + esc(m.time) + '</div><div class="smcm-text">' + richHtml(m.rich) + "</div></div></div>";
      }).join("") + "</div></div>";
  }
  function renderStructured(sc, idx) {
    var t = sc.type;
    var imgs = sc.images || [];
    if (t === "achievements" || t === "badges") {
      var icons = sc.icons && sc.icons.length ? sc.icons : imgs.map(function (u) { return { image: u }; });
      var achCells = icons.map(function (ic, n) {
        return '<div class="' + ["smsc-ach", t === "badges" ? "smsc-ach--badge" : ""].join(" ") + '" title="' + esc(ic.title || "") + '">' + slotTag(imgs[n] || ic.image, "smsc-ach__img", ic.title || "", "showcase", idx + ":" + n) + "</div>";
      }).join("") + (sc.more ? '<div class="smsc-ach smsc-ach--more"><span>' + esc(sc.more) + "</span></div>" : "");
      return shell(sc, idx, '<div class="' + (t === "badges" ? "smsc-badges" : ["smsc-content", "smsc-achs"].join(" ")) + '">' + achCells + "</div>" +
        (sc.stats && sc.stats.length ? '<div class="smsc-content">' + statsRow(sc.stats) + "</div>" : ""));
    }
    if (t === "favoritegame") {
      var fg = gameInfoHtml(sc.game, { favorite: true });
      return shell(sc, idx, '<div class="smsc-content">' + fg.head + statsRow(sc.stats) + "</div>" + fg.stats);
    }
    if (t === "activity") {
      var recent = (sc.games || []).map(function (g) {
        var gi = gameInfoHtml(g);
        return '<div class="smsc-recent">' + gi.head + gi.stats + "</div>";
      }).join("");
      return '<div class="smsc smsc--activity" data-sc="' + idx + '"><div class="smsc-header smsc-header--split"><span>' + esc(sc.title || "Recent Activity") + "</span>" +
        (sc.playtime ? '<span class="smsc-header__aside">' + esc(sc.playtime) + "</span>" : "") + '</div><div class="smsc-block smsc-block--activity">' + recent +
        (sc.quicklinks && sc.quicklinks.length ? '<div class="smsc-quicklinks">' + tr("view") + " " + sc.quicklinks.map(function (q) { return "<span>" + esc(q) + "</span>"; }).join('<i>|</i>') + "</div>" : "") + "</div></div>";
    }
    if (t === "group") {
      var gr = sc.group || {};
      return shell(sc, idx, '<div class="smsc-content"><div class="smsc-group">' +
        '<div class="smsc-group__avatar">' + (gr.avatar ? '<img src="' + esc(px(gr.avatar)) + '" alt="">' : "") + "</div>" +
        '<div class="smsc-group__content"><div class="smsc-group__namerow"><span class="smsc-group__name">' + esc(gr.name) + "</span>" + (gr.kind ? " - " + esc(gr.kind) : "") + "</div>" +
        '<div class="smsc-group__desc">' + esc(gr.description) + "</div>" + statsRow(sc.stats, "smsc-stats--group") + "</div></div></div>");
    }
    if (t === "featured" || t === "artwork" || t === "screenshots") return screenshotShowcase(sc, idx);
    if (t === "info") {
      var body = sc.rich && sc.rich.length ? richHtml(sc.rich) : esc(sc.text || "").replace(/\n/g, "<br>");
      return shell(sc, idx, '<div class="smsc-content smsc-notes">' + body + "</div>");
    }
    if (t === "trade" || t === "items") {
      var slots = sc.slots || [];
      var cells = slots.map(function (s, n) {
        var style = (s.border ? "border-color" + ":" + s.border + ";" : "") + (s.bg ? "background-color" + ":" + s.bg + ";" : "");
        return '<div class="smsc-item"' + (style ? ' style="' + esc(style) + '"' : "") + (s.name ? ' title="' + esc(s.name) + '"' : "") + ">" +
          slotTag(imgs[n] || s.image || "", "smsc-item__img", s.name || "item", "showcase", idx + ":" + n) + "</div>";
      }).join("");
      var notes = sc.rich && sc.rich.length ? '<div class="smsc-notes">' + richHtml(sc.rich) + "</div>" : "";
      var statsBox = (sc.stats && sc.stats.length) || notes ? '<div class="smsc-content">' + statsRow(sc.stats, "smsc-stats--trading") + notes + "</div>" : "";
      if (t === "items") {
        var countStat = sc.stats && sc.stats.length ? '<div class="smsc-item-count">' + statsRow(sc.stats.slice(0, 1)) + "</div>" : "";
        return shell(sc, idx, '<div class="smsc-items">' + cells + countStat + "</div>" + (notes ? '<div class="smsc-content">' + notes + "</div>" : ""));
      }
      return shell(sc, idx, '<div class="smsc-items">' + cells + "</div>" + statsBox);
    }
    if (t === "gamecollector") {
      var games = imgs.map(function (u, n) {
        return '<div class="smsc-game">' + slotTag(u, "smsc-game__img", "game", "showcase", idx + ":" + n) + "</div>";
      }).join("");
      return shell(sc, idx, (sc.stats && sc.stats.length ? '<div class="smsc-content">' + statsRow(sc.stats) + "</div>" : "") +
        (sc.label ? '<div class="smsc-bodylabel">' + esc(sc.label) + "</div>" : "") + '<div class="smsc-games">' + games + "</div>");
    }
    if (t === "workshop") {
      var tiles = "";
      var count = Math.max(5, imgs.length);
      if (count % 5) count += 5 - (count % 5);
      for (var w = 0; w < count; w++) tiles += '<div class="smsc-ws-tile">' + slotTag(imgs[w] || "", "smsc-ws-tile__img", "workshop", "showcase", idx + ":" + w) + "</div>";
      var head = sc.workshopName ? '<div class="smsc-ws-head">' + (sc.avatar ? '<img src="' + esc(px(sc.avatar)) + '" alt="">' : "") + "<span>" + esc(sc.workshopName) + "</span></div>" : "";
      return shell(sc, idx, '<div class="smsc-ws-grid">' + tiles + "</div>" + (sc.stats && sc.stats.length ? '<div class="smsc-content smsc-ws-stats">' + statsRow(sc.stats) + "</div>" : ""), { before: head });
    }
    if (t === "guide" || t === "workshop_item") {
      var g = sc.guide || {};
      return shell(sc, idx, '<div class="smsc-content smsc-guide">' +
        '<div class="smsc-guide__img">' + slotTag(imgs[0] || "", "smsc-guide__image", "guide", "showcase", idx + ":0") + "</div>" +
        '<div class="smsc-guide__details">' +
        (g.title ? '<div class="smsc-guide__title">' + esc(g.title) + "</div>" : "") +
        (g.author ? '<div class="smsc-guide__author">' + esc(g.author) + "</div>" : "") +
        '<div class="smsc-guide__app">' + (g.stars || g.ratings ? '<span class="smsc-guide__stars">' + (g.stars ? '<img src="' + esc(px(g.stars)) + '" alt="">' : "") + (g.ratings ? " " + esc(g.ratings) : "") + "</span>" : "") +
        (g.app_icon ? '<img class="smsc-guide__appicon" src="' + esc(px(g.app_icon)) + '" alt="">' : "") + (g.app ? "<span>" + esc(g.app) + "</span>" : "") + "</div>" +
        (g.description ? '<div class="smsc-guide__desc">' + esc(g.description) + "</div>" : "") +
        "</div></div>");
    }
    // Achievements, badges, favourite game/group, reviews, completionist, awards…
    var grid = imgs.length ? '<div class="smsc-grid smsc-grid--' + esc(t) + '">' + imgs.map(function (u, n) {
      return '<div class="smsc-grid__cell">' + slotTag(u, "smsc-grid__img", "showcase item", "showcase", idx + ":" + n) + "</div>";
    }).join("") + "</div>" : "";
    var caption = sc.caption ? '<div class="smsc-guide__title">' + esc(sc.caption) + "</div>" : "";
    var notesHtml = sc.rich && sc.rich.length ? '<div class="smsc-notes">' + richHtml(sc.rich) + "</div>" : "";
    return shell(sc, idx, (sc.stats && sc.stats.length ? '<div class="smsc-content">' + statsRow(sc.stats) + "</div>" : "") +
      (sc.label ? '<div class="smsc-bodylabel">' + esc(sc.label) + "</div>" : "") + caption + grid +
      (notesHtml ? '<div class="smsc-content">' + notesHtml + "</div>" : ""));
  }

  function renderShowcase(sc, idx) {
    if (sc && sc.v === 2) return renderStructured(sc, idx);
    var t = (sc.type || "").toLowerCase();
    if (t === "featured") {
      return (
        '<div class="profile_main_banner profile_main_banner--featured" data-sc="' + idx + '">' +
        '<div class="profile_main_banner_up"><div class="profile_main_banner_up_content">' +
        '<div class="profile_main_banner_title">' + esc(localizedKnown(sc.title || "Featured Artwork Showcase")) +
        '</div></div></div><div class="profile_main_banner_main"><div class="profile_main_banner_main_content">' +
        '<div class="profile_main_featured">' +
        slotTag((sc.images && sc.images[0]) || "", "profile_main_featured_img", "featured artwork", "showcase", idx + ':0') +
        '</div><div class="profile_main_banner_stats"><span class="profile_main_like">♥ 0</span>' +
        '<span class="profile_main_comment">💬 0</span></div></div></div></div>'
      );
    }
    if (t === "artwork" || t === "art" || t === "split") {
      var big = (sc.images && sc.images[0]) || "";
      var side = (sc.images && sc.images[1]) || "";
      return (
        '<div class="profile_main_banner" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_banner_up"><div class="profile_main_banner_up_content">' +
        '<div class="profile_main_banner_title">' +
        esc(localizedKnown(sc.title || "Artwork Showcase")) +
        "</div></div></div>" +
        '<div class="profile_main_banner_main"><div class="profile_main_banner_main_content">' +
        '<div class="profile_main_banners">' +
        slotTag(big, "profile_main_banner_big", "artwork", "showcase", idx + ':0') +
        slotTag(side, "profile_main_banner_small", "artwork side", "showcase", idx + ':1') +
        "</div>" +
        '<div class="profile_main_banner_stats">' +
        '<span class="profile_main_like">♥ 0</span>' +
        '<span class="profile_main_comment">💬 0</span>' +
        "</div></div></div></div>"
      );
    }
    if (t === "workshop") {
      var imgs = (sc.images || []).filter(Boolean);
      var n = Math.max(5, Math.min(15, imgs.length || 5));
      // pad to full rows of 5
      if (n % 5) n = n + (5 - (n % 5));
      var cells = "";
      for (var i = 0; i < n; i++) {
        cells +=
          '<div class="profile_main_workshop_main_image">' +
          slotTag(imgs[i] || "", "profile_main_workshop_img", "ws", "showcase", idx + ':' + i) +
          "</div>";
      }
      var wsIcon = imgs[0] || "";
      return (
        '<div class="profile_main_workshop" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_workshop_up"><div class="profile_main_workshop_up_content">' +
        '<div class="profile_main_workshop_title">' +
        esc(localizedKnown(sc.title || "Workshop Showcase")) +
        "</div></div></div>" +
        '<div class="profile_main_workshop_main"><div class="profile_main_workshop_main_content">' +
'<div class="profile_main_workshop_main_title">' +
        (wsIcon ? '<img src="' + esc(px(wsIcon)) + '" alt=""/>' : '') +
        '<span>' + esc(sc.workshopName || 'Workshop') + '</span></div>' +
        '<div class="profile_main_workshop_main_images">' +
        cells +
        "</div>" +
        '<div class="profile_main_workshop_main_stat_items">' +
        '<div class="profile_main_workshop_main_stat_item">' +
        '<div class="profile_main_workshop_main_stat_item_number">' +
        esc(sc.subs || 0) +
        "</div>" +
        '<div class="profile_main_workshop_main_stat_item_text">' + tr('submissions') + '</div></div>' +
        '<div class="profile_main_workshop_main_stat_item">' +
        '<div class="profile_main_workshop_main_stat_item_number">' +
        esc(sc.followers || 0) +
        "</div>" +
        '<div class="profile_main_workshop_main_stat_item_text">' + tr('followers') + '</div></div>' +
        "</div></div></div></div>"
      );
    }
    if (t === "guide") {
      return (
        '<div class="profile_main_guide" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_guide_inner">' +
        '<div class="profile_main_guide_title">' +
        esc(localizedKnown(sc.title || "Favorite Guide")) +
        "</div>" +
        '<div class="profile_main_guide_row">' +
        slotTag((sc.images && sc.images[0]) || "", "profile_main_guide_img", "guide", "showcase", idx + ':0') +
        '<div class="profile_main_guide_meta">' +
        "<div>" + tr('created_by') +
        esc(sc.author || "") +
        "</div>" +
        "<div>★★★☆☆ " +
        esc(sc.ratings || 0) +
        tr('ratings') + "</div>" +
        "</div></div></div></div>"
      );
    }
    if (t === "info") {
      return (
        '<div class="profile_main_info" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_info_title">' +
        esc(localizedKnown(sc.title || "Info")) +
        "</div>" +
        '<div class="profile_main_info_body">' +
        esc(sc.text || "") +
        (sc.link
          ? '<div class="profile_main_info_link"><a href="' +
            esc(sc.link) +
            '" target="_blank" rel="noopener">' +
            esc(sc.link) +
            "</a></div>"
          : "") +
        "</div></div>"
      );
    }
    if (t === "artfav" || t === "favorite_artwork") {
      return (
        '<div class="profile_main_illustration" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_illustration_title">' +
        esc(localizedKnown(sc.title || "Favorite Artwork")) +
        "</div>" +
        slotTag((sc.images && sc.images[0]) || "", "profile_main_illustration_img", "fav", "showcase", idx + ':0') +
        "</div>"
      );
    }
    // Steam has several smaller showcase families (game collector, items for
    // trade, achievement grids). Preserve them as editable grids instead of
    // collapsing the whole block into one oversized image.
    var genericImages = (sc.images || []).slice(0, t === "items" ? 12 : 8);
    var genericSlots = genericImages.length ? genericImages : [""];
    return (
      '<div class="profile_main_banner" data-sc="' +
      idx +
      '"><div class="profile_main_banner_up_content"><div class="profile_main_banner_title">' +
      esc(localizedKnown(sc.title || sc.type || tr('showcase'))) +
      "</div></div>" +
      '<div class="sm-generic-grid sm-generic-grid--' + esc(t || "other") + '">' + genericSlots.map(function(url, n) {
        return slotTag(url, "sm-generic-grid__media", "showcase item", "showcase", idx + ':' + n);
      }).join("") + '</div>' +
      "</div>"
    );
  }

  function render(state, root) {
    state = state || defaultState();
    var bg = "";
    var pageStyle = "";
    var bgMovie = state.backgroundMovie || (isVideoUrl(state.background) ? state.background : "");
    var bgStill = state.background && !isVideoUrl(state.background) ? fullBackgroundUrl(state.background) : "";
    if (bgMovie) {
      /* The still is painted first so the page is never black while the
         animated background is still downloading. The video itself plays
         straight from Steam's CDN; our proxy is only the fallback. */
      bg =
        '<video class="profile_animated_background" autoplay muted loop playsinline preload="auto"' +
        (bgStill ? ' poster="' + esc(px(bgStill)) + '"' : "") +
        ' src="' + esc(directMedia(bgMovie)) + '" data-proxy-src="' + esc(px(bgMovie)) + '"></video>';
    }
    if (bgStill) {
      pageStyle = ' style="background-image:url(&quot;' + esc(px(bgStill)) + '&quot;)"';
    }

    var awards = (state.awards || [])
      .slice(0, 8)
      .map(function (a) {
        var u = typeof a === "string" ? a : a.image || a.url || "";
        return imgTag(u, "profile_right_award_img", "award");
      })
      .join("");

    var badges = (state.badges || [])
      .slice(0, 12)
      .map(function (b) {
        var u = typeof b === "string" ? b : b.image || b.url || "";
        return imgTag(u, "profile_right_badge_img", "badge");
      })
      .join("");

    var groups = (state.groups || [])
      .slice(0, 6)
      .map(function (g) {
        return (
          '<div class="profile_groups_item">' +
          imgTag(g.avatar || "", "profile_group_av", "") +
          '<span class="profile_groups_text"><span class="profile_groups_name">' +
          esc(g.name || "") +
          '</span><span class="profile_groups_members">' +
          esc(g.members || g.member_count || "") +
          "</span></span></div>"
        );
      })
      .join("");

    var stats = state.stats || {};
    var statRows = [
      [tr('games'), stats.games],
      [tr('inventory'), stats.inventory || stats.inv],
      [tr('screenshots'), stats.screenshots || stats.screens],
      [tr('videos'), stats.videos],
      [tr('workshop_items'), stats.workshop],
      [tr('reviews'), stats.reviews],
      [tr('guides'), stats.guides],
      [tr('artwork_stat'), stats.artwork || stats.art],
    ]
      .map(function (row) {
        return (
          '<div class="profile_right_stat_row"><span>' +
          esc(row[0]) +
          '</span><span class="profile_right_stat_num">' +
          esc(row[1] || 0) +
          "</span></div>"
        );
      })
      .join("");

    var showHtml = (state.showcases || [])
      .map(function (sc, i) {
        return renderShowcase(sc, i);
      })
      .join("");

    var frame = state.frame
      ? '<img class="profile_up_avatar_frame" src="' + esc(px(state.frame)) + '" alt=""/>'
      : "";

    root.innerHTML =
      '<div class="profile_page' + ((bgStill || bgMovie) ? ' profile_page--has-bg' : '') + '"' + pageStyle + '>' +
      bg +
      '<div class="profile_background_fade" aria-hidden="true"></div>' +
      '<div class="container_profile">' +
      '<div class="profile_sections">' +
      '<div class="profile_section_main">' +
      '<div class="profile_up">' +
      '<div class="profile_up_avatar_wrap">' +
      slotTag(state.avatar, "profile_up_avatar", "avatar", "avatar", 0) +
      frame +
      "</div>" +
      '<div class="profile_up_items">' +
      '<div class="profile_up_name">' +
      esc(localizedKnown(state.name)) +
      "</div>" +
      (state.summary
        ? '<div class="profile_up_summary">' + esc(state.summary) + "</div>"
        : "") +
      "</div></div>" +
      '<div class="profile_main_content">' +
      showHtml +
      commentsHtml(state.comments) +
      "</div></div>" +
      '<div class="profile_section_right">' +
      '<div class="profile_right_level"><em>' + tr('level') + '</em><span>' +
      esc(state.level || 0) +
      "</span></div>" +
      '<div class="profile_right_achievement">' +
      '<div class="profile_right_achievement_content">' +
      slotTag((state.favBadge && state.favBadge.image) || "", "profile_right_achievement_icon", "", "favBadge", 0) +
      '<div class="profile_right_achievement_texts">' +
      '<div class="profile_right_achievement_title">' +
      esc(localizedKnown((state.favBadge && state.favBadge.title) || "Favorite Badge")) +
      "</div>" +
      '<div class="profile_right_achievement_exp">' +
      esc((state.favBadge && state.favBadge.xp) || "") +
      "</div></div></div></div>" +
      (hasSidebar(state) ? sidebarHtml(state) :
      '<div class="profile_right_menu">' +
      '<div class="profile_right_menu_content">' +
      '<div class="profile_right_menu_status">' +
      esc(localizedKnown(state.status || "Currently Offline")) +
      "</div>" +
      '<div class="profile_right_awards_block"><div class="profile_right_block_title">' + tr('awards') + ' <span>' + esc((state.awards || []).length) + '</span></div><div class="profile_right_awards">' +
      (awards || '<div class="sm-slot-empty"></div>') +
      "</div></div>" +
      '<div class="profile_right_badges_block"><div class="profile_right_block_title">' + tr('badges') + ' <span>' + esc((state.badges || []).length) + '</span></div><div class="profile_right_badges">' +
      (badges || '<div class="sm-slot-empty"></div>') +
      "</div></div>" +
      '<div class="profile_right_stats">' +
      statRows +
      "</div>" +
      '<div class="profile_groups"><div class="profile_right_block_title">' + tr('groups') + ' <span>' + esc((state.groups || []).length) + '</span></div>' +
      (groups || '<div class="profile_groups_empty">' + tr('no_groups') + '</div>') +
      "</div>" +
      "</div></div>") +
      "</div></div></div></div>";
    var movie = root.querySelector("video.profile_animated_background[data-proxy-src]");
    if (movie && movie.getAttribute("src") !== movie.getAttribute("data-proxy-src")) {
      movie.addEventListener("error", function () {
        movie.src = movie.getAttribute("data-proxy-src");
      }, { once: true });
    }
  }

  function applySteamProfile(apiProfile, state) {
    state = state || defaultState();
    var p = apiProfile || {};
    /* always replace lists so a second import does not keep old badges/showcases */
    state.badges = [];
    state.awards = [];
    state.groups = [];
    state.favBadge = { image: "", title: "Favorite Badge", xp: "" };
    state.background = "";
    state.backgroundMovie = "";
    state.frame = "";
    state.showcases = defaultState().showcases;
    state.stats = defaultState().stats;
    state.sidebar = p.sidebar && typeof p.sidebar === "object" ? p.sidebar : null;
    state.comments = p.comments && p.comments.items && p.comments.items.length ? p.comments : null;
    if (state.sidebar) {
      if (state.sidebar.status) p.status = p.status || state.sidebar.status;
      if (state.sidebar.groups && !(p.groups && p.groups.length)) {
        state.groups = state.sidebar.groups.items.map(function (g) { return { name: g.name, avatar: g.avatar, members: g.members }; });
      }
    }
    if (p.name) state.name = p.name;
    if (p.realname) state.realname = p.realname;
    if (p.level != null) state.level = p.level;
    if (p.summary) state.summary = p.summary;
    if (p.avatar) state.avatar = p.avatar;
    if (p.background) state.background = p.background;
    if (p.background_item && p.background_item.poster) state.background = p.background_item.poster;
    if (p.background_movie) state.backgroundMovie = p.background_movie;
    if (p.background_item) state.backgroundMovie = p.background_item.webm || p.background_item.mp4 || state.backgroundMovie;
    if (p.background && isVideoUrl(p.background) && !state.backgroundMovie) state.backgroundMovie = p.background;
    if (p.frame) state.frame = p.frame;
    if (p.avatar_frame) state.frame = p.avatar_frame.animated || p.avatar_frame.static || state.frame;
    if (p.favorite_badge || p.favBadge) {
      var fb = p.favorite_badge || p.favBadge;
      state.favBadge = {
        image: fb.image || "",
        title: fb.title || "Favorite Badge",
        xp: fb.xp || ""
      };
    }
    if (p.status) {
      var s = String(p.status).toLowerCase();
      state.status = /online/.test(s)
        ? "Currently Online"
        : /in-game|ingame|game/.test(s)
          ? "Currently In-Game"
          : "Currently Offline";
    }
    if (p.groups && p.groups.length) state.groups = p.groups;
    var sm = p.stats_map || {};
    Object.keys(sm).forEach(function (k) {
      if (k === "inv") state.stats.inventory = sm[k];
      else if (k === "screens") state.stats.screenshots = sm[k];
      else if (k === "art") state.stats.artwork = sm[k];
      else if (k in state.stats) state.stats[k] = sm[k];
    });
    if (p.badges && p.badges.length) {
      state.badges = p.badges.map(function (b) {
        return typeof b === "string" ? { image: b } : b;
      });
    }
    if (p.awards && p.awards.length) {
      state.awards = p.awards.map(function (b) {
        return typeof b === "string" ? { image: b } : b;
      });
    }
    var imported = p.showcase_instances || p.showcases || [];
    if (imported.length) {
      var list = [];
      var artN = 0;
      imported.forEach(function (sc) {
        // Also sanitize older cached imports and extension-supplied catalogs.
        var images = (sc.images || []).filter(function (url) {
          return url && !/^(?:https?:)?\/\/avatars\./i.test(url) && !/\/avatars\//i.test(url);
        });
        var typ = (sc.type || "other").toLowerCase();
        if (Array.isArray(sc.stats)) {
          // Structured import: keep Steam's own fields and layout.
          var item = { v: 2, type: typ, title: sc.title || "", images: images.slice(0, 40) };
          ["stats", "rich", "slots", "guide", "caption", "favorites", "more", "label", "workshopName", "avatar", "text", "icons", "game", "games", "group", "playtime", "shot_stats", "quicklinks"].forEach(function (key) {
            if (sc[key] != null && sc[key] !== "") item[key] = sc[key];
          });
          if (item.slots) item.images = item.slots.map(function (s) { return s.image || ""; });
          list.push(item);
          return;
        }
        if (typ.indexOf("workshop") >= 0) {
          list.push({
            type: "workshop",
            title: sc.title || "Workshop Showcase",
            images: images.slice(0, 15),
            workshopName: (sc.title || "").replace(/Showcase/i, "").trim() || "Workshop",
            subs: sc.subs || 0,
            followers: sc.followers || 0,
          });
        } else if (typ.indexOf("guide") >= 0) {
          list.push({
            type: "guide",
            title: sc.title || "Favorite Guide",
            images: images.slice(0, 1),
            author: sc.author || p.name || "",
            ratings: 0,
          });
        } else if (typ.indexOf("info") >= 0) {
          var infoLink = sc.links && sc.links[0];
          list.push({
            type: "info",
            title: sc.title || "Info",
            text: sc.text || "",
            link: (infoLink && (infoLink.url || infoLink)) || "",
          });
        } else if (typ.indexOf("gamecollector") >= 0 || typ === "games") {
          list.push({type:"gamecollector",title:sc.title || "Game Collector",images:images.slice(0,8)});
        } else if (typ.indexOf("items") >= 0 || typ.indexOf("item") >= 0) {
          list.push({type:"items",title:sc.title || "Item Showcase",images:images.slice(0,12)});
        } else if (typ === "unknown") {
          list.push({type:"unknown",title:sc.title || "Steam Showcase",images:images.slice(0, 8)});
        } else if (images.length) {
          var title = String(sc.title || "Artwork Showcase");
          var lowerTitle = title.toLowerCase();
          var isFavorite = /favorite|избранн/.test(lowerTitle);
          var isFeatured = typ === "featured" || /featured|избранная иллюстрац/.test(lowerTitle);
          var isSplit = typ === "artwork" || typ === "split" || /split|раздел[её]н|составн/.test(lowerTitle);
          list.push({
            type: isFavorite ? "artfav" : (isSplit ? "split" : (isFeatured ? "featured" : "artwork")),
            title: title,
            images: isFavorite ? [images[0]] : [images[0] || "", images[1] || ""],
          });
          artN++;
        }
      });
      if (list.length) state.showcases = list;
    }
    return state;
  }

  global.SteamMockup = {
    defaultState: defaultState,
    render: render,
    applySteamProfile: applySteamProfile,
    px: px,
    esc: esc,
  };
})(window);
