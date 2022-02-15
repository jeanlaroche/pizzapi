import urllib.request as ur
import json
import pigpio
import time

def turnOff():
    print("TURNING OFF")
    pi = pigpio.pi()
    jj = []
    for ii in [14,15]:
        try:
            pi.set_mode(ii, pigpio.OUTPUT)
            pi.write(ii, 0)
            #print(f"Turned {ii} off")
            jj.append(ii)
        except:
            pass
    pi.stop()
    print(f"{time.ctime(time.time())}: Turned off these GPIOS:",jj)


def runSafety():
    # Checks that pizza server is alive and well, and otherwise turns all GPIOs off
    try:
        f = ur.urlopen(" http://localhost:8080/alive",timeout=2)
        data = json.loads(f.read())
        if data['isAlive']: return
        turnOff()
    except:
        turnOff()


if __name__ == '__main__':
    runSafety()
