
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from user import views
from django.conf.urls import  url
app_name = 'user'
urlpatterns = [
url(r"^register/$", views.register, name='register'),
url(r"^register_handle/$", views.register_handle, name="register_handle")
]