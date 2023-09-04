import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from flask import Flask, request, Response
from bfxapi import Client, REST_HOST
from bfxapi.types import Notification, Order
from typing import List
from bfxapi.types import Wallet, Transfer, DepositAddress, LightningNetworkInvoice, Withdrawal, Notification, FundingOffer
from bfxapi.enums import FundingOfferType, Flag, OrderType
import time

app = Flask(__name__)
load_dotenv()

client1 = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
bfx = Client(
    rest_host=REST_HOST,
    api_key="",
    api_secret=""
)

try:
    response = client1.chat_postMessage(channel='#test-environment', text="Hello world!")
    assert response["message"]["text"] == "Hello world!"
except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    assert e.response["ok"] is False
    assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
    print(f"Got an error: {e.response['error']}")

def get_whitelisted_address_and_method(currency):
    whitelisted_addresses = {
        "XRP": ("rNxp4h8apvRis6mJf9Sh8C6iRxfrDWN7AV:304061413", "XRP"),
        "TRX": ("TPF63HGEKpwKo7dwvHDD1nRv6VvTgXKeHk", "TRX"),
        "USX": ("TPF63HGEKpwKo7dwvHDD1nRv6VvTgXKeHk", "TETHERUSX"),
        "USDTSOL": ("B3ZYXkFyBa2rrnFfpMtEftx3gJYhm3SL82moi2AdrwRA", "TETHERUSDTSOL"),
        "USDTXTZ": ("tz28Q3s1ibGY8AHdbXnuP9PBqVyDYywaSLgZ", "TETHERUSDTXTZ"),
        "USDTNEAR": ("c2b44c923c212e93600e0fe29265895a4b3fbaaf62b2518b7a4dd905d1e108cf", "TETHERUSDTNEAR"),
        "USDTDOT": ("12kYRnFXTYBTLuTKJFY51ZAc63S2Gra7fpcYxLEFhLfdW47o", "TETHERUSDTDOT"),
        "USDTPLY": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "TETHERUSDTPLY"),
        "USDTAVAX": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "TETHERUSDTAVAX"),
        "ARBETH": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "ARBETH"),
        "ARB": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "ARB"),
        # ... (other entries)
    }
    
    if currency in whitelisted_addresses:
        address, method = whitelisted_addresses[currency]
        return address, method
    else:
        return None, None

@ app.route('/withdraw', methods=['POST'])
def message_count():
    wallets: List[Wallet] = bfx.rest.auth.get_wallets()
    currency = request.form.get('text')
    print("Wallets", wallets, currency)
    receiver_address, wdmethod = get_whitelisted_address_and_method(currency)
    print("destination address:", receiver_address, "method:", wdmethod)
    D: Notification[Withdrawal] = bfx.rest.auth.submit_wallet_withdrawal(wallet="exchange", method=wdmethod, address=receiver_address, amount=5.0)
    print("Withdrawal:", D.text)
    response1 = client1.chat_postMessage(channel='#test-environment', text=f":ballot_box_with_check:  Withdrawal submitted => {D.status}\nMethod: {D.data.method}\nResponse:{D.text}")
    return Response(), 200

@ app.route('/generateaddress', methods=['POST'])
def generate_address():
    currency_default = 'USX'
    currency = request.form.get('text')
    if request.form.get('text') == 'None' or request.form.get('text') == '' or request.form.get('text') == 'none':
        currency = currency_default
    print(currency)
    currency, method = get_whitelisted_address_and_method(currency)
    print(method)
    B: Notification[DepositAddress] = bfx.rest.auth.get_deposit_address(wallet="exchange", method=method, renew=True)
    print("Deposit address:", B.data)
    responseaddress = client1.chat_postMessage(channel='#test-environment', text=f":ballot_box_with_check:  Deposit Address Generated => \nStatus: {B.text}\nDeposit Address: {B.data.address}")
    return Response(), 200

@ app.route('/testfunding', methods=['POST'])
def test_funding():
    notification: Notification[FundingOffer] = bfx.rest.auth.submit_funding_offer(
    type=FundingOfferType.LIMIT,
    symbol="fUST",
    amount=150.00,
    rate=0.069,
    period=2,
    flags=Flag.HIDDEN
    )
    offers = bfx.rest.auth.get_funding_offers(symbol="fUST")
    responseoffers = client1.chat_postMessage(channel='#test-environment', text=f":ballot_box_with_check: {offers}")
    cancel = bfx.rest.auth.cancel_all_funding_offers(currency="UST")
    offers_after_cancel = bfx.rest.auth.get_funding_offers(symbol="fUST")
    responseoffer_after_cancel = client1.chat_postMessage(channel='#test-environment', text=f":ballot_box_with_check: Cancellation update, active offers (by the way: if nothing is shown, it means I could cancel the funding offer) = {offers_after_cancel}")
    return Response(), 200

@ app.route('/testtrading', methods=['POST'])
def test_trading():
    submit_order_notification: Notification[Order] = bfx.rest.auth.submit_order(
        type=OrderType.EXCHANGE_LIMIT,
        symbol="tBTCUST",
        amount=0.0001,
        price='25000',
        flags=Flag.HIDDEN
    )
    orders = bfx.rest.auth.get_orders(symbol='tBTCUST')
    responseoffers = client1.chat_postMessage(channel='#test-environment', text=f":ballot_box_with_check: {orders}")
    return Response(), 200

@ app.route('/testplatform', methods=['POST'])
def general_test():
    test_trading()
    test_funding()
    generate_address()
    return Response(), 200

    

if __name__ == "__main__":
    app.run(debug=True)
