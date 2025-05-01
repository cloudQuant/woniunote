import functools
import time
import traceback
import uuid
from flask import request, session
from woniunote.common.simple_logger import get_simple_logger

# 线程本地存储，用于跟踪ID
_thread_local_trace_id = {}

# 生成跟踪ID
def generate_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID
def get_trace_id():
    if 'trace_id' not in _thread_local_trace_id:
        _thread_local_trace_id['trace_id'] = generate_trace_id()
    return _thread_local_trace_id['trace_id']

def log_function(logger=None, log_args=True, log_return=True, log_exception=True, performance=True):
    """
    通用函数/方法日志装饰器，自动记录trace_id、参数、返回值、异常、耗时。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_simple_logger(func.__module__)
            trace_id = get_trace_id()
            func_name = f"{func.__module__}.{func.__qualname__}"
            # 记录参数
            if log_args:
                logger.info(f"调用: {func_name}", {'trace_id': trace_id, 'args': str(args), 'kwargs': str(kwargs)})
            start = time.time() if performance else None
            try:
                result = func(*args, **kwargs)
                if log_return:
                    logger.info(f"返回: {func_name}", {'trace_id': trace_id, 'result': str(result)})
                return result
            except Exception as e:
                if log_exception:
                    logger.error(f"异常: {func_name}: {e}", {'trace_id': trace_id, 'exception': traceback.format_exc()})
                raise
            finally:
                if performance and start is not None:
                    elapsed = (time.time() - start) * 1000
                    logger.info(f"性能: {func_name} 耗时 {elapsed:.2f}ms", {'trace_id': trace_id, 'elapsed_ms': elapsed})
        return wrapper
    return decorator
