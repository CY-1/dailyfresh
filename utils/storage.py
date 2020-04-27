from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    '''fast_dfs文件存储类'''

    def _open(self, name, mode='rb'):
        '''打开文件使用'''
        pass

    def _save(self, name, content):
        '''保存文件使用'''
        # name选择的上传文件的名字
        # content是File对象 包涵上传文件内容
        # 下面的路径是相对于项目的
        client = Fdfs_client('.utils/fdfs/client.conf')
        # 上传文件 返回一个字典
        # @return dict {
        #     'Group name'      : group_name,
        #     'Remote file_id'  : remote_file_id,
        #     'Status'          : 'Upload successed.',
        #     'Local file name' : '',
        #     'Uploaded size'   : upload_size,
        #     'Storage IP'      : storage_ip
        # } if success else None
        res = client.upload_by_buffer(content.read())
        if res.get("Status") !='Upload successed.':
            # 上传失败
            raise Exception("上传文件失败")
        else:
            # 获取返回的remote_file_id
            filename = res.get("Remote file_id")
        return filename

    def exists(self, name):
        '''判断文件是否可用'''
        # 因为我们存在fdfs里面会自动区别是否一样的文件
        return False