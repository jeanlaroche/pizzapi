import urllib.request as ur
import json
import pigpio
import time

def turnOff():
    print("TURNING OFF")
    pi = pigpio.pi()
    jj = []
    for ii in range(28):
        try:
            pi.set_mode(ii, pigpio.OUTPUT)
            pi.write(ii, 0)
            #print(f"Turned {ii} off")
            jj.append(ii)
        except:
            pass
    pi.stop()
    print(f"Turned off these GPIOS:",jj)


def runSafety():
    # Checks that pizza server is alive and well, and otherwise turns all GPIOs off
    try:
        f = ur.urlopen(" http://localhost:8080/alive")
        data = json.loads(f.read())
        if data['isAlive']: return
        turnOff()
    except:
        turnOff()


if __name__ == '__main__':
    while 1:
        runSafety()
        time.sleep(1)
