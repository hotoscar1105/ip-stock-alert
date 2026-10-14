"""Offline test: fake Apple + fake CallMeBot, run the real script twice via --once."""
import os, sys, json, importlib, types
os.environ.update(WHATSAPP_PHONE="+85200000000", TEXTMEBOT_APIKEY="k", STATE_FILE="/tmp/_st.json", RUN_SECONDS="0")
if os.path.exists("/tmp/_st.json"): os.remove("/tmp/_st.json")
import requests
sent=[]; stock={"open":False,"avail":False}
class R:
    def __init__(s,code=200,text="",js=None): s.status_code=code;s.text=text;s._j=js;s.ok=code<400
    def json(s): return s._j
    def raise_for_status(s):
        if s.status_code>=400: raise requests.HTTPError(str(s.status_code))
def fake_get(url,params=None,**k):
    if "textmebot" in url: sent.append(params["text"]); assert params["recipient"]=="+85200000000"; return R()
    if "buy-iphone" in url: return R(text="MK2D4ZA/A MK2E4ZA/A")
    if "fulfillment" in url:
        if "pl" not in (params or {}):
            return R(js={"body":{"content":{"deliveryMessage":{params["parts.0"]:{"isBuyable":stock.get("buy",False),"regular":{"deliveryOptions":[{"displayName":"Delivers Fri 23 Oct"}]}}}}}})
        if not stock["open"]: return R(541)
        p=params["parts.0"]; ok=stock["avail"] and p=="MK2D4ZA/A"
        return R(js={"body":{"content":{"pickupMessage":{"stores":[{"storeName":"ifc mall","partsAvailability":{p:{"pickupDisplay":"available" if ok else "unavailable","messageTypes":{"regular":{"storePickupProductTitle":"iPhone Duo 1TB Night Sky"}}}}}]}}}})
requests.get=fake_get
import time; time.sleep=lambda *_:None
sys.argv=["x","--once"]
import stock_alert as m
def run(): m.main()
run(); assert len(sent)==1 and "started" in sent[0], sent        # start msg only
run(); assert len(sent)==1, sent                                  # pickup closed: silent
stock["open"]=True; run(); assert "已開放" in sent[-1], sent       # pickup opens
n=len(sent); stock["avail"]=True; run(); assert "IN STOCK" in sent[-1] and len(sent)==n+1
n=len(sent); run(); assert len(sent)==n, "must not repeat alert"  # dedupe via state file
n=len(sent); stock["buy"]=True; run(); assert any("ORDERABLE" in x for x in sent[n:]), sent
n=len(sent); run(); assert len(sent)==n
print("OFFLINE TEST PASSED:", len(sent), "messages"); print(sent[-1])
