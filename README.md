# dailyfresh
B2B by Django3.0.5

黑马程序员Django练习项目重构到到新版本Django3.0.5
## 用户登录
- 注册用户后发送激活邮件, 点击激活邮件里面对应的网页链接可激活账户
- 激活链接的身份标识用itsdangerous的TimedJSONWebSignatureSerializer加密
- celery任务队列来发送激活邮件, redis作为中间人

