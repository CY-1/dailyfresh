# 定义索引类
from haystack import indexes
# 导入模型类
from goods.models import GoodsSKU


# 指定对于某个类的某些数据建立索引
# 索引类名格式：模型类名+index
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    # 索引字段 use_template=True 根据哪些字段建立字段 把说明放在一个文件中
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return GoodsSKU

    # 建立索引的数据
    def index_queryset(self, using=None):
        # 返回什么 对什么建立索引
        return self.get_model().objects.all()