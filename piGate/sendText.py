from twilio.rest import Client
import threading
import time

account = "AC61f8be00513231ed9b5301e3593d87eb"
token = "fee568ebe5a55fda904670a0fbcc60f1"

class sendText(object):
    stopTimeS = 0
    def  __init__(self):
        pass
        
    def sendText(self, body, pause=0, durationS = 1):
        # Sends a text to my phone number using twilio
        client = Client(account, token)
        def doit():
            now = time.time()
            self.stopTimeS = now+durationS
            while now < self.stopTimeS:
                #client.messages.create(to="8312957882", from_="8317775381", body=body)
                print "Send text"
                time.sleep(pause)
                now = time.time()
        threading.Thread(target=doit).start()
