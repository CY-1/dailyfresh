from django.contrib import admin
from goods.models import GoodsType, GoodsSKU, Goods
# Register your models here.

admin.site.register(GoodsType)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
