from twilio.rest import Client
import threading
import time
import logging
# If you get the infamous AttributeError: 'module' object has no attribute 'X509_up_ref' error
# uninstall pyOpenSSL 

account = "AC61f8be00513231ed9b5301e3593d87eb"
token = "fee568ebe5a55fda904670a0fbcc60f1"

class textSender(object):
    stopTimeS = 0
    isActive = 0
    def  __init__(self):
        pass
        
    def sendText(self, body, pause=0, durationS = 1):
        # Sends a text to my phone number using twilio
        client = Client(account, token)
        def doit():
            now = time.time()
            self.stopTimeS = now+durationS
            self.body = body
            # If already active, simply adjust the end time, and return.
            if self.isActive and now < self.stopTimeS: return
            self.isActive = 1
            while now < self.stopTimeS:
                client.messages.create(to="8312957882", from_="8317775381", body=self.body)
                logging.info(self.body)
                time.sleep(pause)
                now = time.time()
            self.isActive = 0
        threading.Thread(target=doit).start()
