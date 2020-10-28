from flask.views import View, MethodView
from flask import render_template


# 基于类的视图
class RegUser(View):
    methods = ['GET', 'POST']

    def dispatch_request(self):
        return render_template('register.html')


class UserLogin(View):
    def dispatch_request(self):
        pass


# 基于方法的视图
class MyRegUser(MethodView):
    def get(self):
        return render_template('register.html')

    def post(self):
        # 不需要判断GET/POST请求
        return None