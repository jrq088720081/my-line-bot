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
import google.generativeai as genai

app = Flask(__name__)

configuration = Configuration(access_token=os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# 設定 Gemini AI
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# 系統提示：給 AI 設定身份與背景知識
SYSTEM_PROMPT = """你是「我的助理」，一個專為中油雇員電器類國家考試設計的 LINE 學習助理。

你的主要任務：
1. 回答電工原理、電機機械相關的考試問題
2. 提供複習建議與學習方向
3. 解釋電學概念，讓使用者容易理解
4. 用繁體中文回答，語氣親切友善

考試範圍參考（10週進度）：
- 第1週：電工原理 p.1~p.15｜電的基本概念＋電阻＋填充題
- 第2週：電工原理 p.15~p.38｜直流分析：KVL、串並聯、填充題
- 第3週：電工原理 p.65~p.71｜電容與電感＋填充題
- 第4週：電工原理 p.90~p.97｜交流分析＋功因改善＋填充題
- 第5週：電工原理 p.107~p.109｜諧振電路（串聯＋並聯）＋填充題
- 第6週：電工原理 p.114~p.115｜三相電路＋填充題
- 第7週：電機機械 p.32~p.53｜變壓器全章＋填充題
- 第8週：電機機械 p.53~p.70｜三相感應機全章＋填充題
- 第9週：電機機械 p.1~p.31｜直流機：發電機＋電動機＋效率＋填充題
- 第10週：電機機械 p.71~p.75｜同步機全章＋填充題

回答原則：
- 回答要簡潔清楚，適合在手機 LINE 上閱讀
- 若是計算題，列出公式與步驟
- 適時給予鼓勵，幫助使用者建立信心
- 若問題與考試無關，也可以友善地回應日常對話
"""

# 保活功能
RENDER_URL = os.environ.get('RENDER_URL', 'https://my-line-bot-f984.onrender.com')

def keep_alive():
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(RENDER_URL + '/ping')
        except Exception:
            pass

@app.route("/ping", methods=['GET'])
def ping():
    return 'pong', 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text.strip()

    try:
        # 把使用者訊息交給 Gemini AI 回答
        response = model.generate_content(
            SYSTEM_PROMPT + "\n\n使用者說：" + user_msg
        )
        reply = response.text
    except Exception as e:
        reply = f"抱歉，AI 暫時無法回應，請稍後再試。\n（錯誤：{str(e)[:50]}）"

    # LINE 單則訊息上限 5000 字
    if len(reply) > 4000:
        reply = reply[:4000] + "...\n（回答較長，已截斷）"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

if __name__ == "__main__":
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
