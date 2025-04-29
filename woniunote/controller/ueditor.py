import time
import uuid
import os

from flask import Blueprint, render_template, request, jsonify, session
import traceback
from woniunote.common.utils import compress_image
from woniunote.common.simple_logger import get_simple_logger

ueditor = Blueprint("ueditor", __name__)

# 初始化日志记录器
ueditor_logger = get_simple_logger('ueditor')

# 生成唯一的跟踪ID
def get_ueditor_trace_id():
    """
    生成唯一的跟踪ID用于日志关联
    
    Returns:
        str: 唯一的跟踪ID
    """
    return f"ueditor_{uuid.uuid4().hex}"


@ueditor.route('/uedit', methods=['GET', 'POST'])
def uedit():
    """
    UEditor编辑器接口函数
    
    处理UEditor编辑器的各种请求，包括配置获取、图片上传和图片列表获取
    
    Returns:
        Response: 根据请求类型返回相应的响应
    """
    # 生成跟踪ID
    trace_id = get_ueditor_trace_id()
    
    # 记录UEditor请求
    ueditor_logger.info("UEditor请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'action': request.args.get('action'),
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
    })
    
    try:
        # 根据UEditor的接口定义规则，如果前端参数为action=config，
        # 则表示试图请求后台的config.json文件，请求成功则说明后台接口能正常工作
        param = request.args.get('action')
        
        # 处理配置请求
        if request.method == 'GET' and param == 'config':
            ueditor_logger.info("请求UEditor配置", {
                'trace_id': trace_id,
                'action': 'config'
            })
            
            config_json = 'config.json'
            response = render_template(config_json)
            
            ueditor_logger.info("返回UEditor配置成功", {
                'trace_id': trace_id,
                'config_file': config_json,
                'response_length': len(response) if response else 0
            })
            
            return response

        # 构造上传图片的接口
        elif request.method == 'POST' and request.args.get('action') == 'uploadimage':
            ueditor_logger.info("开始上传图片", {
                'trace_id': trace_id,
                'action': 'uploadimage',
                'content_length': request.content_length,
                'content_type': request.content_type
            })
            
            # 获取前端图片文件数据
            f = request.files['upfile']
            filename = f.filename
            
            ueditor_logger.info("接收到图片文件", {
                'trace_id': trace_id,
                'filename': filename,
                'file_size': f.content_length if hasattr(f, 'content_length') else -1
            })

            # 为上传来的文件生成统一的文件名
            suffix = filename.split('.')[-1]  # 取得文件的后缀名
            newname = time.strftime('%Y%m%d_%H%M%S.' + suffix)
            save_path = './resource/upload/' + newname
            
            # 保存图片
            try:
                f.save(save_path)
                ueditor_logger.info("图片保存成功", {
                    'trace_id': trace_id,
                    'original_filename': filename,
                    'new_filename': newname,
                    'save_path': save_path
                })
            except Exception as save_error:
                ueditor_logger.error("图片保存失败", {
                    'trace_id': trace_id,
                    'original_filename': filename,
                    'new_filename': newname,
                    'save_path': save_path,
                    'error': str(save_error),
                    'error_type': type(save_error).__name__
                })
                raise save_error

            # 对图片进行压缩，按照1200像素宽度为准，并覆盖原始文件
            source = dest = save_path
            try:
                compress_image(source, dest, 1200)
                ueditor_logger.info("图片压缩成功", {
                    'trace_id': trace_id,
                    'source': source,
                    'dest': dest,
                    'width': 1200
                })
            except Exception as compress_error:
                ueditor_logger.error("图片压缩失败", {
                    'trace_id': trace_id,
                    'source': source,
                    'dest': dest,
                    'width': 1200,
                    'error': str(compress_error),
                    'error_type': type(compress_error).__name__
                })
                # 即使压缩失败也继续返回原图片URL

            # 构造响应数据
            result = {'state': 'SUCCESS', "url": f"/upload/{newname}", 'title': filename, 'original': filename}
            
            ueditor_logger.info("图片上传完成", {
                'trace_id': trace_id,
                'url': f"/upload/{newname}",
                'title': filename,
                'original': filename
            })
            
            # 以JSON数据格式返回响应，供前端编辑器引用
            return jsonify(result)

        # 列出所有图片给前端浏览
        elif request.method == 'GET' and param == 'listimage':
            ueditor_logger.info("请求图片列表", {
                'trace_id': trace_id,
                'action': 'listimage'
            })
            
            m_list = []
            upload_dir = './resource/upload'
            
            try:
                filelist = os.listdir(upload_dir)
                # 将所有图片构建成可访问的URL地址并添加到列表中
                for filename in filelist:
                    if filename.lower().endswith('.png') or filename.lower().endswith('.jpg'):
                        m_list.append({'url': '/upload/%s' % filename})
                
                ueditor_logger.info("读取图片列表成功", {
                    'trace_id': trace_id,
                    'total_files': len(filelist),
                    'image_count': len(m_list)
                })
            except Exception as list_error:
                ueditor_logger.error("读取图片列表失败", {
                    'trace_id': trace_id,
                    'upload_dir': upload_dir,
                    'error': str(list_error),
                    'error_type': type(list_error).__name__
                })
                # 如果读取失败，返回空列表

            # 根据listimage接口规则构建响应数据
            result = {'state': 'SUCCESS', 'list': m_list, 'start': 0, 'total': len(m_list)}
            
            ueditor_logger.info("返回图片列表", {
                'trace_id': trace_id,
                'state': 'SUCCESS',
                'image_count': len(m_list),
                'start': 0,
                'total': len(m_list)
            })
            
            return jsonify(result)
        
        # 处理未知操作
        else:
            ueditor_logger.warning("未知的UEditor操作", {
                'trace_id': trace_id,
                'method': request.method,
                'action': param
            })
            
            return jsonify({'state': 'FAIL', 'message': 'Unknown action'})
            
    except Exception as e:
        # 记录异常
        ueditor_logger.error("UEditor操作异常", {
            'trace_id': trace_id,
            'method': request.method,
            'action': request.args.get('action'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        
        # 返回错误响应
        return jsonify({'state': 'ERROR', 'message': str(e)})
