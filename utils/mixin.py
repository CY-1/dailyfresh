from django.contrib.auth.decorators import login_required

class LoginRequireMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用cls父类的as_view 因为调用第二次所以调用view
        view = super(LoginRequireMixin, cls).as_view(**initkwargs)
        return login_required(view)

