"""Create a disposable geometric PNG for manual browser brush/depth QA."""
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(tempfile.mkdtemp(prefix='showcase-motion-qa-'))
image = Image.new('RGBA', (400, 600), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.ellipse((130, 40, 270, 180), fill='#a6eaff')
draw.rounded_rectangle((100, 180, 300, 580), radius=35, fill='#204967')
for y in range(220, 560, 25):
    draw.line((110, y, 290, y), fill='#52d5ff', width=5)
path = folder / 'character.png'
image.save(path)
print(path)
