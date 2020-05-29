from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
# Create your models here.

class AddressManager(models.Manager):
    '''地质模型管理器类'''
    # 1.改变原有查询的结果集
    # 2.封装方法： 用户操作模型管理类对应的数据表
    def get_default_address(self, user):
        # self.model 获取self对象火灾的模型类
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            address = None
        print(address)
        return address


class User(AbstractUser, BaseModel):
    '''用户模型类'''

    image = models.ImageField(upload_to='image', verbose_name='头像')

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class Address(BaseModel):
    '''地址模型类'''
    user = models.ForeignKey('User', verbose_name='所属账户', on_delete=models.CASCADE)
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    objects = AddressManager()

    def __str__(self):
        return self.user.username+"的地址"

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name
