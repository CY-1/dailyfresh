
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from order.views import OrderPlaceView, OrderCommitView
from django.conf.urls import url
app_name = 'order'
urlpatterns = [
    url(r'^place/$', OrderPlaceView.as_view(), name='place'),# 提交订单页面显示
    url(r'^commit/$', OrderCommitView.as_view(), name='commit'),# 订单创建
]