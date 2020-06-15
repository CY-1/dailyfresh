from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
import re
from django.http import StreamingHttpResponse
import random
from django.http import JsonResponse
from django.core.paginator import Paginator
from goods.models import GoodsSKU
from django.http import HttpResponse
from user.models import User, Address
from django.conf import settings
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from celery_tasks.tasks import send_register_active_email, send_verify_code
from utils.mixin import LoginRequireMixin
from django_redis import get_redis_connection
from order.models import OrderInfo, OrderGoods
from utils.image_code.code import verify_code
from django.core.mail import send_mail


# Create your views here.

# /user/register
def register(request):
    '''显示注册页面'''
    if request.method == "GET":
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

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
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
        if request.user.is_authenticated:  # 防止用户重复登录
            return redirect(reverse('goods:index'))
        if 'username' in request.COOKIES:
            username = request.COOKIES.get("username")
            checked = "checked"
        else:
            username = ""
            checked = ""
        return render(request, 'login.html', {"username": username, "checked": checked})

    def post(self, request):
        '''登录效验'''
        # 接受数据
        username = request.POST.get('username')
        password = request.POST.get("pwd")
        # 效验数据
        if not all([username, password]):
            return render(request, 'login.html', {"errmsg": "不完整"})
        # 业务处理 用的是自带的认证系统
        user = authenticate(username=username, password=password)

        # 获取登录后要跳转的地址 如果能获取到返回值就获取 获取不到就获取reverse的值
        # 获取不到就是None
        next_url = request.GET.get('next', reverse('goods:index'))
        if user is not None:
            if user.is_active:
                # 记录用户登录状态 用自带的用户系统
                login(request, user)
                response = redirect(next_url)
                # 判断是否记住用户名
                remember = request.POST.get("remember")
                if remember == "on":
                    # 是否记住用户名
                    response.set_cookie("username", username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie("username")
                # 跳转到首页
                return response
            else:
                return render(request, 'login.html', {"errmsg": "用户没激活"})
        else:
            return render(request, 'login.html', {"errmsg": "用户名或密码不正确"})


# /user/logout
class LogoutView(View):
    '''退出登录'''

    def get(self, request):
        '''退出登录'''
        # 使用的内置认证系统 也要使用内置的退出
        # 清楚用户的session
        logout(request)
        return redirect(reverse("goods:index"))


# /user
class UserInfoView(LoginRequireMixin, View):
    '''用户中心 信息页'''

    def get(self, request):
        # 获取用户的个人信息
        address = Address.objects.get_default_address(request.user)
        user = request.user
        # 获取用户的历史游览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host="192.168.80.132", port=6379, db=9)
        con = get_redis_connection("default")
        history_key = "history_%d" % user.id
        # 获取用户最新游览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)
        # 从数据库中查询用户游览商品的具体信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        # 组织上下文
        context = {"page": "user",
                   "address": address,
                   "goods_li": goods_li}
        return render(request, 'user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequireMixin, View):
    '''用户中心 订单页'''

    def get(self, request, page):
        # 获取用户的订单信息
        user = request.user
        # 获取用户的默认地址信息
        #
        user = request.user
        orders = OrderInfo.objects.filter(user=user, is_delete=0).order_by("-create_time")

        # 遍历获取订单商品的信息
        for order in orders:
            # 根据order_Id 查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            # 遍历order_skus计算商品小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性 保存订单商品小计
                order_sku.amount = amount
            # 保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给order增加属性
            order.order_skus = order_skus
        # 分页
        paginator = Paginator(orders, 1)
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1
        order_page = paginator.page(page)
        # 获取page页的内容
        # 1 总页数小于五页 页面上显示所有页码
        # 2 如果当前页是前三页 显示前五页的页码
        # 3 如果当前页是后三页 显示后五页的页码
        # 4 其他情况 显示当前页,当前页的前两页和后两页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)
        # 组织上下文
        if len(orders) == 0:
            pages = None
        context = {
            'order_page': order_page,
            'pages': pages,
            'page': orders,
        }
        return render(request, 'user_center_order.html', context)


# /user/address
class UserAddressView(LoginRequireMixin, View):
    '''用户中心 地址'''

    def get(self, request):
        # 获取用户的默认地址信息
        user = request.user
        default_address = Address.objects.get_default_address(user)
        address = Address.objects.filter(user=user, is_default=0)
        return render(request, 'user_center_site.html',
                      {"page": "address", "default_address": default_address, "address": address})

    def post(self, request):
        """地址的添加"""
        # 接受数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get("addr")
        zip_code = request.POST.get("zip_code")
        phone = request.POST.get("phone")

        # 效验数据
        if not all([receiver, addr, phone]):
            return render(request, "user_center_site.html", {"errmsg": "数据不完整"})
        if not re.match(r"^^[1][3,4,5,7,8][0-9]{9}$", phone):
            return render(request, "user_center_site.html", {"errmsg": "手机格式不正确"})
        # 业务处理
        # 如果用户已经默认收货地址 添加的的地址不作为默认收货地址 否则就是默认收货地址
        # 获取登录用户
        user = request.user

        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True
        # 添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default,
                               )
        # 应答 刷新地址页面
        return redirect(reverse("user:address"))


# 修改地址
class UserChangeAddress(LoginRequireMixin, View):

    def post(self, request):
        user = request.user
        # 产生新的默认地址

        if request.POST.get("is_delete") == "false":
            # 让原来的默认地址变成普通地址
            old_default_address = Address.objects.get_default_address(user)
            old_default_address.is_default = 0
            old_default_address.save()
            new_default_address = Address.objects.get(id=request.POST.get("new_address_value"))
            new_default_address.is_default = 1
            new_default_address.save()
        else:
            new_default_address = Address.objects.get(id=request.POST.get("new_address_value"))
            new_default_address.delete()
        return JsonResponse({"res": 3})


# 修改头像
class UserImage(LoginRequireMixin, View):
    def post(self, request):
        """修改头像"""

        user = User.objects.get(id=request.user.id)
        image = request.FILES.get('file')
        if image is None:
            return JsonResponse({"code": 2})
        else:
            user.image = image
            user.save()

        return JsonResponse({"code": 1})


# 修改密码
class ChangePassword(View):
    """修改密码"""
    def get(self, request):
        return render(request, 'changepassword.html')

    def post(self, request):
        con = get_redis_connection("default")
        user_name = request.POST.get("user_name")
        code = request.POST.get("code")
        # 上传来的验证码
        img_code = request.POST.get("img_code")
        user = User.objects.get(username=user_name)
        password = request.POST.get("password")
        redis_code = con.get(user_name).decode()
        csrf_token = request.COOKIES.get("csrftoken")
        # 数据库保存的验证码
        send_img_code = con.get("password_%s" % csrf_token)
        con.delete("password_%s" % csrf_token)
        con.delete(user_name)
        print(send_img_code, "   ",img_code)
        if code == redis_code and send_img_code.decode().lower() == img_code:
            user.set_password(password)
            user.save()
            return JsonResponse({"code": 1})

        else:
            return JsonResponse({"code": 2})


# 修改密码发送验证信息
class SendCode(View):
    """验证信息"""
    def post(self, request):
        """发送验证邮件"""
        user_name = request.POST.get("user_name")
        user = User.objects.get(username=user_name)
        email = user.email
        user_name = user.username
        token = "".join(random.sample("qwertyuipoadfgjfkxsrfh12345", 4))
        # 发送邮件
        send_verify_code(email, user_name, token)
        con = get_redis_connection("default")
        con.set(user_name, token)
        return JsonResponse({"code": 1})


# 图片验证码
class ImageCode(View):
    """验证信息"""
    def get(self, request):
        """发送验证邮件"""
        # 生成验证码图片 名字 真实文本 图片数据
        name, text, image_data = verify_code()
        con = get_redis_connection()
        csrf_token = request.COOKIES.get("csrftoken")
        con.set("password_%s" % csrf_token, text, 300)
        return HttpResponse(image_data, content_type='image/jpg')


