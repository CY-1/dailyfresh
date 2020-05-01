
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from cart.views import CartAddView,CartInfoView, CartUpdateView,CartDeleteView
app_name = 'cart'
urlpatterns = [
    re_path(r"^add/$", CartAddView.as_view(), name='add'),
    re_path(r"^$", CartInfoView.as_view(), name='show'),# 购物车页面显示
    re_path(r"^update/$", CartUpdateView.as_view(), name='update'),# 购物车页面添加商品数
    re_path(r"^delete/$", CartDeleteView.as_view(), name='delete'),# 购物车删除一项订单
]