from django.shortcuts import render, redirect
from django.urls import reverse
import re
from user.models import User
# Create your views here.

# /user/register
def register(request):
    '''显示注册页面'''
    return render(request, "register.html")


def register_handle(request):
    '''注册处理'''
    # 接收数据
    user_name = request.POST.get('user_name')
    password = request.POST.get("pwd")
    email = request.POST.get("email")
    allow = request.POST.get("allow")
    if allow!='on':
        return render(request, "register.html", {'errmsg': "请同意协议"})
    # 数据效验
    if not all([user_name,password,email]):
        return render(request, "register.html", {'errmsg': "数据不完整"})
    # 验证邮箱
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, "register.html", {'errmsg': "邮箱错误"})
    try:
        user = User.objects.get(username=user_name)
    except User.DoesNotExist:
        user= None
    if user:
        return render(request, "register.html", {'errmsg': "用户名已存在"})
    # 业务处理
    user = User.objects.create_user(user_name, email, password)
    user.is_active = 0
    user.save(0)
    # 返回处理
    return redirect(reverse('goods:index'))