from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.urls import reverse
import re
from django.http import HttpResponse
from user.models import User
from django.conf import  settings
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from celery_tasks.tasks import  send_register_active_email
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
        send_register_active_email.delay(email, user_name, token.decode())
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
        if 'username' in request.COOKIES:
            username = request.COOKIES.get("username")
            checked = "checked"
        else:
            username = ""
            checked = ""
        return render(request, 'login.html', {"username": username, "checked": checked})

    def post(self,request):
        '''登录效验'''
        # 接受数据
        username = request.POST.get('username')
        password = request.POST.get("pwd")
        # 效验数据
        if not all([username, password]):
            return render(request, 'login.html', {"errmsg":"不完整"})
        # 业务处理 用的是自带的认证系统
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                # 记录用户登录状态 用自带的用户系统
                login(request, user)
                response = redirect(reverse("goods:index"))
                # 判断是否记住用户名
                remember = request.POST.get("remember")
                if remember=="on":
                    # 是否记住用户名
                    response.set_cookie("username", username, max_age=7*24*3600)
                else:
                    response.delete_cookie("username")
                # 跳转到首页
                return response
            else:
                return render(request, 'login.html', {"errmsg": "用户没激活"})
        else:
            return render(request, 'login.html', {"errmsg": "用户名或密码不正确"})

# /user
class UserInfoView(View):
    '''用户中心 信息页'''

    def get(self, request):
        return render(request, 'user_center_info.html', {"page": "user"})

# /user/order
class UserOrderView(View):
    '''用户中心 订单页'''

    def get(self, request):
        return render(request, 'user_center_order.html', {"page": "order"})


# /user/address
class UserAddressView(View):
    '''用户中心 地址'''

    def get(self, request):
        return render(request, 'user_center_site.html', {"page": "address"})
