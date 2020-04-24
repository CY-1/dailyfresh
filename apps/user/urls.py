
from django.contrib import admin
from django.urls import path
from django.urls import path,include,re_path
from user.views import RegisterView, ActiveView, LoginView
from django.conf.urls import  url

app_name = 'user'
urlpatterns = [
   url(r"^register/$", RegisterView.as_view()),
   url(r"^active/$", LoginView.as_view()),
   url(r"^active/(?P<token>.*)/$", ActiveView.as_view())
]