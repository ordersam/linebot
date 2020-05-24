from flask import Flask, render_template, request,abort
from scipy.misc import imsave, imread, imresize
import numpy as np
import keras.models
import re
import base64
import tempfile
import sys 
import os
sys.path.append(os.path.abspath("./model"))
from load import *

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)
global model, graph
model, graph = init()
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/predict/', methods=['GET','POST'])
def predict():
    # get data from drawing canvas and save as image
    parseImage(request.get_data())

    # read parsed image back in 8-bit, black and white mode (L)
    x = imread('output.png', mode='L')
    x = np.invert(x)
    x = imresize(x,(28,28))

    # reshape image data for use in neural network
    x = x.reshape(1,28,28,1)
    with graph.as_default():
        out = model.predict(x)
        print('1',out)
        print('2',np.argmax(out, axis=1))
        response = np.array_str(np.argmax(out, axis=1))
        print(response)
        return response 
    
def parseImage(imgData):
    # parse canvas bytes and save as output.png
    imgstr = re.search(b'base64,(.*)', imgData).group(1)
    with open('output.png','wb') as output:
        output.write(base64.decodebytes(imgstr))

# line
YOUR_CHANNEL_ACCESS_TOKEN = ''
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
YOUR_CHANNEL_SECRET = ''
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


# 使用者輸入文字
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if msg == '辨識範例':
        url1 = url2 = 'https://i.imgur.com/ERCZGCz.png'
        # 辨識
        x = imread(os.path.join('static', 'sample.png'), mode='L')
        x = np.invert(x)
        x = imresize(x, (28, 28))
        # reshape image data for use in neural network
        x = x.reshape(1, 28, 28, 1)
        with graph.as_default():
            out = model.predict(x)
            print('1', out)
            print('2', np.argmax(out, axis=1))
            response = np.array_str(np.argmax(out, axis=1))
            print(response)
            #return response
        line_bot_api.reply_message(event.reply_token, 
                           [ImageSendMessage(original_content_url=url1, preview_image_url=url2), 
                            TextSendMessage(text='-圖片轉文字為-'), TextSendMessage(text=response)])
    else:
        carousel_template_message = TemplateSendMessage(
            alt_text='Carousel template', 
            template=CarouselTemplate(
                columns=[CarouselColumn(thumbnail_image_url='https://i.imgur.com/pHX1jsZ.jpg', 
                                        title='歡迎加入寶寶mnist手寫辨識', text='請上傳單一數字圖檔以供辨識', 
                                        actions=[URIAction(label='網頁版即時繪製辨識', uri='https://ordersamlinemnist.herokuapp.com'), 
                                                 MessageAction(label='辨識範例', text='辨識範例', 
                                                               image_url='https://i.imgur.com/tqUlzuS.png')])]))
        line_bot_api.reply_message(event.reply_token, carousel_template_message)

# Other Message Type
@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return
 
    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '.' + ext
    dist_name = os.path.basename(dist_path)
    os.rename(tempfile_path, dist_path)
    getImg=request.host_url + os.path.join('static', dist_name)

    #image = Image.open(os.path.join('static', dist_name))
    #code = pytesseract.image_to_string(image)
    

    # read parsed image back in 8-bit, black and white mode (L)
    x = imread(os.path.join('static', dist_name), mode='L')
    x = np.invert(x)
    x = imresize(x,(28,28))

    # reshape image data for use in neural network
    x = x.reshape(1,28,28,1)
    with graph.as_default():
        out = model.predict(x)
        print('1',out)
        print('2',np.argmax(out, axis=1))
        response = np.array_str(np.argmax(out, axis=1))
        print(response)
        #return response 
    
    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(text='-圖片轉文字為-'),
            TextSendMessage(text=response)            
        ])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)