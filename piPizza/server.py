from BaseClasses.baseServer import Server
from ReadTemps import Temps
import pigpio
import time

from BaseClasses.utils import runThreaded
from flask import Flask

app = Flask(__name__)

RelayTop    = 14
RelayBottom = 15

class PizzaServer(Server):
    def __init__(self):
        super().__init__()
        self.Temps = Temps()
        self.pi = pigpio.pi()  # Connect to local Pi.
        self.pi.set_mode(RelayTop, pigpio.OUTPUT)
        self.pi.set_mode(RelayBottom, pigpio.OUTPUT)
        self.pi.write(RelayTop, 0)
        self.pi.write(RelayBottom, 0)
        runThreaded(self.processLoop)

    def __delete__(self):
        self.pi.stop()

    def processLoop(self):
        while 1:
            pass
            time.sleep(0.1)

@app.route('/favicon.ico')
def favicon():
    return server.favicon()


@app.route("/reboot")
def reboot():
    server.reboot()
    return ('', 204)


@app.route('/kg')
def kg():
    server.kg()
    return ('', 204)


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return server.Index()


@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1, param2):
    return jsonify(param1=param1, param2=param2)
if __name__ == "__main__":
    server = PizzaServer()

    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
