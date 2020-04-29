from goods.views import IndexView, DetailView, ListView
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from goods import views
from django.urls import re_path
from django.conf.urls import url
app_name = 'goods'
urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r"^list/(?P<type_id>\d+)/(?P<page>\d+)/$", ListView.as_view(), name='list'),
    url(r'^goods/(?P<goods_id>\d+)/$', DetailView.as_view(), name='detail'),
]