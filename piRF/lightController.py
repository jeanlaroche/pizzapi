import pigpio
from _433 import tx
import time


TX_GPIO = 17
# Codes for our light remote. > 0 means turn on, < 0 means turn off
codesLivRoom = {1:5510451,-1:5510460,2:5510595,-2:5510604,3:5510915,-3:5510924,4:5512451,-4:5512460,5:5518595,-5:5518604}
codesBedRoom = {1:283955,-1:283964,2:284099,-2:284108,3:284419,-3:284428,4:285955,-4:285964,5:292099,-5:292108
}
codes = codesLivRoom
codes = codesBedRoom

class lightController(object):

    transmitter = None
    pi = None
    
    def __init__(self):
        self.pi = pigpio.pi() # Connect to local Pi.
        self.transmitter = tx(self.pi,gpio = TX_GPIO, repeats=6)
    
    def turnLigthOnOff(self, lightNum, onOff):
        if lightNum == 6:
            for ii in range(1,6):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        code = codes[lightNum] if onOff == 1 else codes[-lightNum]
        self.transmitter.send(code)

if __name__ == "__main__":
    lc = lightController()
    
    while 1:
        a = raw_input('Command ->[]')
        a = int(a)
        lc.turnLigthOnOff(abs(a),a>0)
        
