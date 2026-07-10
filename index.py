from flask import Flask , jsonify , request , render_template
from yt_stream import get_stream_links , list_formats
from commands import *
import chatwork
import os

app       = Flask(__name__)
API_TOKEN = os.getenv("API_TOKEN")
bot_id    = 11156582
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/" , methods=["POST"])
def webhook():
    data = request.json
    account_id = chatwork.webhook_get_account_id(data)
    body       = chatwork.webhook_get_message(data)
    message_id = chatwork.webhook_get_message_id(data)
    room_id    = chatwork.webhook_get_roomid(data)  

    cw       = chatwork.setup(room_id,API_TOKEN)
    cw2      = chatwork.setup(420107748,API_TOKEN)
    log_room = chatwork.setup(418992889,API_TOKEN)
    role     = cw.is_admin(account_id)

    if int(account_id) == bot_id:
        print("bot垢やね")

    if body == "/help-sazanami":
        help()

    elif body == "/live?":
        cw.messagesend("[info][title]さざなみ生存確認[/title]圧　倒　的　生　き　て　ま　す　（？）")
    
    elif body == "/update":
        cw.messagesend("[info]さざなみbotV-1作成[/info]")
    return jsonify({"status": "ok"}), 200