/**
 * Steam-like profile mockup renderer (DOM + steam_profile.css classes).
 * Shared by /profile (editor) and /profile/{user} (public).
 */
(function (global) {
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
  function imgTag(url, cls, alt) {
    if (!url) {
      return '<div class="' + esc(cls) + ' sm-slot-empty" data-empty="1"></div>';
    }
    return (
      '<img class="' +
      esc(cls) +
      '" src="' +
      esc(px(url)) +
      '" alt="' +
      esc(alt || "") +
      '" loading="lazy"/>'
    );
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
        { type: "info", title: "Info", text: "", link: "" },
        {
          type: "workshop",
          title: "Workshop Showcase",
          images: ["", "", "", "", ""],
          subs: 0,
          followers: 0,
        },
        { type: "guide", title: "Favorite Guide", images: [""], author: "", ratings: 0 },
        { type: "artfav", title: "Favorite Artwork", images: [""] },
      ],
    };
  }

  function renderShowcase(sc, idx) {
    var t = (sc.type || "").toLowerCase();
    if (t === "artwork" || t === "art") {
      var big = (sc.images && sc.images[0]) || "";
      return (
        '<div class="profile_main_banner" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_banner_up"><div class="profile_main_banner_up_content">' +
        '<div class="profile_main_banner_title">' +
        esc(sc.title || "Artwork Showcase") +
        "</div></div></div>" +
        '<div class="profile_main_banner_main"><div class="profile_main_banner_main_content">' +
        '<div class="profile_main_banners">' +
        imgTag(big, "profile_main_banner_big", "artwork") +
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
          imgTag(imgs[i] || "", "profile_main_workshop_img", "ws") +
          "</div>";
      }
      var wsIcon = imgs[0] || "";
      return (
        '<div class="profile_main_workshop" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_workshop_up"><div class="profile_main_workshop_up_content">' +
        '<div class="profile_main_workshop_title">' +
        esc(sc.title || "Workshop Showcase") +
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
        '<div class="profile_main_workshop_main_stat_item_text">Submissions</div></div>' +
        '<div class="profile_main_workshop_main_stat_item">' +
        '<div class="profile_main_workshop_main_stat_item_number">' +
        esc(sc.followers || 0) +
        "</div>" +
        '<div class="profile_main_workshop_main_stat_item_text">Followers</div></div>' +
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
        esc(sc.title || "Favorite Guide") +
        "</div>" +
        '<div class="profile_main_guide_row">' +
        imgTag((sc.images && sc.images[0]) || "", "profile_main_guide_img", "guide") +
        '<div class="profile_main_guide_meta">' +
        "<div>Created by — " +
        esc(sc.author || "") +
        "</div>" +
        "<div>★★★☆☆ " +
        esc(sc.ratings || 0) +
        " ratings</div>" +
        "</div></div></div></div>"
      );
    }
    if (t === "info") {
      return (
        '<div class="profile_main_info" data-sc="' +
        idx +
        '">' +
        '<div class="profile_main_info_title">' +
        esc(sc.title || "Info") +
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
        esc(sc.title || "Favorite Artwork") +
        "</div>" +
        imgTag((sc.images && sc.images[0]) || "", "profile_main_illustration_img", "fav") +
        "</div>"
      );
    }
    // generic
    var g = (sc.images && sc.images[0]) || "";
    return (
      '<div class="profile_main_banner" data-sc="' +
      idx +
      '"><div class="profile_main_banner_up_content"><div class="profile_main_banner_title">' +
      esc(sc.title || sc.type || "Showcase") +
      "</div></div>" +
      imgTag(g, "profile_main_banner_big", "") +
      "</div>"
    );
  }

  function render(state, root) {
    state = state || defaultState();
    var bg = "";
    if (state.backgroundMovie) {
      bg =
        '<video class="profile_animated_background" autoplay muted loop playsinline src="' +
        esc(px(state.backgroundMovie)) +
        '"></video>';
    } else if (state.background) {
      bg =
        '<div class="profile_animated_background profile_animated_background_fallback" style="background-image:url(' +
        esc(px(state.background)) +
        ')"></div>';
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
          '<span class="profile_groups_name">' +
          esc(g.name || "") +
          "</span></div>"
        );
      })
      .join("");

    var stats = state.stats || {};
    var statRows = [
      ["Games", stats.games],
      ["Inventory", stats.inventory || stats.inv],
      ["Screenshots", stats.screenshots || stats.screens],
      ["Videos", stats.videos],
      ["Workshop Items", stats.workshop],
      ["Reviews", stats.reviews],
      ["Guides", stats.guides],
      ["Artwork", stats.artwork || stats.art],
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
      '<div class="profile_page">' +
      bg +
      '<div class="container_profile">' +
      '<div class="profile_sections">' +
      '<div class="profile_section_main">' +
      '<div class="profile_up">' +
      '<div class="profile_up_avatar_wrap">' +
      imgTag(state.avatar, "profile_up_avatar", "avatar") +
      frame +
      "</div>" +
      '<div class="profile_up_items">' +
      '<div class="profile_up_name">' +
      esc(state.name) +
      "</div>" +
      (state.summary
        ? '<div class="profile_up_summary">' + esc(state.summary) + "</div>"
        : "") +
      "</div></div>" +
      '<div class="profile_main_content">' +
      showHtml +
      "</div></div>" +
      '<div class="profile_section_right">' +
      '<div class="profile_right_level"><span>' +
      esc(state.level || 0) +
      "</span></div>" +
      '<div class="profile_right_achievement">' +
      '<div class="profile_right_achievement_content">' +
      imgTag((state.favBadge && state.favBadge.image) || "", "profile_right_achievement_icon", "") +
      '<div class="profile_right_achievement_texts">' +
      '<div class="profile_right_achievement_title">' +
      esc((state.favBadge && state.favBadge.title) || "Favorite Badge") +
      "</div>" +
      '<div class="profile_right_achievement_exp">' +
      esc((state.favBadge && state.favBadge.xp) || "") +
      "</div></div></div></div>" +
      '<div class="profile_right_menu">' +
      '<div class="profile_right_menu_content">' +
      '<div class="profile_right_menu_status">' +
      esc(state.status || "Currently Offline") +
      "</div>" +
      '<div class="profile_right_awards_block"><div class="profile_right_block_title">Profile Awards</div><div class="profile_right_awards">' +
      (awards || '<div class="sm-slot-empty"></div>') +
      "</div></div>" +
      '<div class="profile_right_badges_block"><div class="profile_right_block_title">Badges</div><div class="profile_right_badges">' +
      (badges || '<div class="sm-slot-empty"></div>') +
      "</div></div>" +
      '<div class="profile_right_stats">' +
      statRows +
      "</div>" +
      '<div class="profile_groups"><div class="profile_right_block_title">Groups</div>' +
      (groups || '<div class="profile_groups_empty">No groups</div>') +
      "</div>" +
      "</div></div>" +
      "</div></div></div></div>";
  }

  function applySteamProfile(apiProfile, state) {
    state = state || defaultState();
    var p = apiProfile || {};
    if (p.name) state.name = p.name;
    if (p.realname) state.realname = p.realname;
    if (p.level != null) state.level = p.level;
    if (p.summary) state.summary = p.summary;
    if (p.avatar) state.avatar = p.avatar;
    if (p.background) state.background = p.background;
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
    var imported = p.showcases || [];
    if (imported.length) {
      var list = [];
      var artN = 0;
      imported.forEach(function (sc) {
        var images = (sc.images || []).filter(Boolean);
        var typ = (sc.type || "other").toLowerCase();
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
          list.push({
            type: "info",
            title: sc.title || "Info",
            text: sc.text || "",
            link: (sc.links && sc.links[0]) || "",
          });
        } else if (images.length) {
          if (!artN) {
            list.push({
              type: "artwork",
              title: sc.title || "Artwork Showcase",
              images: images.slice(0, 2),
            });
          } else {
            list.push({
              type: "artfav",
              title: sc.title || "Favorite Artwork",
              images: [images[0]],
            });
          }
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
