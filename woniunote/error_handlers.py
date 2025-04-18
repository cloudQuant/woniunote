from flask import render_template, make_response, jsonify

# 添加全局错误处理函数
def register_error_handlers(app):
    """为Flask应用注册全局错误处理函数"""
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error-404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error-500.html'), 500
    
    @app.errorhandler(TypeError)
    def handle_type_error(e):
        """处理类型错误，特别是返回整数而不是响应对象的错误"""
        if "did not return a valid response" in str(e):
            app.logger.error(f"视图函数返回了无效响应: {str(e)}")
            return render_template('error-500.html'), 500
        return render_template('error-500.html'), 500
