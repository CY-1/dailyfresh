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
        # 获取用户
        user = request.user
        # 获取用户购物车信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_dict = conn.hgetall(cart_key)

        skus = []
        total_count = 0
        total_price = 0
        # 遍历获取商品信息
        for sku_id, count in cart_dict.items():
            # 根据商品id获取信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品订单数目
            amount = sku.price*(int(count))
            # 动态增加属性
            sku.amount = amount
            sku.count = count.decode()
            skus.append(sku)
            # 累加计算总数目和总价格
            total_count+=int(count)
            total_price+=amount
        context = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus,
        }
        return render(request, 'cart.html', context)


# 更新购物车的记录
# 前端采用ajax post请求
# 前端需要传递参数商品id 更新的商品数目
class CartUpdateView( View):
    '''购物车记录'''
    def post(self, request):
        '''购物车记录更新'''

        if not request.user.is_authenticated:
            return JsonResponse({'res': 0, "errmsg": '先登录'})
        count = request.POST.get('count')
        sku_id = request.POST.get('sku_id')
        user = request.user
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
        # 数据效验
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        if count>sku.stock:
            return JsonResponse({'res':4,'errmsg':"库存不够"})
        # 业务应答
        conn.hset(cart_key, sku_id, count)
        # 用户购物车商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count+=int(val)
        # 返回响应
        return JsonResponse({'res':5, "message":'更新成功','total_count':total_count})


# 删除购物车记录
# 采用ajax post请求
# 前端需要传递的参数 sku.id
class CartDeleteView( View):
    def post(self, request):
        '''购物车删除'''
        if not request.user.is_authenticated:
            return JsonResponse({'res': 0, "errmsg": '先登录'})
        sku_id = request.POST.get('sku_id')
        # 数据效验
        if not sku_id:
            return JsonResponse({'res':1,'errmsg':'无效数据'})
        conn = get_redis_connection('default')
        cart_key = "cart_%d" % request.user.id
        exists = conn.hexists(cart_key, sku_id)
        if not exists:
            return JsonResponse({'res':2,'errmsg':'不存在数据'})

        conn.hdel(cart_key, sku_id)
        # 用户购物车商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count+=int(val)
        # 返回数据
        return JsonResponse({'res':3, 'total_count':total_count,'message':'删除成功'})
