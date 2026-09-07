import io
import unittest

from PIL import Image

import processor
import steam_catalog


class WorkshopOutlineTests(unittest.TestCase):
    def test_static_outline_is_drawn_inside_every_panel(self):
        source = Image.new("RGB", (750, 40), "#112233")
        result = processor.process_image_workshop(
            source, outline_width=2, outline_color="#ffffff"
        )
        for index in range(1, 6):
            with Image.open(io.BytesIO(result[f"part_{index}.png"])) as part:
                rgba = part.convert("RGBA")
                self.assertEqual(rgba.size, (150, 40))
                self.assertEqual(rgba.getpixel((0, 0))[:3], (255, 255, 255))
                self.assertEqual(rgba.getpixel((2, 2))[:3], (17, 34, 51))

    def test_points_shop_link_targets_the_exact_reward(self):
        item = steam_catalog._points_item(
            {
                "appid": 730,
                "defid": 1047,
                "point_cost": 2000,
                "community_item_data": {
                    "item_title": "Example",
                    "item_image_large": "abc.jpg",
                },
            },
            "frame",
        )
        self.assertEqual(
            item["buy_url"],
            "https://store.steampowered.com/points/shop/app/730/reward/1047",
        )


if __name__ == "__main__":
    unittest.main()
