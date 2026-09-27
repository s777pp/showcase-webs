import unittest

from smweb.steam_showcases import parse_showcases, sanitize
from smweb.steam import _clean_extension_profile

IMG = "https://images.steamusercontent.com/ugc/{}/x.png"
ECON = "https://community.fastly.steamstatic.com/economy/image/{}"
EMO = "https://community.fastly.steamstatic.com/economy/emoticon/{}"


def block(header, inner, extra=""):
    return (f'<div class="profile_customization{extra}"><div class="profile_customization_header">{header}</div>'
            f'<div class="profile_customization_block">{inner}</div></div>')


INFO = block("ABOUT ME", '<div class="customtext_showcase"><div class="showcase_content_bg showcase_notes">'
             f'<img class="emoticon" alt=":mb:" src="{EMO.format("mb")}"> Board<br><b>Bold</b> '
             '<a class="bb_link" href="https://steamcommunity.com/linkfilter/?u=https%3A%2F%2Fexample.com">Parts</a>'
             '<span class="bb_link_host">[example.com]</span></div></div>')
TRADE = block("Items Up For Trade", '<div class="trade_showcase"><div class="showcase_slot_row trade_showcase_items">'
              + "".join(f'<div class="showcase_slot item_showcase_item" style="border-color: #eb4b4b; background-color: #402d2d; ">'
                        f'<a><img class="item_image" src="{ECON.format(i)}"></a></div>' for i in range(3))
              + '</div><div class="showcase_content_bg"><div class="showcase_stats_row showcase_stats_trading">'
              '<a class="showcase_stat"><div class="value">479</div><div class="label">Items Owned</div></a></div>'
              '<div class="showcase_notes">trade code</div></div></div>')
FEATURED = block("Featured Artwork Showcase", '<div class="screenshot_showcase"><div class="screenshot_showcase_primary single showcase_slot">'
                 f'<a class="screenshot_showcase_screenshot"><img src="{IMG.format(1)}"></a>'
                 '<div class="screenshot_showcase_itemname">Name</div><div class="screenshot_showcase_stats">'
                 '<span class="screenshot_showcase_stat"><span class="screenshot_showcase_staticon favorite"></span> 2 </span></div></div></div>', " myart")
ARTWORK = block("Artwork Showcase", '<div class="screenshot_showcase"><div class="screenshot_showcase_primary showcase_slot">'
                f'<a class="screenshot_showcase_screenshot"><img src="{IMG.format(2)}"></a></div><div class="screenshot_showcase_rightcol">'
                f'<div class="screenshot_showcase_smallscreenshot showcase_slot"><a><img src="{IMG.format(3)}"></a></div>'
                '<a class="screenshot_showcase_smallscreenshot screenshot_count"><div class="screenshot_showcase_screenshot">+ 74</div></a></div></div>', " myart")
GAMES = block("Game Collector", '<div class="gamecollector_showcase"><div class="showcase_content_bg showcase_stats_row">'
              '<a class="showcase_stat"><div class="value">298</div><div class="label">Games</div></a></div>'
              '<div class="showcase_bodylabel">Featured Games</div><div class="showcase_gamecollector_games">'
              + "".join(f'<div class="showcase_slot showcase_gamecollector_game"><a><img class="game_capsule" '
                        f'src="https://shared.fastly.steamstatic.com/apps/{i}/capsule.jpg"></a></div>' for i in range(4))
              + '</div></div>')
ACTIVITY = block("Recent Activity", '<div class="recent_games"><div class="recent_game"></div></div>')


class SteamShowcaseParserTest(unittest.TestCase):
    def test_custom_titled_info_box_is_info_with_rich_text(self):
        sc = parse_showcases(INFO)[0]
        self.assertEqual(sc["type"], "info")
        self.assertEqual(sc["images"], [])
        kinds = [seg["t"] for seg in sc["rich"]]
        self.assertIn("emoticon", kinds)
        self.assertIn("link", kinds)
        self.assertIn({"t": "text", "v": "Bold", "s": "b"}, sc["rich"])

    def test_trade_keeps_rarity_colours_stats_and_notes(self):
        sc = parse_showcases(TRADE)[0]
        self.assertEqual(sc["type"], "trade")
        self.assertEqual(len(sc["slots"]), 3)
        self.assertEqual(sc["slots"][0]["border"], "#eb4b4b")
        self.assertEqual(sc["stats"], [{"value": "479", "label": "Items Owned"}])
        self.assertEqual(sc["text"], "trade code")

    def test_screenshot_family_split_into_featured_and_artwork(self):
        featured, artwork = parse_showcases(FEATURED + ARTWORK)
        self.assertEqual((featured["type"], featured["favorites"], featured["caption"]), ("featured", "2", "Name"))
        self.assertEqual(artwork["type"], "artwork")
        self.assertEqual(artwork["images"], [IMG.format(2), IMG.format(3)])
        self.assertEqual(artwork["more"], "+ 74")

    def test_game_collector_and_activity(self):
        items = parse_showcases(GAMES + ACTIVITY)
        self.assertEqual([i["type"] for i in items], ["gamecollector", "activity"])
        self.assertEqual(items[1]["images"], [])
        self.assertEqual(items[0]["label"], "Featured Games")
        self.assertEqual(len(items[0]["images"]), 4)

    def test_extension_html_goes_through_same_parser_and_allowlist(self):
        evil = block("X", '<div class="customtext_showcase"><div class="showcase_notes">'
                          '<a href="https://evil.example/x">bad</a><img class="emoticon" src="https://evil.example/e.png"></div></div>')
        profile = _clean_extension_profile({"name": "n", "showcase_html": INFO + TRADE + evil}, "76561198000000000")
        types = [sc["type"] for sc in profile["showcase_instances"]]
        self.assertEqual(types, ["info", "trade", "info"])
        self.assertEqual([seg["t"] for seg in profile["showcase_instances"][2]["rich"]], [])

    def test_sanitize_rejects_bad_colours(self):
        out = sanitize([{"type": "trade", "slots": [{"image": ECON.format(1), "border": "red;background:url(x)"}]}], lambda u: u)
        self.assertEqual(out[0]["slots"][0]["border"], "")


ACH = block("Rarest Achievement Showcase", '<div class="achievement_showcase"><div class="showcase_content_bg">'
            + "".join(f'<div class="showcase_achievement" data-tooltip-html="A{i}&lt;br&gt;desc"><a><img src="https://shared.fastly.steamstatic.com/a/{i}.jpg"></a></div>' for i in range(3))
            + '<div class="showcase_achievement plus_more">+19,854</div></div><div class="showcase_content_bg showcase_stats_row">'
            '<div class="showcase_stat" data-tooltip-text="x"><a class="showcase_stat"><div class="value">28%</div><div class="label">Avg</div></a></div></div></div>')
FAV_GAME = block("Favorite Game", '<div class="favoritegame_showcase"><div class="showcase_content_bg"><div class="favoritegame_showcase_game showcase_slot">'
                 '<div class="favorite_game_cap"><a><img class="game_capsule" src="https://shared.fastly.steamstatic.com/cap.jpg"></a></div>'
                 '<div class="showcase_item_detail_title"><a class="whiteLink">Dune</a></div></div><div class="showcase_stats_row"><div class="showcase_stat">'
                 '<div class="value">805</div><div class="label">Hours played</div></div></div></div><div class="game_info_stats"><span class="game_info_achievement_summary">'
                 '<a class="whiteLink">Achievement Progress</a> <span class="ellipsis">54 of 74</span></span><div class="achievement_progress_bar_ctn"><div class="progress_bar" style="width: 72%;"></div></div>'
                 '<div class="game_info_achievement plus_more">+49</div><a class="published_file_link">Review 1</a></div></div>')
GROUP = block("Favorite Group", '<div class="favoritegroup_showcase"><div class="showcase_content_bg"><div class="favoritegroup_showcase_group showcase_slot">'
              '<div class="favoritegroup_avatar"><a><img src="https://avatars.fastly.steamstatic.com/g.jpg"></a></div><div class="favoritegroup_content">'
              '<div class="favoritegroup_namerow ellipsis"><a class="favoritegroup_name">Innovate</a> - Public Group</div><div class="favoritegroup_description">desc</div>'
              '<div class="favoritegroup_stats showcase_stats_row"><div class="showcase_stat favoritegroup_online"><div class="value">46</div><div class="label">Online</div></div></div></div></div></div></div>')
PAGE = ('<div class="profile_page"><div class="profile_header_badge"><a class="favorite_badge"><div class="favorite_badge_icon"><img src="https://community.fastly.steamstatic.com/b.png"></div>'
        '<div class="favorite_badge_description"><div class="name ellipsis">Stockpiler</div><div class="xp">8,677 XP</div></div></a></div>'
        + ACH + '<div class="profile_rightcol"><div class="profile_in_game persona online"><div class="profile_in_game_header">Currently Online</div></div>'
        '<div class="profile_badges"><div class="profile_count_link"><a><span class="count_link_label">Badges</span><span class="profile_count_link_total"> 1,547 </span></a></div>'
        '<div class="profile_badges_badge"><a><img class="badge_icon small" src="https://community.fastly.steamstatic.com/b1.png"></a></div></div>'
        '<div class="profile_item_links"><div class="profile_count_link"><a><span class="count_link_label">Games</span><span class="profile_count_link_total"> 8,427 </span></a></div></div>'
        '<div class="profile_friend_links"><div class="profile_count_link"><a><span class="count_link_label">Friends</span><span class="profile_count_link_total"> 216 </span></a></div>'
        '<div class="profile_topfriends"><div class="friendBlock persona in-game"><div class="friendPlayerLevel"><span class="friendPlayerLevelNum">1010</span></div>'
        '<div class="playerAvatar in-game"><img src="https://avatars.fastly.steamstatic.com/f.jpg"></div><div class="friendBlockContent"> Noel<br><span class="friendSmallText">In-Game CS2</span></div></div></div></div></div>'
        '<div class="commentthread_area"><a class="commentthread_allcommentslink">View all <span id="commentthread_Profile_1_totalcount">369</span> comments</a>'
        '<div class="commentthread_comment"><div class="commentthread_comment_avatar playerAvatar online"><a><img src="https://avatars.fastly.steamstatic.com/c.jpg"></a></div>'
        '<a class="commentthread_author_link"><bdi>Fran</bdi></a><div class="commentthread_comment_timestamp"> </div><div class="commentthread_comment_timestamp">6 Sep @ 3:24am</div>'
        '<div class="commentthread_comment_text"> +Rep <b>best</b> </div></div></div></div>')


class SteamWholeProfileTest(unittest.TestCase):
    def test_rarest_achievements_keep_icons_more_tile_and_unnested_stats(self):
        sc = parse_showcases(ACH)[0]
        self.assertEqual(sc["type"], "achievements")
        self.assertEqual(len(sc["icons"]), 3)
        self.assertEqual(sc["icons"][0]["title"], "A0 - desc")
        self.assertEqual(sc["more"], "+19,854")
        self.assertEqual(sc["stats"], [{"value": "28%", "label": "Avg"}])

    def test_favorite_game_and_group(self):
        game, group = parse_showcases(FAV_GAME + GROUP)
        self.assertEqual(game["game"]["name"], "Dune")
        self.assertEqual(game["game"]["progress"], {"text": "54 of 74", "pct": 72.0})
        self.assertEqual((game["game"]["more"], game["game"]["files"]), ("+49", ["Review 1"]))
        self.assertEqual(group["group"]["kind"], "Public Group")
        self.assertEqual(group["stats"][0]["tone"], "online")

    def test_extension_page_html_brings_sidebar_badge_and_comments(self):
        profile = _clean_extension_profile({"name": "n", "page_html": PAGE}, "76561198000000000")
        side = profile["sidebar"]
        self.assertEqual(side["status"], "Currently Online")
        self.assertEqual(side["badges"]["count"], 1547)
        self.assertEqual(side["counts"], [{"label": "Games", "value": "8,427"}])
        self.assertEqual(side["friends"]["items"][0]["name"], "Noel")
        self.assertEqual(side["friends"]["items"][0]["persona"], "in-game")
        self.assertEqual(profile["favorite_badge"]["title"], "Stockpiler")
        self.assertEqual(profile["comments"]["total"], 369)
        comment = profile["comments"]["items"][0]
        self.assertEqual((comment["author"], comment["time"], comment["persona"]), ("Fran", "6 Sep @ 3:24am", "online"))
        self.assertIn({"t": "text", "v": "best", "s": "b"}, comment["rich"])


if __name__ == "__main__":
    unittest.main()
