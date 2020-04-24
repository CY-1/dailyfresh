from django.shortcuts import render, redirect
from django.urls import reverse
import re
from django.http import HttpResponse
from user.models import User
from django.conf import  settings
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from django.core.mail import send_mail
# Create your views here.

# /user/register
def register(request):
    '''显示注册页面'''
    if request.method=="GET":
        return render(request, "register.html")
    else:
        '''注册处理'''
        # 接收数据
        user_name = request.POST.get('user_name')
        password = request.POST.get("pwd")
        email = request.POST.get("email")
        allow = request.POST.get("allow")
        if allow != 'on':
            return render(request, "register.html", {'errmsg': "请同意协议"})
        # 数据效验
        if not all([user_name, password, email]):
            return render(request, "register.html", {'errmsg': "数据不完整"})
        # 验证邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, "register.html", {'errmsg': "邮箱错误"})
        try:
            user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, "register.html", {'errmsg': "用户名已存在"})
        # 业务处理
        user = User.objects.create_user(user_name, email, password)
        user.is_active = 0
        user.save(0)
        # 返回处理
        return redirect(reverse('goods:index'))


class RegisterView(View):
    '''注册'''
    def get(self,request):
        return render(request, 'register.html')

    def post(self,request):
        '''注册处理'''
        # 接收数据
        user_name = request.POST.get('user_name')
        password = request.POST.get("pwd")
        email = request.POST.get("email")
        allow = request.POST.get("allow")
        if allow != 'on':
            return render(request, "register.html", {'errmsg': "请同意协议"})
        # 数据效验
        if not all([user_name, password, email]):
            return render(request, "register.html", {'errmsg': "数据不完整"})
        # 验证邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, "register.html", {'errmsg': "邮箱错误"})
        try:
            user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, "register.html", {'errmsg': "用户名已存在"})
        # 业务处理
        user = User.objects.create_user(user_name, email, password)
        user.is_active = 0
        user.save(0)
        # 发送激活邮件 包涵激活链接
        # 加速用户身份信息 生成token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {"confirm": user.id}
        token = serializer.dumps(info)
        # 发送邮件
        subject = '天天生鲜欢迎信息'
        message = ""
        sender = settings.EMAIL_FROM
        receiver = [email]
        html_message =r'<a href="http://127.0.0.1:8000/user/active/%s/"> http://127.0.0.1:8000/user/active/%s/ </a>' % \
                  (token.decode('utf-8'), token.decode('utf-8'))
        send_mail(subject, message=message, from_email=sender, recipient_list=receiver, html_message=html_message)
        # 返回处理
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''  用户激活  '''

    def get(self, request, token):
        '''进行用户激活'''
        # token解密
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取激活用户的id
            user_id = info['confirm']
            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 返回登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired:
            # 激活链接过期
            return HttpResponse("过期了")


class LoginView(View):
    '''登录'''

    def get(self, request):
        return render(request, 'login.html')