import unittest

from steam_catalog import _normalise_showcase, _profile_customizations


class ShowcaseAvatarFilterTest(unittest.TestCase):
    def test_workshop_keeps_five_tiles_in_order_not_author_avatar(self):
        tiles = [f'https://steamuserimages-a.akamaihd.net/ugc/{i}/tile.jpg' for i in range(5)]
        for host in ('avatars.steamstatic.com', 'avatars.akamai.steamstatic.com',
                     'avatars.cloudflare.steamstatic.com', 'avatars.fastly.steamstatic.com'):
            with self.subTest(host=host):
                markup = '<div class="profile_customization"><div class="profile_customization_header">Workshop Showcase</div>'
                markup += f'<a class="playerAvatar"><img src="https://{host}/author.jpg"></a>'
                markup += ''.join(f'<img src="{url}">' for url in tiles) + '</div>'
                parsed = _profile_customizations(markup)['showcases'][0]
                self.assertEqual(_normalise_showcase(parsed)['images'], tiles)

    def test_regular_artwork_is_preserved(self):
        images = ['https://steamuserimages-a.akamaihd.net/ugc/1/art.jpg',
                  'https://steamuserimages-a.akamaihd.net/ugc/2/side.jpg']
        self.assertEqual(_normalise_showcase({'type': 'artwork', 'images': images})['images'], images)


if __name__ == '__main__':
    unittest.main()
