#!/usr/bin/env python3
"""
文章加载性能测试脚本
比较原版和优化版的性能差异
"""

import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_article_loading_performance():
    """测试文章加载性能"""
    
    # 测试配置
    BASE_URL = "http://localhost:5000"
    ARTICLE_ID = 1  # 测试文章ID
    TEST_ROUNDS = 10  # 测试轮数
    CONCURRENT_USERS = 5  # 并发用户数
    
    print("🚀 文章加载性能测试")
    print("=" * 50)
    
    # 测试原版文章加载
    print("\n📊 测试原版文章加载...")
    original_times = test_endpoint(f"{BASE_URL}/article/{ARTICLE_ID}", TEST_ROUNDS, CONCURRENT_USERS)
    
    # 测试优化版文章加载
    print("\n⚡ 测试优化版文章加载...")
    optimized_times = test_endpoint(f"{BASE_URL}/article/fast/{ARTICLE_ID}", TEST_ROUNDS, CONCURRENT_USERS)
    
    # 分析结果
    print("\n📈 性能分析结果")
    print("=" * 50)
    
    if original_times and optimized_times:
        analyze_performance(original_times, optimized_times)
    else:
        print("❌ 测试失败，请检查服务器是否运行")

def test_endpoint(url, rounds, concurrent_users):
    """测试指定端点的性能"""
    response_times = []
    
    for round_num in range(rounds):
        print(f"  轮次 {round_num + 1}/{rounds}")
        
        # 并发请求
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request, url) for _ in range(concurrent_users)]
            
            for future in as_completed(futures):
                response_time = future.result()
                if response_time is not None:
                    response_times.append(response_time)
    
    return response_times

def make_request(url):
    """发起HTTP请求并测量响应时间"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            return (end_time - start_time) * 1000  # 转换为毫秒
        else:
            print(f"    ❌ HTTP {response.status_code}: {url}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"    ❌ 请求失败: {e}")
        return None

def analyze_performance(original_times, optimized_times):
    """分析性能数据"""
    
    # 计算统计数据
    original_stats = calculate_stats(original_times)
    optimized_stats = calculate_stats(optimized_times)
    
    # 输出原版统计
    print("\n📊 原版性能统计:")
    print_stats("原版", original_stats)
    
    # 输出优化版统计
    print("\n⚡ 优化版性能统计:")
    print_stats("优化版", optimized_stats)
    
    # 性能对比
    print("\n🔄 性能对比:")
    print("-" * 30)
    
    improvement_avg = ((original_stats['avg'] - optimized_stats['avg']) / original_stats['avg']) * 100
    improvement_p95 = ((original_stats['p95'] - optimized_stats['p95']) / original_stats['p95']) * 100
    improvement_p99 = ((original_stats['p99'] - optimized_stats['p99']) / original_stats['p99']) * 100
    
    print(f"平均响应时间提升: {improvement_avg:.1f}%")
    print(f"P95响应时间提升: {improvement_p95:.1f}%")
    print(f"P99响应时间提升: {improvement_p99:.1f}%")
    
    # 性能等级评估
    print("\n🏆 性能等级评估:")
    print("-" * 30)
    
    def get_performance_grade(avg_time):
        if avg_time < 200:
            return "优秀 🟢"
        elif avg_time < 500:
            return "良好 🟡"
        elif avg_time < 1000:
            return "一般 🟠"
        else:
            return "较差 🔴"
    
    print(f"原版性能等级: {get_performance_grade(original_stats['avg'])}")
    print(f"优化版性能等级: {get_performance_grade(optimized_stats['avg'])}")
    
    # 建议
    print("\n💡 优化建议:")
    print("-" * 30)
    
    if improvement_avg > 50:
        print("✅ 优化效果显著，建议部署优化版本")
    elif improvement_avg > 20:
        print("✅ 优化效果良好，建议部署优化版本")
    elif improvement_avg > 0:
        print("⚠️ 优化效果一般，可考虑进一步优化")
    else:
        print("❌ 优化效果不明显，需要重新评估优化策略")
    
    if optimized_stats['avg'] > 500:
        print("⚠️ 响应时间仍然较高，建议检查:")
        print("   - 数据库查询优化")
        print("   - 缓存命中率")
        print("   - 网络延迟")
        print("   - 服务器资源")

def calculate_stats(times):
    """计算统计数据"""
    if not times:
        return None
    
    times_sorted = sorted(times)
    return {
        'count': len(times),
        'avg': statistics.mean(times),
        'median': statistics.median(times),
        'min': min(times),
        'max': max(times),
        'p95': times_sorted[int(len(times_sorted) * 0.95)],
        'p99': times_sorted[int(len(times_sorted) * 0.99)],
        'std': statistics.stdev(times) if len(times) > 1 else 0
    }

def print_stats(name, stats):
    """打印统计信息"""
    if not stats:
        print(f"{name}: 无数据")
        return
    
    print(f"  请求总数: {stats['count']}")
    print(f"  平均响应时间: {stats['avg']:.1f}ms")
    print(f"  中位数响应时间: {stats['median']:.1f}ms")
    print(f"  最小响应时间: {stats['min']:.1f}ms")
    print(f"  最大响应时间: {stats['max']:.1f}ms")
    print(f"  P95响应时间: {stats['p95']:.1f}ms")
    print(f"  P99响应时间: {stats['p99']:.1f}ms")
    print(f"  标准差: {stats['std']:.1f}ms")

def test_cache_performance():
    """测试缓存性能"""
    print("\n🗄️ 缓存性能测试")
    print("=" * 30)
    
    try:
        # 测试缓存API
        cache_url = "http://localhost:5000/article/api/hot-articles"
        
        # 第一次请求（缓存未命中）
        start_time = time.time()
        response1 = requests.get(cache_url, timeout=10)
        time1 = (time.time() - start_time) * 1000
        
        # 第二次请求（缓存命中）
        start_time = time.time()
        response2 = requests.get(cache_url, timeout=10)
        time2 = (time.time() - start_time) * 1000
        
        if response1.status_code == 200 and response2.status_code == 200:
            print(f"首次请求（缓存未命中）: {time1:.1f}ms")
            print(f"第二次请求（缓存命中）: {time2:.1f}ms")
            
            if time2 < time1:
                improvement = ((time1 - time2) / time1) * 100
                print(f"缓存加速效果: {improvement:.1f}%")
            else:
                print("缓存效果不明显")
        else:
            print("缓存测试失败")
            
    except Exception as e:
        print(f"缓存测试异常: {e}")

if __name__ == "__main__":
    print("文章加载性能测试工具")
    print("请确保服务器在 http://localhost:5000 运行")
    
    # 检查服务器是否可用
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        print("✅ 服务器连接正常")
    except:
        print("❌ 无法连接到服务器，请先启动应用")
        sys.exit(1)
    
    # 运行性能测试
    test_article_loading_performance()
    
    # 运行缓存测试
    test_cache_performance()
    
    print("\n🎉 测试完成！")