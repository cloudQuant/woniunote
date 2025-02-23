import time

from flask import Blueprint, render_template, request, jsonify
import os
import traceback
from woniunote.common.utils import compress_image

ueditor = Blueprint("ueditor", __name__)


@ueditor.route('/uedit', methods=['GET', 'POST'])
def uedit():
    try:
        # 根据UEditor的接口定义规则，如果前端参数为action=config，
        # 则表示试图请求后台的config.json文件，请求成功则说明后台接口能正常工作
        param = request.args.get('action')
        if request.method == 'GET' and param == 'config':
            config_json = 'config.json'
            return render_template(config_json)

        # 构造上传图片的接口
        elif request.method == 'POST' and request.args.get('action') == 'uploadimage':
            f = request.files['upfile']  # 获取前端图片文件数据
            filename = f.filename

            # 为上传来的文件生成统一的文件名
            suffix = filename.split('.')[-1]  # 取得文件的后缀名
            newname = time.strftime('%Y%m%d_%H%M%S.' + suffix)
            f.save('./resource/upload/' + newname)  # 保存图片

            # 对图片进行压缩，按照1200像素宽度为准，并覆盖原始文件
            source = dest = './resource/upload/' + newname
            compress_image(source, dest, 1200)

            result = {'state': 'SUCCESS', "url": f"/upload/{newname}", 'title': filename, 'original': filename}  # 构造响应数据

            return jsonify(result)  # 以JSON数据格式返回响应，供前端编辑器引用

        # 列出所有图片给前端浏览
        elif request.method == 'GET' and param == 'listimage':
            m_list = []
            filelist = os.listdir('./resource/upload')
            # 将所有图片构建成可访问的URL地址并添加到列表中
            for filename in filelist:
                if filename.lower().endswith('.png') or filename.lower().endswith('.jpg'):
                    m_list.append({'url': '/upload/%s' % filename})

            # 根据listimage接口规则构建响应数据
            result = {'state': 'SUCCESS', 'list': m_list, 'start': 0, 'total': 50}
            return jsonify(result)
    except Exception as e:
        print(e)
        traceback.print_exc()
