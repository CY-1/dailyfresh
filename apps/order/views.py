from django.shortcuts import render, redirect, reverse
from django.views import View
from goods.models import GoodsSKU
from user.models import Address
from django.http import JsonResponse
from django_redis import get_redis_connection
from utils.mixin import LoginRequireMixin
from order.models import OrderInfo, OrderGoods
from datetime import datetime
from django.db import transaction
from alipay import AliPay, ISVAliPay
from django.conf import settings
import os


class OrderPlaceView(LoginRequireMixin, View):
    '''提交订单页面'''
    def post(self, request):
        '''提交订单页面'''
        user = request.user
        # 获取参数sku_ids
        sku_ids = request.POST.getlist("sku_ids")  # [1,26]
        # 效验参数
        if not sku_ids:
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        skus = []
        # 保存商品的总数目和总价格
        total_count = 0
        total_price = 0
        # 遍历sku_ids 获取用户购买的商品信息
        for sku_id in sku_ids:
            # 根据商品id信息获取信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取数目
            count = conn.hget(cart_key, sku_id).decode()
            # 计算小计
            amount = sku.price * int(count)
            # 动态给对象增加一个属性 count保存购买商品的数量 和价格amount
            sku.amount = amount
            sku.count = count
            skus.append(sku)
            # 累加计算商品的总价和总数目
            total_count += int(count)
            total_price += amount
        # 运费  应该有一个子系统
        transit_price = 10
        total_pay = total_price + transit_price
        # 获取用户的地址
        addrs = Address.objects.filter(user=user)
        # 组织上下文
        sku_ids = ','.join(sku_ids)
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'addrs': addrs,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'sku_ids': sku_ids,
        }
        return render(request, "place_order.html", context)


# 前端传递的参数 地址 支付方式 商品id
class OrderCommitView(View):
    '''订单创建'''
    PAY_METHOD_CHOICES = {
        "1": '货到付款',
        "2": '微信支付',
        "3": '支付宝',
        "4": '银联支付',
    }

    @transaction.atomic
    def post(self, request):
        '''订单创建 向df_order_info添加一条记录 向df_order_goods添加商品个数的信息'''

        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "用户未登录"})
        # 接收参数
        addr_id = request.POST.get("addr_id")
        pay_method = request.POST.get("pay_method")
        sku_ids = request.POST.get("sku_ids")
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({"res": 1, 'errmsg': "参数不完整"})
        # 校验支付方式
        if pay_method not in self.PAY_METHOD_CHOICES.keys():
            return JsonResponse({"res": 2, "errmsg": "非法支付方式"})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({"res": 3, 'errmsg': '地址非法'})
        # 创建订单
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        # 运费先写死
        transit_price = 10
        # 总数目和总金额
        total_count = 0
        total_price = 0
        # 设置事务保存点
        save_id = transaction.savepoint()
        try:
            # 创建订单信息
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price
                                             )
            sku_ids = sku_ids.split(",")
            conn = get_redis_connection('default')
            cart_key = "cart_%d" % user.id
            for sku_id in sku_ids:
                # 获取商品信息
                try:
                    # 上锁  悲观锁
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({"res": 4, "errmsg": "商品不存在"})

                # 从redis中获取用户所要购买的商品的数目
                count = conn.hget(cart_key, sku_id)
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({"res": 6, "errmsg": "库存不足"})
                # 向订单商品表中添加信息
                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price,
                )
                #  更新商品库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # 累加计算订单商品的总数目和总价格
                amount = sku.price * int(count)
                total_count += int(count)
                total_price += amount
            # 更新订单信息表中的商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
            # 清除用户购物车中对应的记录
        except Exception as  e:
            transaction.savepoint_rollback(save_id)

            return JsonResponse({'res': 7, "errmsg": '下单失败'})
        transaction.savepoint_commit(save_id)
        conn.hdel(cart_key, *sku_ids)
        # 返回应答
        return JsonResponse({"res": 5, "message": "创建成功"})


class OrderCommitView2(View):
    '''订单创建'''
    PAY_METHOD_CHOICES = {
        "1": '货到付款',
        "2": '微信支付',
        "3": '支付宝',
        "4": '银联支付',
    }

    @transaction.atomic
    def post(self, request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "用户未登录"})
        # 接受参数
        addr_id = request.POST.get("addr_id")
        pay_method = request.POST.get("pay_method")
        sku_ids = request.POST.get("sku_ids")
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({"res": 1, 'errmsg': "参数不完整"})
        # 校验支付方式
        if pay_method not in self.PAY_METHOD_CHOICES.keys():
            return JsonResponse({"res": 2, "errmsg": "非法支付方式"})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({"res": 3, 'errmsg': '地址非法'})
        # 创建订单
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        # 运费先写死
        transit_price = 10
        # 总数目和总金额
        total_count = 0
        total_price = 0
        save_id = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price
                                             )
            sku_ids = sku_ids.split(",")
            conn = get_redis_connection('default')
            cart_key = "cart_%d" % user.id
            for sku_id in sku_ids:
                for i in range(3):
                    # 获取商品信息
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({"res": 4, "errmsg": "商品不存在"})

                    # 从redis中获取用户所要购买的商品的数目
                    count = conn.hget(cart_key, sku_id)
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({"res": 6, "errmsg": "库存不足"})

                    # 更新商品库存和销量
                    orgin_stock = sku.stock
                    new_sales = orgin_stock - int(count)
                    new_stock = sku.sales + int(count)
                    # 返回受影响的函数
                    res = GoodsSKU.objects.filter(id=sku.id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({"res": 7, 'errmsg': "下单失败"})
                        continue
                    # 向订单商品表中添加信息
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price,
                    )
                    sku.stock -= int(count)
                    sku.sales += int(count)
                    sku.save()
                    # 累加计算订单商品的总数目和总价格
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount
                    # 代表执行成功跳出循环
                    break
            # 更新订单信息表中的商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
            # 清楚用户购物车中对应的记录
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, "errmsg": '下单失败'})
        transaction.savepoint_commit(save_id)
        conn.hdel(cart_key, *sku_ids)
        # 返回应答
        return JsonResponse({"res": 5, "message": "创建成功"})


class OrderPayView(View):
    '''订单支付'''

    def post(self, request):

        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python sdk调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()
        alipay = AliPay(
            appid="2016102200738204",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_pay),  # 支付总金额
            subject='天天生鲜%s 用户' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class OrderCheck(View):
    '''查看订单支付结果'''
    def post(self, request):
        '''查询支付结果'''
# 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:

            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python sdk调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()
        alipay = AliPay(
            appid="2016102200738204",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, 此处沙箱模拟True
        )
        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            code = response.get('code')
            if code == '10000' and response.get('trade_status')=="TRADE_SUCCESS":
                # 支付成功
                trade_no = response.get("trade_no")
                # 获取支付宝交易号
                order.trade_no = trade_no
                # 更新交易状态
                order.order_status = 4
                order.save()
                return JsonResponse({'res': 3, "messsage":'成功'})
            elif code=='40004' or (code=="10000" and response.get('trade_status')=="WAIT_BUYER_PAY"):
                # 等待买家付款
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                return JsonResponse({"res": 4, 'errmsg':"支付失败"})


class OrderCommentView(LoginRequireMixin, View):
    def get(self, request, order_id):
        """展示评论页"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 需要根据状态码获取状态
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 根据订单id查询对应商品，计算小计金额,不能使用get
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount = order_sku.count * order_sku.price
            order_sku.amount = amount
        # 增加实例属性
        order.order_skus = order_skus

        context = {
            'order': order,
        }
        return render(request, 'order_comment.html', context)

    def post(self, request, order_id):
        """处理评论内容"""
        # 判断是否登录
        user = request.user

        # 判断order_id是否为空
        if not order_id:
            return redirect(reverse('user:order'))

        # 根据order_id查询当前登录用户订单
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 获取评论条数
        total_count = int(request.POST.get("total_count"))

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)  # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')  # comment_1 comment_2

            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            # 保存评论到订单商品表
            order_goods.comment = content
            order_goods.save()

        # 修改订单的状态为“已完成”
        order.order_status = 5  # 已完成
        order.save()
        # 1代表第一页的意思，不传会报错
        return redirect(reverse("user:order", kwargs={"page": 1}))