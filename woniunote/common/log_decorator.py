import functools
import time
import traceback
from woniunote.common.logging_util import get_logger, get_trace_id
from flask import request, session

def log_function(logger=None, log_args=True, log_return=True, log_exception=True, performance=True):
    """
    通用函数/方法日志装饰器，自动记录trace_id、参数、返回值、异常、耗时。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            trace_id = get_trace_id()
            func_name = f"{func.__module__}.{func.__qualname__}"
            # 记录参数
            if log_args:
                logger.info(f"调用: {func_name}", extra={'extra_data': {'trace_id': trace_id, 'args': str(args), 'kwargs': str(kwargs)}})
            start = time.time() if performance else None
            try:
                result = func(*args, **kwargs)
                if log_return:
                    logger.info(f"返回: {func_name}", extra={'extra_data': {'trace_id': trace_id, 'result': str(result)}})
                return result
            except Exception as e:
                if log_exception:
                    logger.error(f"异常: {func_name}: {e}", exc_info=True, extra={'extra_data': {'trace_id': trace_id, 'exception': traceback.format_exc()}})
                raise
            finally:
                if performance and start is not None:
                    elapsed = (time.time() - start) * 1000
                    logger.info(f"性能: {func_name} 耗时 {elapsed:.2f}ms", extra={'extra_data': {'trace_id': trace_id, 'elapsed_ms': elapsed}})
        return wrapper
    return decorator
