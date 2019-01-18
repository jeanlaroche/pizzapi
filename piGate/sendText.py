from twilio.rest import Client
import threading
import time

account = "AC61f8be00513231ed9b5301e3593d87eb"
token = "fee568ebe5a55fda904670a0fbcc60f1"


def sendText(body,nRepeat=1,pause=0):
    # Sends a text to my phone number using twilio
    client = Client(account, token)
    def doit():
        for i in range(nRepeat):
            client.messages.create(to="8312957882", from_="8317775381", body=body)
            time.sleep(pause)
    threading.Thread(target=doit).start()
