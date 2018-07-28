import sys
import os
from PIL import ImageFont

from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.core import cmdline, error


def get_device(actual_args=None):
    """
    Create device from command-line arguments and return it.
    """
    if actual_args is None:
        actual_args = sys.argv[1:]
    parser = cmdline.create_parser(description='luma.examples arguments')
    args = parser.parse_args(actual_args)

    if args.config:
        # load config from file
        config = cmdline.load_config(args.config)
        args = parser.parse_args(config + actual_args)

    print(display_settings(args))

    # create device
    try:
        device = cmdline.create_device(args)
    except error.Error as e:
        parser.error(e)

    return device

def display_settings(args):
    """
    Display a short summary of the settings.

    :rtype: str
    """
    iface = ''
    display_types = cmdline.get_display_types()
    if args.display not in display_types['emulator']:
        iface = 'Interface: {}\n'.format(args.interface)

    lib_name = cmdline.get_library_for_display_type(args.display)
    if lib_name is not None:
        lib_version = cmdline.get_library_version(lib_name)
    else:
        lib_name = lib_version = 'unknown'

    import luma.core
    version = 'luma.{} {} (luma.core {})'.format(
        lib_name, lib_version, luma.core.__version__)

    return 'Version: {}\nDisplay: {}\n{}Dimensions: {} x {}\n{}'.format(
        version, args.display, iface, args.width, args.height, '-' * 60)
        
def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    font_path = os.path.join('luma.oled/examples/luma.examples/examples/fonts',name)
    return ImageFont.truetype(font_path, size)

    
device = get_device()
regulator = framerate_regulator(fps=1)
font = make_font("fontawesome-webfont.ttf", device.height - 10)

while 1:
    with regulator:
        code = "B"
        with canvas(device) as draw:
            print "draw"
            w, h = draw.textsize(text=code, font=font)
            left = (device.width - w) / 2
            top = (device.height - h) / 2
            draw.text((left, top), text=code, font=font, fill="white")
