from django.shortcuts import render
from django.views.generic import View
from goods.models import GoodsSKU
from django.http import JsonResponse
from django_redis import get_redis_connection
from utils.mixin import LoginRequireMixin
class CartAddView(View):
    '''购物车添加'''
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'res': 0, "errmsg":'先登录'})
        count = request.POST.get('count')
        sku_id = request.POST.get('sku_id')
        # 数据效验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': "数据不完整"})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})
        # 添加购物车记录
        conn = get_redis_connection('default')
        # 先尝试获取sku_id的值 看看购物车是否已经在购物车当中
        cart_key = 'cart_%d' % request.user.id
        # 如果hget拿不到 就会返回一个None
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            # 累加购物车商品的数据
            count += int(cart_count)
        if count>sku.stock:
            return JsonResponse({'res': 4, "errmsg": '库存不够'})
        conn.hset(cart_key, sku_id, count)
        total_count = conn.hlen(cart_key)
        return JsonResponse({'res': 5, 'message': 'success', 'total_count': total_count})


class CartInfoView(LoginRequireMixin , View):
    '''购物车页面显示'''
    def get(self, request):
        return render(request, 'cart.html')

