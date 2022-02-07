# TEST OF THE mcp9600 library
#sudo pip3 install mcp9600
#sudo pip3 install smbus
#sudo apt-get install i2ctools
# Use sudo i2cdetect -y 1 to see the devices

import mcp9600
import time

class Temps():
    # Small wrapper around MCP9600
    def __init__(self):
        self.top = mcp9600.MCP9600(0x67)
        time.sleep(.1)
        self.bottom = mcp9600.MCP9600(0x65)
        self.top.set_thermocouple_type('K')
        self.bottom.set_thermocouple_type('K')

    def getTemps(self):
        try:
            temp_m1 = self.top.get_hot_junction_temperature()
            temp_m2 = self.bottom.get_hot_junction_temperature()
        except Exception as e:
            print(f"Could not read temp: {e}")
            return 0,0
        return round(temp_m1,1),round(temp_m2,1)

if __name__ == "__main__":
    T = Temps()
    while 1:
        t_1,t_2 = T.getTemps()
        print(f"Top: {t_1} Bottom: {t_2}")
        time.sleep(1)

# top = mcp9600.MCP9600(0x67)
# time.sleep(.1)
# bottom = mcp9600.MCP9600(0x65)
# top.set_thermocouple_type('K')
# bottom.set_thermocouple_type('K')
# print(f"{top.get_thermocouple_type()}")
# print(f"{bottom.get_thermocouple_type()}")
# while 1:
#     print(f"{top.get_cold_junction_temperature()}, {top.get_hot_junction_temperature()}, {top.get_temperature_delta()}")
#     print(f"{bottom.get_cold_junction_temperature()}, {bottom.get_hot_junction_temperature()}, {bottom.get_temperature_delta()}\n______")
#     time.sleep(.5)