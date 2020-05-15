from django.contrib import admin
from order.models import OrderInfo, OrderGoods
# Register your models here.
admin.site.register(OrderInfo)
admin.site.register(OrderGoods)