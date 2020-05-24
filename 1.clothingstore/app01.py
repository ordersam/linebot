import os
from flask import *
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore, storage
import MySQLdb
import random
from flask_session import Session
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage,URIAction,
    LocationMessage,
    ImagemapSendMessage,
    ImageCarouselColumn,
    ImageCarouselTemplate,Video,ExternalLink,
    ConfirmTemplate,PostbackAction,MessageAction,
    PostbackTemplateAction,FlexSendMessage,
    TemplateSendMessage, ButtonsTemplate, URITemplateAction,CarouselColumn,
    BaseSize,URIImagemapAction,MessageImagemapAction,ImagemapArea,CarouselTemplate)

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = './static/'
# Firebase Storage
cred = credentials.Certificate('serviceAccount.json')     # 放自己的憑證檔
firebase_admin.initialize_app(cred, {'storageBucket': '圖片儲存URL'})
app01 = firebase_admin.initialize_app(cred, {'storageBucket': '圖片儲存URL',}, 
                                      name='storage')
# 登入狀態管理
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
app.config['SECRET_KEY'] = os.urandom(24)
from flask_session import Session
app.config['SESSION_TYPE'] = 'filesystem'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template("index.html")
    # POST
    user_id = request.form['user_id']
        # 登入成功
    if (user_id in users) and (request.form['password'] == users[user_id]['password']):
        user = User()
        user.id = user_id
        login_user(user)
        # 訊息閃現flask.flash()
            # 前端取值
                # {% with messages = get_flashed_messages() %}
                #     {% if messages %}
                #         {% for message in messages %}
                #             {{ message }}
                #         {% endfor %}
                #     {% endif %}
                # {% endwith %}
        flash(f'{user_id}！歡迎您！')
        return redirect(url_for('from_start'))
        # 登入失敗
    flash('登入失敗,請重新輸入')
    return render_template('index.html')
# 1.flask_login
    # 使用者帳號密碼
users = {'abc': {'password': '1234'}}
    # (1)初始化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = 'login'
login_manager.login_message = '網頁不存在~ERROR'
    # (2)繼承 UserMixin
class User(UserMixin):
    pass
    # (3)設置call back function(web登入)
@login_manager.user_loader
def user_loader(user_id):
    if user_id not in users:
        return
    user = User()
    user.id = user_id
    return user
    # (3)設置call back function(API登入)
@login_manager.request_loader
def request_loader(request):
    user_id = request.form.get('user_id')
    if user_id not in users:
        return
    user = User()
    user.id = user_id
    user.is_authenticated = request.form['password'] == users[user_id]['password']
    return user

# 登入
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("index.html")
    # POST
    user_id = request.form['user_id']
    if (user_id in users) and (request.form['password'] == users[user_id]['password']):
        user = User()
        user.id = user_id
        login_user(user)
        flash(f'{user_id}！歡迎您！')
        return redirect(url_for('from_start'))
    flash('登入失敗,請重新輸入')
    return render_template('index.html')
# 登出
@app.route('/logout')
def logout():
    user_id = current_user.get_id()
    logout_user()
    flash(f'{user_id}！歡迎下次再來！')
    return render_template('index.html') 

@app.route("/from_start")
@login_required
def from_start():
    #return render_template("getinfo.html")
    return redirect(url_for('getinfo'))

# 新增
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        db = MySQLdb.connect("伺服器", "帳號", "密碼", "schema", charset='utf8')
        cursor = db.cursor()
        psort = request.form.get('psort')
        pname = request.form.get('pname')
        pmoney = request.form.get('pmoney')
        file = request.files['pimg']
        filename = file.filename     # 圖片檔名
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # 圖片上傳到 firebase Storage：先去firebase建立anysell資料夾
        bucket = storage.bucket(app=app01)
        blob = bucket.blob('anysell/'+filename)
        blob.upload_from_filename(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        blob.make_public()
        fbimg = blob.public_url
        pstorage = fbimg
        sql = 'INSERT INTO product(psort, pname, pmoney, pimg, pstorage) VALUES ("%s", "%s", "%s", "%s", "%s")' % (psort, pname, pmoney, filename, pstorage)
        try:
            cursor.execute(sql)
            db.commit()
        except:
            db.rollback()
        db.close()                       
        return render_template('upload.html', okk='thanks')
    else:
        return render_template('upload.html')

# 查詢
@app.route('/getinfo')
@login_required
def getinfo():
    db = MySQLdb.connect("伺服器", "帳號", "密碼", "schema", charset='utf8')
    cursor = db.cursor()
    sql = 'SELECT * FROM product'
    try:
        cursor.execute(sql)
        U = cursor.fetchall()
        db.commit()
    except:
        db.rollback()
    db.close()
    return render_template('getinfo.html', u=U)

# 刪除
@app.route('/deletec', methods=['GET', 'POST'])
@login_required
def delete_entry():
    if request.method == 'POST':
        print(type(request.form['entry_id']))
        db = MySQLdb.connect("伺服器", "帳號", "密碼", "schema", charset='utf8')
        cursor = db.cursor()
        #myid=request.POST['pid']
        myid = request.form['entry_id']
        intmid = int(myid)
        cursor.execute('DELETE FROM product WHERE pid =%s', (intmid,))
        db.commit()
        # 圖片檔名
        myimg = request.form['entry_img']
        # firebase Storage圖片刪除
        bucket = storage.bucket(app=app01)
        blob_name = myimg
        blob = bucket.blob('anysell/'+blob_name)
        blob.delete()
        print('blob{}deleted.'.format(blob_name))
        return redirect(url_for('getinfo'))
    else:
        return redirect(url_for('getinfo'))

# 抓取特定id
def getimginfo(getA):
    db = MySQLdb.connect("伺服器", "帳號", "密碼", "schema", charset='utf8')
    cursor = db.cursor()
    sql = "SELECT pstorage FROM product WHERE pid = '%s'"% getA
    try:
        cursor.execute(sql)
        results = cursor.fetchone()
        strR = list(results)
        return strR[0]
    except:
        print ("Error: unable to fecth data")
    db.close()

# 抓取特定分類 三個
def getinfoRand(getA):
    db = MySQLdb.connect("伺服器", "帳號", "密碼", "schema", charset='utf8')
    cursor = db.cursor()
    sql ="SELECT * FROM product WHERE psort= '%s'"% getA
    try:
        cursor.execute(sql)
        db.commit()
        results = cursor.fetchall()
        print(results)
        # 所有該分類物件[[物件1], [物件2], ...]
        a = []
        # 隨機抽三個
        ra = []
        myaa = ''
        for row in results:
            arow = list(row)
            a.append(arow)
        ra = random.sample(a, 3)            
        return ra
    except:
        print ("Error: unable to fecth data")
    db.close()

# line
    # 上傳圖文選單 Anysell
        # A：連結
        # B：詢問店家
        # C：門市訊息
        # D：上衣
        # E：褲子
        # F：裙子

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 抓使用者資訊
    profile = line_bot_api.get_profile(event.source.user_id)
    usern = profile.display_name
    
    msg = event.message.text
    if msg == '上衣':
        myans = getinfoRand('上衣')
        mymessage = TemplateSendMessage(
            alt_text='ImageCarousel template',
            template=ImageCarouselTemplate(
                columns=[
                    ImageCarouselColumn(
                        image_url=myans[0][5],
                        action=PostbackAction(label=myans[0][2], text=myans[0][2], 
                                              data='action=buy&itemid=1')),
                    ImageCarouselColumn(
                        image_url=myans[1][5],
                        action=PostbackAction(label=myans[1][2], text=myans[1][2], 
                                              data='action=buy&itemid=1')),
                    ImageCarouselColumn(
                        image_url=myans[2][5],
                        action=PostbackAction(label=myans[2][2], text=myans[2][2], 
                                              data='action=buy&itemid=1')), ]))
        line_bot_api.reply_message(event.reply_token, mymessage)
    elif msg == '裙子':
        myans = getinfoRand('裙子')
        line_bot_api.reply_message(
            event.reply_token, 
            [TextSendMessage(text=myans[0][2]), 
             ImageSendMessage(original_content_url=myans[0][5], preview_image_url=myans[0][5]), 
             TextSendMessage(text=myans[1][2]), 
             ImageSendMessage(original_content_url=myans[1][5], preview_image_url=myans[1][5]),])
    elif msg == '褲子':
        myans = getinfoRand('褲子')
        image_carousel_template = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        thumbnail_image_url=myans[0][5],
                        title=myans[0][1], text=myans[0][2],
                        actions=[PostbackAction(label='褲子類', data='ping', text='褲子類'),]),
                    CarouselColumn(
                        thumbnail_image_url=myans[1][5],
                        title=myans[1][1], text=myans[1][2],
                        actions=[PostbackAction(label='褲子類', data='ping', text='褲子類'),]),
                    CarouselColumn(
                        thumbnail_image_url=myans[2][5],
                        title=myans[2][1], text=myans[2][2],
                        actions=[PostbackAction(label='褲子類', data='ping', text='褲子類'),])]))
        line_bot_api.reply_message(event.reply_token, image_carousel_template)
    elif msg == '尋問店家':
        line_bot_api.reply_message(event.reply_token, 
                                   [TextSendMessage(text='歡迎加line: goodbabyworker 或 email: ordersams@gmail.com')])
    elif msg == '門市訊息':
        line_bot_api.reply_message(event.reply_token, 
                                   [TextSendMessage(text='營業時間:全年無休，請打給寶寶:0933584513')]) 
    else:
        line_bot_api.reply_message(event.reply_token, 
                                   [TextSendMessage(text='營業時間:全年無休，請打給寶寶:0933584513')])

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)