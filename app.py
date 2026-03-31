from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
import threading
import time
import urllib.request

app = Flask(__name__)

# 從環境變數讀取金鑰（不要直接寫在程式碼裡）
configuration = Configuration(access_token=os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# ── 保活功能：每 10 分鐘自動 ping 自己，防止 Render 睡眠 ──
RENDER_URL = os.environ.get('RENDER_URL', 'https://my-line-bot-f984.onrender.com')

def keep_alive():
    while True:
        time.sleep(600)  # 等 10 分鐘
        try:
            urllib.request.urlopen(RENDER_URL + '/ping')
        except Exception:
            pass  # 即使失敗也不影響主程式

@app.route("/ping", methods=['GET'])
def ping():
    return 'pong', 200

# ── 複習提示內容 ──────────────────────────────────────────
STUDY_TOPICS = {
    "第1週": "電工原理 p.1~p.15｜電的基本概念＋電阻＋填充題",
    "第2週": "電工原理 p.15~p.38｜直流分析：KVL、串並聯、填充題",
    "第3週": "電工原理 p.65~p.71｜電容與電感＋填充題",
    "第4週": "電工原理 p.90~p.97｜交流分析＋功因改善＋填充題",
    "第5週": "電工原理 p.107~p.109｜諧振電路（串聯＋並聯）＋填充題",
    "第6週": "電工原理 p.114~p.115｜三相電路＋填充題",
    "第7週": "電機機械 p.32~p.53｜變壓器全章＋填充題",
    "第8週": "電機機械 p.53~p.70｜三相感應機全章＋填充題",
    "第9週": "電機機械 p.1~p.31｜直流機：發電機＋電動機＋效率＋填充題",
    "第10週": "電機機械 p.71~p.75｜同步機全章＋填充題",
}

HELP_MSG = """🤖 我的助理指令說明

📚 查詢複習內容：
  輸入「第1週」～「第10週」查看該週課程

🆘 其他指令：
  「說明」或「help」→ 顯示此說明
  「你好」→ 打招呼

直接傳訊息我也會回應你喔！"""

# ── Webhook 接收端點 ──────────────────────────────────────
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ── 訊息處理邏輯 ──────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text.strip()

    # 判斷回覆內容
    if user_msg in STUDY_TOPICS:
        reply = f"📖 {user_msg} 複習內容：\n\n{STUDY_TOPICS[user_msg]}\n\n加油！考試必上！💪"
    elif user_msg in ["說明", "help", "Help", "HELP"]:
        reply = HELP_MSG
    elif any(w in user_msg for w in ["你好", "哈囉", "hi", "Hi", "hello", "Hello"]):
        reply = "你好！我是你的考試複習助理 📚\n輸入「說明」看我能幫你做什麼！"
    else:
        reply = f"你說：「{user_msg}」\n\n輸入「說明」查看所有指令 📋"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

# ── 啟動伺服器 ────────────────────────────────────────────
if __name__ == "__main__":
    # 啟動保活背景執行緒
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # 用 gunicorn 啟動時也要啟動保活
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
