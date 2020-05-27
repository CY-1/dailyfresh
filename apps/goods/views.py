from django.shortcuts import render, redirect,reverse
from django.views.generic import View
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU
from django_redis import get_redis_connection
from order.models import OrderGoods
from django.core.paginator import  Paginator
# Create your views here.


class IndexView(View):
    def get(self, request):
        '''返回首页'''
        # 获取商品的种类信息
        types = GoodsType.objects.all()
        # 获取首页轮播商品信息 order_by默认就是升序
        goods_banners = IndexGoodsBanner.objects.all().order_by("index")
        # 获取首页的促销活动信息
        promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
        # 获取首页分类商品展示信息
        for type in types:
            # 获取type种类首页分类商品的展示信息
            # 给type增加属性 分别保存首页分类商品的图片展示信息和文字展示信息
            type.image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
            type.title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by("index")

        # 获取购物车商品的数目
        user = request.user

        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            # 获取用户购物车商品里面的数据
            cart_count = conn.hlen(cart_key)
        # 组织模板上下文
        context = {
            'types': types,
            'goods_banners': goods_banners,
            "promotion_banners": promotion_banners,
            "cart_count": cart_count,
        }
        return render(request, 'index.html', context)


# /goods/商品ID
class DetailView(View):
    '''详情页'''
    def get(self, request, goods_id=1):
        '''显示详情页'''
        # 获取商品信息
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取商品的分类信息
        types = GoodsType.objects.all()
        # 获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment="")
        # 新品推荐
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取同一个SPU的其他规格的商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取购物车数量
        user = request.user

        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = "cart_%d" % user.id
            cart_count = conn.hlen(cart_key)
            conn = get_redis_connection("default")
            history_key = "history_%d"% user.id
            # 先移除goods_id 后加入 以此来调整历史记录位置
            conn.lrem(history_key, 0, goods_id)
            conn.lpush(history_key, goods_id)
            # 保留固定的元素
            conn.ltrim(history_key, 0, 4)
        # 组织上下文
        context = {
            'sku': sku,
            'types': types,
            'sku_orders': sku_orders,
            'new_skus': new_skus,
            "cart_count": cart_count,
            'same_spu_skus': same_spu_skus,
        }
        return render(request, 'detail.html', context)

# 需要传递种类id 页码 排序方式
# /list/种类id/页码?sort=排序方式
class ListView(View):
    '''列表页'''
    def get(self, request, type_id, page):
        '''显示列表页'''
        # 先获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse("goods:index"))
        # 获取排序的方式
        sort = request.GET.get('sort')
        # 获取商品的分类信息
        types = GoodsType.objects.all()
        if sort=='price':
            skus = GoodsSKU.objects.filter(type=type).order_by("price")
        elif sort=='hot':
            skus = GoodsSKU.objects.filter(type=type).order_by("-sales")
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
            sort = 'default'
        paginator = Paginator(skus, 5)
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page>paginator.num_pages:
            page = 1
        skus_page = paginator.page(page)
        # 获取page页的内容
        # 1 总页数小于五页 页面上显示所有页码
        # 2 如果当前页是前三页 显示前五页的页码
        # 3 如果当前页是后三页 显示后五页的页码
        # 4 其他情况 显示当前页,当前页的前两页和后两页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages-page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+3)

        # 新品推荐
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]
        # 购物车数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = "cart_%d"% user.id
            cart_count = conn.hlen(cart_key)
        context = {
            'skus': skus,
            'type':type,
            'skus_page': skus_page,
            'cart_count': cart_count,
            'sort': sort,
            'types':types,
            'pages': pages,
            "new_skus": new_skus,
        }
        return render(request, 'search/indexes/list.html', context)