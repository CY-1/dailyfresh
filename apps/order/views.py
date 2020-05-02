from django.shortcuts import  render, redirect, reverse
from django.views import View
from goods.models import  GoodsSKU
from user.models import Address
from django_redis import get_redis_connection
from utils.mixin import  LoginRequireMixin
class OrderPlaceView(LoginRequireMixin, View):
    '''提交订单页面'''
    def post(self, request):
        '''提交订单页面'''
        user = request.user
        # 获取参数sku_ids
        sku_ids = request.POST.getlist("sku_ids")# [1,26]
        # 效验阐述
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
            count = conn.hget(cart_key, sku_id)
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
        total_pay = total_price+transit_price
        # 获取用户的地址
        addrs = Address.objects.filter(user=user)
        # 组织上下文
        context = {
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'addrs':addrs,
            'transit_price':transit_price,
            'total_pay':total_pay,
        }
        return render(request, "place_order.html", context)


