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
