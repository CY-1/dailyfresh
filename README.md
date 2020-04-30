# dailyfresh
B2B by Django3.0.5

黑马程序员Django练习项目重构到到新版本Django3.0.5
## 用户
- ### 用户注册
    - 注册用户后发送激活邮件, 点击激活邮件里面对应的网页链接可激活账户
    - 激活链接的身份标识用itsdangerous的TimedJSONWebSignatureSerializer加密
    - celery任务队列来发送激活邮件, redis作为中间人
- ### 用户登录
    - 使用自带的user认证系统
    - redis作为session缓存
    - 在需要判断登录的视图用Mixin方法,以此检测是否登录
- ### 用户中心
    - redis作为储存历史游览记录   
    - 可以上传多个地址 设置默认地址待补充
- ### 搜索
    - 采用haystack框架 jieba分词
    - 为了兼容新版本Django模块 安装six模块 复制到了django.utils里面
- ### 购物车
    - 后台通过ajax添加购物车
    - 存在redis中
