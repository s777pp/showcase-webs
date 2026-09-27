from smweb.core import _check_public_url
from smweb.page_media import looks_like_media_file, meta_candidates


def test_popular_sources_are_accepted_and_others_are_not():
    for url in ("https://giphy.com/gifs/x", "https://tenor.com/view/x", "https://www.instagram.com/p/x/",
                "https://vk.com/video1_2", "https://www.pixiv.net/artworks/1", "https://wallhaven.cc/w/x"):
        assert _check_public_url(url) == (True, ""), url
    assert _check_public_url("https://example.com/page") == (False, "Unsupported source")


def test_private_addresses_stay_blocked_even_for_direct_files():
    assert not _check_public_url("http://127.0.0.1/a.png", any_host=True)[0]
    assert not _check_public_url("http://169.254.169.254/latest.gif", any_host=True)[0]
    # NAT64 addresses are judged by the IPv4 address they wrap.
    assert not _check_public_url("http://[64:ff9b::a00:1]/a.png", any_host=True)[0]


def test_direct_file_detection_ignores_query_strings():
    assert looks_like_media_file("https://cdn.example.com/a/b.GIF?cid=1")
    assert looks_like_media_file("https://cdn.example.com/clip.mp4")
    assert not looks_like_media_file("https://example.com/view/cat-gif-123")


def test_meta_candidates_prefer_gif_on_gif_sites_and_video_elsewhere():
    page = (
        '<meta property="og:image" content="https://media.tenor.com/a/cat.gif">'
        '<meta property="og:video" content="https://media.tenor.com/a/cat.mp4">'
        '<meta name="twitter:image" content="/thumb.jpg">'
    )
    assert meta_candidates(page, "https://tenor.com/view/x", prefer_gif=True)[0].endswith("cat.gif")
    first = meta_candidates(page, "https://tenor.com/view/x")
    assert first[0].endswith("cat.mp4")
    assert "https://tenor.com/thumb.jpg" in first
