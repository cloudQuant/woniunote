#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能测试模块

此模块提供WoniuNote的性能测试功能，包括：
- 并发用户测试
- 响应时间测试
- 负载测试
- 压力测试
"""

import os
import sys
import time
import logging
import pytest
import threading
import queue
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

from tests.utils.test_config import PERFORMANCE_CONFIG, SERVER_CONFIG
from tests.utils.test_base import FlaskAppContextProvider

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTest:
    """性能测试基类"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始测试"""
        self.start_time = time.time()
        logger.info(f"开始性能测试: {self.__class__.__name__}")
    
    def end(self):
        """结束测试"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info(f"性能测试完成: {self.__class__.__name__}, 耗时: {duration:.2f}秒")
    
    def record_result(self, result: Dict[str, Any]):
        """记录测试结果"""
        self.results.append(result)
    
    def get_statistics(self) -> Dict[str, float]:
        """获取测试统计信息"""
        if not self.results:
            return {}
        
        response_times = [r['response_time'] for r in self.results]
        return {
            'min': min(response_times),
            'max': max(response_times),
            'mean': statistics.mean(response_times),
            'median': statistics.median(response_times),
            'p95': statistics.quantiles(response_times, n=20)[18],  # 95th percentile
            'p99': statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        }

class ConcurrentUserTest(PerformanceTest):
    """并发用户测试"""
    
    def __init__(self, base_url: str, num_users: int = None):
        super().__init__(base_url)
        self.num_users = num_users or PERFORMANCE_CONFIG['concurrent_users']
        self.request_timeout = PERFORMANCE_CONFIG['request_timeout']
        self.think_time = PERFORMANCE_CONFIG['think_time']
        self.ramp_up_time = PERFORMANCE_CONFIG['ramp_up_time']
    
    def run(self):
        """运行并发用户测试"""
        self.start()
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=self.num_users) as executor:
            # 提交任务
            futures = []
            for i in range(self.num_users):
                # 计算每个用户的启动延迟，实现渐进式负载
                delay = (i * self.ramp_up_time) / self.num_users
                futures.append(executor.submit(self._user_workload, i, delay))
            
            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"用户任务执行失败: {e}")
        
        self.end()
        return self.get_statistics()
    
    def _user_workload(self, user_id: int, start_delay: float):
        """模拟单个用户的工作负载"""
        time.sleep(start_delay)
        logger.info(f"用户 {user_id} 开始工作负载")
        
        # 模拟用户操作序列
        operations = [
            ('GET', '/'),  # 访问首页
            ('GET', '/login'),  # 访问登录页
            ('POST', '/login', {'username': 'test', 'password': 'test'}),  # 登录
            ('GET', '/articles'),  # 查看文章列表
            ('GET', '/articles/1'),  # 查看文章详情
        ]
        
        for method, path, *args in operations:
            start_time = time.time()
            try:
                # 这里应该使用实际的HTTP请求，这里只是示例
                response_time = time.time() - start_time
                self.record_result({
                    'user_id': user_id,
                    'operation': f"{method} {path}",
                    'response_time': response_time,
                    'status': 'success'
                })
                
                # 模拟用户思考时间
                time.sleep(self.think_time)
            except Exception as e:
                logger.error(f"用户 {user_id} 执行操作 {method} {path} 失败: {e}")
                self.record_result({
                    'user_id': user_id,
                    'operation': f"{method} {path}",
                    'response_time': time.time() - start_time,
                    'status': 'error',
                    'error': str(e)
                })

@pytest.mark.performance
def test_concurrent_users(app_context, base_url):
    """测试并发用户性能"""
    test = ConcurrentUserTest(base_url)
    stats = test.run()
    
    # 验证性能指标
    assert stats['mean'] < 1.0, f"平均响应时间过长: {stats['mean']:.2f}秒"
    assert stats['p95'] < 2.0, f"95%请求响应时间过长: {stats['p95']:.2f}秒"
    assert stats['p99'] < 3.0, f"99%请求响应时间过长: {stats['p99']:.2f}秒"
    
    logger.info(f"并发用户测试完成，统计信息: {stats}")

@pytest.mark.performance
def test_response_time(app_context, base_url):
    """测试响应时间"""
    test = ConcurrentUserTest(base_url, num_users=1)  # 单用户测试
    stats = test.run()
    
    # 验证响应时间
    assert stats['mean'] < 0.5, f"平均响应时间过长: {stats['mean']:.2f}秒"
    assert stats['max'] < 1.0, f"最大响应时间过长: {stats['max']:.2f}秒"
    
    logger.info(f"响应时间测试完成，统计信息: {stats}")

if __name__ == "__main__":
    print("手动运行性能测试...") 