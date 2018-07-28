from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1325, ssd1331, sh1106
from PIL import ImageFont, ImageDraw
import os

# rev.1 users set port=0
# substitute spi(device=0, port=0) below if using that interface
serial = i2c(port=1, address=0x3C)

# See https://luma-oled.readthedocs.io/en/latest/python-usage.html
# substitute ssd1331(...) or sh1106(...) below if using that device
device = ssd1306(serial)

# draw.text is here: https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html#module-PIL.ImageDraw
for dirpath, dirnames, filenames in os.walk('/usr/share/fonts/truetype'):
    for file in filenames:
        if not '.ttf' in file: continue
        fontName = os.path.join(dirpath,file)
        print fontName
        with canvas(device) as draw:
            #font = ImageFont.load("arial.pil")
            # Lots of fonts here: /usr/share/fonts/truetype
            
            font =  ImageFont.truetype(font=fontName, size=10, index=0, encoding='', layout_engine=None)
            #draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((30, 40), "Temp = 82F", fill="white",font=font)
        raw_input("asdf")
