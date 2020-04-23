
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from goods import views
from django.conf.urls import url
app_name = 'goods'
urlpatterns = [
    url(r'^$', views.index, name='index')
]