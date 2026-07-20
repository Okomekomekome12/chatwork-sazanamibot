from flask import Flask , jsonify , request , render_template
from yt_stream import get_stream_links , list_formats
from commands import help , link
import chatwork
import os

app       = Flask(__name__)
API_TOKEN = os.getenv("API_TOKEN")
bot_id    = 11156582
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/webhook" , methods=["POST"])
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
    
    print(f"\n=== Webhook受信 ===")
    print(f"account_id: {account_id}")
    print(f"body: {body}")
    print(f"一致?: {int(account_id) == bot_id}")
    print(f"message_id : {message_id}")
    print(f"room_id : {room_id}")
    print(f"==================\n")

    if int(account_id) == bot_id:
        print("bot垢やね")

    if body == "/help-sazanami":
        help.help(cw)

    elif body == "/live?":
        cw.messagesend("[info][title]さざなみ生存確認[/title]圧　倒　的　生　き　て　ま　す　（？）[/info]")
    
    elif body == "/update":
        cw.messagesend("[info]さざなみbotV-1作成[/info]")

    elif body and body.count("削除") >= 1:
            target = body.split("to=")[1].split("]")[0]  
            delete_room_id , delete_message_id = target.split("-")
            deleter_room_id = delete_room_id
            deleter_message_id = delete_message_id
            print(deleter_room_id,deleter_message_id)
            cw.delete_message(deleter_message_id)
    elif body == "/link":
        link.link(cw)
    elif body.count("/youtube") >= 1:
        stream_link = body.split()[1]
        print(stream_link)
        info = get_stream_links(stream_link)
        print(info.url)
        cw.messagesend(f"[info][title]{stream_link}の統合ストリーム[/title]{info.url}")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
     port = int(os.environ.get("PORT",8080))
     app.run(host="0.0.0.0" , port=port)