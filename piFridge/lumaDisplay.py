from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1325, ssd1331, sh1106
from PIL import ImageFont, ImageDraw
import os
import time

class Luma(object):
    newLine = 16
    
    def __init__(self,size=16):
        # rev.1 users set port=0
        # substitute spi(device=0, port=0) below if using that interface
        self.serial = i2c(port=1, address=0x3C)
        # See https://luma-oled.readthedocs.io/en/latest/python-usage.html
        # substitute ssd1331(...) or sh1106(...) below if using that device
        self.device = ssd1306(self.serial)
        self.fontPath = '/usr/share/fonts/truetype/ttf-bitstream-vera/VeraMoBI.ttf'
        self.font =  ImageFont.truetype(font=self.fontPath, size=size, index=0, encoding='', layout_engine=None)
    
    def printText(self,text):
        with canvas(self.device) as draw:
            for ii,txt in enumerate(text):
                draw.text((0,ii*self.newLine),txt,fill="white",font=self.font)
            
if __name__ == "__main__":
    luma = Luma()
    ii = 0
    while 1:
        Format = "%H:%M:%S"
        text = ['Temp 102F','Waiting',time.strftime(Format,time.localtime())+" {}".format(ii)]
        luma.printText(text)
        ii += 1

def foo():
    # draw.text is here: https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html#module-PIL.ImageDraw
    while 1:
        for dirpath, dirnames, filenames in os.walk('/usr/share/fonts/truetype'):
            for file in filenames:
                if not '.ttf' in file: continue
                if 'lyx' in dirpath: continue
                fontName = os.path.join(dirpath,file)
                print fontName
                for temp in range(80,120):
                    with canvas(device) as draw:
                        #font = ImageFont.load("arial.pil")
                        # Lots of fonts here: /usr/share/fonts/truetype
                        
                        font =  ImageFont.truetype(font=fontName, size=16, index=0, encoding='', layout_engine=None)
                        #draw.rectangle(device.bounding_box, outline="white", fill="black")
                        offset=16
                        # draw.text((0, 0), "{}F".format(temp), fill="white",font=font)
                        draw.text((0, 0), "Target = {}F".format(temp), fill="white",font=font)
                        draw.text((0, offset), "Temp = 82F", fill="white",font=font)
                        draw.text((0, 2*offset), "Time: 1:32:24", fill="white",font=font)
                        Format = "%H:%M:%S"
                        draw.text((0, 3*offset), time.strftime(Format,time.localtime()), fill="white",font=font)
                time.sleep(0)
