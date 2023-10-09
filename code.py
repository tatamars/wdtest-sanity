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

#try:
#    response = client1.chat_postMessage(channel='#test-environment', text="INFO: The bot has been restarted.")
#    assert response["message"]["text"] == "INFO: The bot has been restarted."
#except SlackApiError as e:
#    # You will get a SlackApiError if "ok" is False
#    assert e.response["ok"] is False
#    assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
#    print(f"Got an error: {e.response['error']}")

def get_whitelisted_address_and_method(currency):
    whitelisted_addresses = {
        "ETH": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "ETHEREUM", "ETH", "tETHUSD"),        
        "XRP": ("rNxp4h8apvRis6mJf9Sh8C6iRxfrDWN7AV:304061413", "XRP", "XRP", "tXRPUSD"),
        "TRX": ("TPF63HGEKpwKo7dwvHDD1nRv6VvTgXKeHk", "TRX", "TRX", "tTRXUSD"),
        "USX": ("TPF63HGEKpwKo7dwvHDD1nRv6VvTgXKeHk", "TETHERUSX", "UST", "tUSTUSD"),
        "USDTSOL": ("B3ZYXkFyBa2rrnFfpMtEftx3gJYhm3SL82moi2AdrwRA", "TETHERUSDTSOL", "UST", "tUSTUSD"),
        "USDTXTZ": ("tz28Q3s1ibGY8AHdbXnuP9PBqVyDYywaSLgZ", "TETHERUSDTXTZ", "UST", "tUSTUSD"),
        "USDTNEAR": ("c2b44c923c212e93600e0fe29265895a4b3fbaaf62b2518b7a4dd905d1e108cf", "TETHERUSDTNEAR", "UST", "tUSTUSD"),
        "USDTDOT": ("12kYRnFXTYBTLuTKJFY51ZAc63S2Gra7fpcYxLEFhLfdW47o", "TETHERUSDTDOT", "UST", "tUSTUSD"),
        "USDTPLY": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "TETHERUSDTPLY", "UST", "tUSTUSD"),
        "USDTAVAX": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "TETHERUSDTAVAX", "UST", "tUSTUSD"),
        "ARBETH": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "ARBETH", "ARBETH", "tUSTUSD"),
        "ARB": ("0x256fb9a6b489010c9b916e7456049ae6807fc26a", "ARB", "ARB", "tUSTUSD"),
        # ... (other entries)
    }
    
    if currency in whitelisted_addresses:
        address, method, apisymbol, tradingsymbol = whitelisted_addresses[currency]
        return address, method, apisymbol, tradingsymbol
    else:
        return None, None, None, None

def checkbalance(target_currency):
    wallets: List[Wallet] = bfx.rest.auth.get_wallets()
    for wallet in wallets:
        if wallet.currency == target_currency:
            print(wallet.currency, wallet.available_balance)
            return wallet.available_balance
    return
tr = checkbalance('ETH')
print(tr)

def checkminimumwithdrawal(target_currency):
    a, b, c, d = get_whitelisted_address_and_method(target_currency)
    response = bfx.rest.public.get_t_ticker(d)
    minimumwithdrawal = 6/response.ask
    print("Minimum Withdrawal Amount:", target_currency, minimumwithdrawal)
    return minimumwithdrawal
checkminimumwithdrawal("ETH")

@ app.route('/withdraw', methods=['POST'])
def testwithdraw():
    wallets: List[Wallet] = bfx.rest.auth.get_wallets()
    currency = request.form.get('text')
    print("Wallets", wallets, currency)
    receiver_address, wdmethod, apisymbol, tradingsymbol = get_whitelisted_address_and_method(currency)
    print("destination address:", receiver_address, "method:", wdmethod)
    minimumwithdrawal = checkminimumwithdrawal(currency)
    currencybalance = checkbalance(apisymbol)
    if currencybalance == None:
        currencybalance = 0
        diff = (minimumwithdrawal - currencybalance)*1.1
        bfx.rest.auth.submit_order(type=OrderType.EXCHANGE_MARKET, symbol=tradingsymbol, amount=diff, price=None, flags=Flag.HIDDEN)
    elif currencybalance < minimumwithdrawal:
        diff = (minimumwithdrawal - currencybalance)*1.1
        bfx.rest.auth.submit_order(type=OrderType.EXCHANGE_MARKET, symbol=tradingsymbol, amount=diff, price=None, flags=Flag.HIDDEN)
    D: Notification[Withdrawal] = bfx.rest.auth.submit_wallet_withdrawal(wallet="exchange", method=wdmethod, address=receiver_address, amount=minimumwithdrawal)
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
    currency2, method, uisymbol, tradingsymbol = get_whitelisted_address_and_method(currency)
    if method == "none":
        method = currency
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
