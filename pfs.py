from flask import Flask, render_template, request, redirect, url_for, g
from flask import session, flash, send_from_directory, make_response
import sqlite3
from datetime import datetime, timedelta
import os
from account.views import RegUser, UserLogin, MyRegUser


app = Flask(__name__)
app.secret_key = '*^%&$&^%&*()&*^%'
DATABASE_URL = r'.\db\feedback.db'
UPLOAD_FOLDER = r'.\uploads'
ALLOWED_EXTENSIONS = ['.jpg', '.png', '.gif']


# 呈现特定目录下的资源
@app.route('/profile/<filename>/')
def render_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# 将游标获取的Tuple根据数据库列表转换成dict
def make_dicts(cursor, row):
    return dict((cursor.description[i][0], value) for i, value in enumerate(row))


# 检查文件是否允许上传
def allowed_file(filename):
    name, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


# 获取（建立数据库连接）
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_URL)
        db.row_factory = make_dicts
    return db


# 执行SQL语句不返回数据结果
def execute_sql(sql, prms=()):
    c = get_db().cursor()
    c.execute(sql, prms)
    c.connection.commit()


# 执行用于选择数据的SQL语句
def query_sql(sql, prms=(), one=False):
    c = get_db().cursor()
    result = c.execute(sql, prms).fetchall()
    c.close()
    return (result[0] if request else None) if one else result


# 关闭连接（在当前app上下文销毁时关闭连接）
@app.teardown_appcontext
def close_connection(exeption):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def hello_world():
    return render_template('base.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', None)
        passwd = request.form.get('passwd', None)
        sql = "select Password from UserInfo where UserName = ?"
        user_info = query_sql(sql, (username,))
        get_passwd = user_info[0]['Password'] if user_info else None
        if passwd == get_passwd:
            session['username'] = username
            return redirect(url_for('feedback_list'))
        else:
            flash('用户名或密码错误！')
    return render_template('login.html')


@app.route('/logout/')
def logout():
    session.pop('username', None)
    g.user = None
    return redirect(url_for('feedback_list'))


@app.before_request
def before_request():
    g.user = None
    if 'username' in session:
        sql = "select UserName from UserInfo"
        result = query_sql(sql)
        user = [u for u in result if u['UserName'] == session['username']][0]
        g.user = user


@app.route('/feedback/')
def feedback():
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    sql = 'select ROWID, CategoryName from category'
    categories = c.execute(sql).fetchall()
    c.close()
    conn.close()
    return render_template('post.html', categories=categories)


@app.route('/post_feedback/', methods=['POST'])
def post_feedback():
    # 如果当前请求的方法为POST
    if request.method == 'POST':
        # 获取表单内容
        subject = request.form['subject']
        categoryid = request.form.get('category', 1)
        username = request.form.get('username')
        email = request.form.get('email')
        body = request.form.get('body')
        release_time = datetime.now()
        state = 0
        img_path = None
        if 'screenshot' in request.files:
            # 获取图片上传，并且获取文件名，以便和其他字段一并插入数据库
            img = request.files['screenshot']
            if allowed_file(img.filename):
                # 重命名文件
                img_path = datetime.now().strftime('%Y%m%d%H%M%f') + os.path.splitext(img.filename)[1]
                # 上传图片
                img.save(os.path.join(UPLOAD_FOLDER, img_path))

        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        sql = "insert into feedback (Subject, CategoryID, UserName, Email, Body, State, ReleaseTime, Image) values (?,?,?,?,?,?,?,?)"
        c.execute(sql, (subject, categoryid, username, email, body, state, release_time, img_path))
        conn.commit()
        conn.close()
        return redirect(url_for('feedback'))


@app.route('/admin/list/')
def feedback_list():
    if not g.user:
        return redirect(url_for('login'))
    else:
        key = request.args.get('key', '')
        sql = 'SELECT f.ROWID,f.*,c.CategoryName FROM feedback f INNER JOIN category c on c.ROWID = f.CategoryID WHERE f.Subject LIKE ? ORDER BY f.ROWID DESC'
        feedbacks = query_sql(sql, ('%{}%'.format(key),))
        return render_template('feedback_list.html', items=feedbacks)


@app.route('/admin/edit/<id>/')
def edit_feedback(id=None):
    sql = "select ROWID, CategoryName from category"
    categories = query_sql(sql)
    # 获取当前id的信息并绑定至form表单，以备修改
    sql = "select rowid, * from feedback where rowid = ?"
    current_feedback = query_sql(sql, (id,), one=True)
    return render_template('edit.html', categories=categories, item=current_feedback)


@app.route('/admin/save_edit/', methods=['POST'])
def save_feedback():
    if request.method == 'POST':
        # 获取表单内容
        rowid = request.form.get('rowid', None)
        reply = request.form.get('reply')
        state = 1 if request.form.get('isprocessed', 0) == 'on' else 0

        print("rowid={}, reply={}, state={}".format(rowid, reply, state))

        sql = "update feedback set Reply = ?, State = ? where rowid = ?"
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute(sql, (reply, state, rowid))
        conn.commit()
        c.close()
        conn.close()

    return redirect(url_for('feedback_list'))


@app.route('/admin/delete_feedback/<id>/')
def delete_feedback(id=None):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    sql = 'delete from feedback where rowid = ?'
    c.execute(sql, (id, ))
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for('feedback_list'))


@app.route('/setck/')
def set_mycookie():
    resp = make_response('hello quincy')
    resp.set_cookie('username', 'quincy学python', path='/', httponly=False, expires=datetime.now() + timedelta(days=7))
    return resp


@app.route('/getck/')
def get_mycookie():
    ck = request.cookies.get('username', None)
    if ck:
        return ck
    else:
        return 'No content'


@app.route('/removeck/')
def remove_cookie():
    resp = make_response('删除 cookie')
    resp.set_cookie('username', '', expires=datetime.now() + timedelta(hours=-1))
    return resp


# 为导入的基于类的视图添加分配URL规则
app.add_url_rule('/reg/', view_func=RegUser.as_view('reg_user'))

app.add_url_rule('/register', view_func=MyRegUser.as_view('register_user'))


if __name__ == '__main__':
    app.run(debug=True)