
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from cart.views import CartAddView,CartInfoView
app_name = 'cart'
urlpatterns = [
    re_path(r"^add/$", CartAddView.as_view(), name='add'),
    re_path(r"^$", CartInfoView.as_view(), name='show'),# 购物车页面显示
]