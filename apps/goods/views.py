from django.shortcuts import render
from django.views.generic import View
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection
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
            print(cart_key)
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