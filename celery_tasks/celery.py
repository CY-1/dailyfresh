# 使用celery
from celery import Celery
from django.conf import  settings
from django.core.mail import  send_mail
# 在任务处理者加入
import os
import django
# 因为依赖了django里面的setting初始化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
django.setup()


# 创建一个Celery对象 redis 作为中间人 8表示8号数据库
app = Celery("celery_task.tasks", broker='redis://192.168.80.132:6379/8')

# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ""
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = r'<a href="http://127.0.0.1:8000/user/active/%s/"> http://127.0.0.1:8000/user/active/%s/ </a>' % \
                   (token, token)
    send_mail(subject, message=message, from_email=sender, recipient_list=receiver, html_message=html_message)