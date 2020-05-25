
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from order.views import OrderPlaceView, OrderCommitView, OrderCommitView2, OrderPayView, OrderCheck, OrderCommentView\
    , OrderDelete
from django.conf.urls import url
app_name = 'order'
urlpatterns = [
    url(r'^place/$', OrderPlaceView.as_view(), name='place'),# 提交订单页面显示
    url(r'^commit/$', OrderCommitView.as_view(), name='commit'),# 订单创建
    url(r'^pay/$', OrderPayView.as_view(), name='pay'),# 支付
    url(r'^check/$', OrderCheck.as_view(), name='check'),# 验证支付
    url(r'^delete/$', OrderDelete.as_view(), name='delete'),# 删除订单
    url(r'^comment/(?P<order_id>.+)/$', OrderCommentView.as_view(), name='comment'),# 验证支付
]# pgcshl9204@sandbox.com