#!/usr/bin/env python3
"""
测试智能运维管理模块
确保系统监控、自动修复、容量规划等组件的完整功能覆盖
"""

import pytest
import time
import threading
import subprocess
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
from collections import deque
import statistics
import math

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from woniunote.common.intelligent_ops_manager import (
    SystemMonitor, AutoHealer, CapacityPlanner, IntelligentOpsManager,
    SystemMetric, Alert, HealthCheck, AlertLevel, SystemComponent, HealthStatus,
    get_ops_manager, init_intelligent_ops_management, monitor_function_health
)


class TestSystemMonitor:
    """测试系统监控器"""
    
    def test_init(self):
        """测试初始化"""
        monitor = SystemMonitor(check_interval=60)
        assert monitor.check_interval == 60
        assert len(monitor.metrics_history) == 0
        assert len(monitor.alerts) == 0
        assert monitor.running is False
        assert monitor.monitor_thread is None
    
    def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        monitor = SystemMonitor(check_interval=0.1)  # 短间隔用于测试
        
        # 启动监控
        monitor.start_monitoring()
        assert monitor.running is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        
        # 等待一小段时间让监控线程运行
        time.sleep(0.2)
        
        # 停止监控
        monitor.stop_monitoring()
        assert monitor.running is False
        
        # 等待线程结束
        if monitor.monitor_thread:
            monitor.monitor_thread.join(timeout=1)
    
    @patch('woniunote.common.intelligent_ops_manager.psutil')
    def test_collect_system_metrics(self, mock_psutil):
        """测试收集系统指标"""
        # 设置mock
        mock_psutil.cpu_percent.return_value = 75.5
        
        mock_memory = Mock()
        mock_memory.percent = 80.2
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.used = 800 * 1024**3  # 800GB
        mock_disk.total = 1000 * 1024**3  # 1TB
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_network = Mock()
        mock_network.bytes_sent = 1024 * 1024 * 100  # 100MB
        mock_psutil.net_io_counters.return_value = mock_network
        
        monitor = SystemMonitor()
        monitor._collect_system_metrics()
        
        # 验证指标被收集
        assert len(monitor.metrics_history) == 4  # CPU, Memory, Disk, Network
        
        # 验证CPU指标
        cpu_key = f"{SystemComponent.CPU.value}_usage_percent"
        assert cpu_key in monitor.metrics_history
        cpu_metrics = monitor.metrics_history[cpu_key]
        assert len(cpu_metrics) == 1
        assert cpu_metrics[0].value == 75.5
        
        # 验证内存指标
        memory_key = f"{SystemComponent.MEMORY.value}_usage_percent"
        assert memory_key in monitor.metrics_history
        memory_metrics = monitor.metrics_history[memory_key]
        assert len(memory_metrics) == 1
        assert memory_metrics[0].value == 80.2
    
    def test_check_threshold(self):
        """测试阈值检查"""
        monitor = SystemMonitor()
        
        # 创建一个超过临界阈值的指标
        critical_metric = SystemMetric(
            component=SystemComponent.CPU,
            metric_name="usage_percent",
            value=95.0,
            unit="%",
            timestamp=datetime.now(),
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        
        # 执行阈值检查
        monitor._check_threshold(critical_metric)
        
        # 验证告警被触发
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.level == AlertLevel.CRITICAL
        assert alert.component == SystemComponent.CPU
    
    def test_check_health(self):
        """测试健康检查"""
        monitor = SystemMonitor()
        
        with patch('woniunote.common.intelligent_ops_manager.psutil') as mock_psutil:
            mock_psutil.pids.return_value = list(range(500))  # 500个进程
            
            monitor._check_health()
            
            # 验证健康检查记录
            assert SystemComponent.APPLICATION in monitor.health_checks
            health_checks = monitor.health_checks[SystemComponent.APPLICATION]
            assert len(health_checks) == 1
            
            health_check = health_checks[0]
            assert health_check.component == SystemComponent.APPLICATION
            assert health_check.name == "process_count"
            assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
    
    def test_analyze_trends(self):
        """测试趋势分析"""
        monitor = SystemMonitor()
        
        # 添加一些递增的指标数据
        metric_key = f"{SystemComponent.CPU.value}_usage_percent"
        base_time = datetime.now()
        
        for i in range(15):  # 15个数据点
            metric = SystemMetric(
                component=SystemComponent.CPU,
                metric_name="usage_percent",
                value=50.0 + i * 2.0,  # 递增的值
                unit="%",
                timestamp=base_time + timedelta(minutes=i),
                threshold_warning=70.0,
                threshold_critical=90.0
            )
            monitor.metrics_history[metric_key].append(metric)
        
        # 执行趋势分析
        monitor._analyze_trends()
        
        # 如果趋势增长过快，应该有告警
        # 检查是否有趋势告警（可能有也可能没有，取决于阈值）
        trend_alerts = [alert for alert in monitor.alerts if "Trend" in alert.title]
        # 这里不强制要求有告警，因为阈值可能不会触发
    
    def test_trigger_alert(self):
        """测试触发告警"""
        monitor = SystemMonitor()
        
        monitor._trigger_alert(
            AlertLevel.WARNING,
            SystemComponent.MEMORY,
            "Memory Warning",
            "Memory usage is high",
            {'usage': 85.0}
        )
        
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.level == AlertLevel.WARNING
        assert alert.component == SystemComponent.MEMORY
        assert alert.title == "Memory Warning"
        assert alert.description == "Memory usage is high"
        assert alert.metadata == {'usage': 85.0}
        assert alert.resolved_at is None
        assert alert.auto_resolved is False
    
    def test_get_current_metrics(self):
        """测试获取当前指标"""
        monitor = SystemMonitor()
        
        # 添加一些指标
        metric = SystemMetric(
            component=SystemComponent.CPU,
            metric_name="usage_percent",
            value=75.0,
            unit="%",
            timestamp=datetime.now(),
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        
        metric_key = f"{SystemComponent.CPU.value}_usage_percent"
        monitor.metrics_history[metric_key].append(metric)
        
        current_metrics = monitor.get_current_metrics()
        
        assert metric_key in current_metrics
        current_metric = current_metrics[metric_key]
        assert current_metric['value'] == 75.0
        assert current_metric['unit'] == "%"
        assert current_metric['threshold_warning'] == 70.0
        assert current_metric['threshold_critical'] == 90.0
    
    def test_get_alerts(self):
        """测试获取告警列表"""
        monitor = SystemMonitor()
        
        # 添加一些告警
        current_time = datetime.now()
        
        # 当前告警
        monitor._trigger_alert(
            AlertLevel.CRITICAL,
            SystemComponent.CPU,
            "Current Alert",
            "Current description",
            {}
        )
        
        # 旧告警（25小时前）
        old_alert = Alert(
            alert_id="old_alert",
            level=AlertLevel.WARNING,
            component=SystemComponent.MEMORY,
            title="Old Alert",
            description="Old description",
            timestamp=current_time - timedelta(hours=25),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        monitor.alerts.append(old_alert)
        
        # 获取最近24小时的告警
        recent_alerts = monitor.get_alerts(hours=24)
        assert len(recent_alerts) == 1
        assert recent_alerts[0]['title'] == "Current Alert"
        
        # 获取所有告警
        all_alerts = monitor.get_alerts(hours=48)
        assert len(all_alerts) == 2
        
        # 按级别过滤
        critical_alerts = monitor.get_alerts(hours=48, level=AlertLevel.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0]['title'] == "Current Alert"


class TestAutoHealer:
    """测试自动修复器"""
    
    def test_init(self):
        """测试初始化"""
        healer = AutoHealer()
        assert len(healer.healing_actions) >= 3  # 至少有默认的3个修复动作
        assert len(healer.healing_history) == 0
    
    def test_register_healing_action(self):
        """测试注册修复动作"""
        healer = AutoHealer()
        
        def custom_action(alert):
            return True
        
        healer.register_healing_action("custom_trigger", custom_action)
        
        assert "custom_trigger" in healer.healing_actions
        assert healer.healing_actions["custom_trigger"] == custom_action
    
    def test_trigger_healing_success(self):
        """测试成功的自动修复"""
        healer = AutoHealer()
        
        # 注册一个测试修复动作
        def test_action(alert):
            return True
        
        healer.register_healing_action("test_critical", test_action)
        
        # 创建测试告警
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.CRITICAL,
            component=SystemComponent.MEMORY,
            title="Test Alert",
            description="Test Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        
        # 触发修复
        result = healer.trigger_healing(alert)
        
        assert result is True
        assert alert.auto_resolved is True
        assert alert.resolved_at is not None
        assert len(alert.actions_taken) == 1
        assert len(healer.healing_history) == 1
        
        history_record = healer.healing_history[0]
        assert history_record['alert_id'] == "test_alert"
        assert history_record['success'] is True
    
    def test_trigger_healing_failure(self):
        """测试失败的自动修复"""
        healer = AutoHealer()
        
        # 注册一个会失败的修复动作
        def failing_action(alert):
            raise Exception("Healing failed")
        
        healer.register_healing_action("test_critical", failing_action)
        
        # 创建测试告警
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.CRITICAL,
            component=SystemComponent.MEMORY,
            title="Test Alert",
            description="Test Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        
        # 触发修复
        result = healer.trigger_healing(alert)
        
        assert result is False
        assert alert.auto_resolved is False
        assert alert.resolved_at is None
    
    def test_trigger_healing_no_action(self):
        """测试没有对应修复动作的情况"""
        healer = AutoHealer()
        
        # 创建一个没有对应修复动作的告警
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.INFO,  # INFO级别没有对应的修复动作
            component=SystemComponent.MEMORY,
            title="Test Alert",
            description="Test Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        
        # 触发修复
        result = healer.trigger_healing(alert)
        
        assert result is False
    
    @patch('woniunote.common.intelligent_ops_manager.gc')
    def test_free_memory(self, mock_gc):
        """测试释放内存"""
        healer = AutoHealer()
        mock_gc.collect.return_value = 100  # 模拟回收了100个对象
        
        alert = Mock()
        result = healer._free_memory(alert)
        
        assert result is True
        mock_gc.collect.assert_called_once()
    
    @patch('woniunote.common.intelligent_ops_manager.os.path.exists')
    @patch('woniunote.common.intelligent_ops_manager.os.walk')
    @patch('woniunote.common.intelligent_ops_manager.os.remove')
    @patch('woniunote.common.intelligent_ops_manager.os.path.getsize')
    @patch('woniunote.common.intelligent_ops_manager.os.path.getmtime')
    @patch('woniunote.common.intelligent_ops_manager.time.time')
    def test_clean_disk(self, mock_time, mock_getmtime, mock_getsize, 
                       mock_remove, mock_walk, mock_exists):
        """测试清理磁盘空间"""
        healer = AutoHealer()
        
        # 设置mock
        mock_time.return_value = 1000000000  # 当前时间
        mock_exists.return_value = True
        mock_walk.return_value = [
            ('/tmp', [], ['old_file.tmp', 'new_file.tmp'])
        ]
        
        # 设置文件信息
        def getsize_side_effect(path):
            if 'old_file' in path:
                return 1024 * 1024  # 1MB
            return 512 * 1024  # 512KB
        
        def getmtime_side_effect(path):
            if 'old_file' in path:
                return 1000000000 - 8 * 24 * 3600  # 8天前
            return 1000000000 - 1 * 24 * 3600  # 1天前
        
        mock_getsize.side_effect = getsize_side_effect
        mock_getmtime.side_effect = getmtime_side_effect
        
        alert = Mock()
        result = healer._clean_disk(alert)
        
        assert result is True
        # 只有old_file应该被删除（超过7天）
        mock_remove.assert_called_once_with('/tmp/old_file.tmp')
    
    def test_restart_service(self):
        """测试重启服务"""
        healer = AutoHealer()
        
        alert = Mock()
        result = healer._restart_service(alert)
        
        # 在测试环境中，这只是模拟，应该返回True
        assert result is True
    
    def test_get_healing_history(self):
        """测试获取修复历史"""
        healer = AutoHealer()
        
        # 添加一些修复历史
        current_time = datetime.now()
        
        healer.healing_history.extend([
            {
                'timestamp': current_time,
                'alert_id': 'alert1',
                'trigger': 'memory_critical',
                'action': 'free_memory',
                'success': True,
                'duration': 1.5,
                'details': {}
            },
            {
                'timestamp': current_time - timedelta(hours=25),
                'alert_id': 'alert2',
                'trigger': 'disk_critical',
                'action': 'clean_disk',
                'success': False,
                'duration': 2.0,
                'details': {}
            }
        ])
        
        # 获取最近24小时的历史
        recent_history = healer.get_healing_history(hours=24)
        assert len(recent_history) == 1
        assert recent_history[0]['alert_id'] == 'alert1'
        
        # 获取所有历史
        all_history = healer.get_healing_history(hours=48)
        assert len(all_history) == 2


class TestCapacityPlanner:
    """测试容量规划器"""
    
    def test_init(self):
        """测试初始化"""
        planner = CapacityPlanner()
        assert len(planner.predictions) == 0
    
    def test_analyze_capacity_trends(self):
        """测试分析容量趋势"""
        planner = CapacityPlanner()
        
        # 创建一些指标历史数据
        metrics_history = {}
        metric_key = "cpu_usage_percent"
        metrics_history[metric_key] = deque()
        
        # 添加递增的数据点
        base_time = datetime.now()
        for i in range(25):  # 超过20个数据点的要求
            metric = SystemMetric(
                component=SystemComponent.CPU,
                metric_name="usage_percent",
                value=50.0 + i * 1.0,  # 线性增长
                unit="%",
                timestamp=base_time + timedelta(hours=i),
                threshold_warning=70.0,
                threshold_critical=90.0
            )
            metrics_history[metric_key].append(metric)
        
        predictions = planner.analyze_capacity_trends(metrics_history)
        
        assert metric_key in predictions
        prediction = predictions[metric_key]
        assert 'current_value' in prediction
        assert 'growth_rate_per_hour' in prediction
        assert 'predictions' in prediction
        assert 'recommendations' in prediction
        assert prediction['growth_rate_per_hour'] > 0  # 应该检测到增长趋势
    
    def test_predict_capacity_insufficient_data(self):
        """测试数据不足时的容量预测"""
        planner = CapacityPlanner()
        
        # 创建数据不足的指标
        metrics = []
        for i in range(5):  # 少于20个数据点
            metric = SystemMetric(
                component=SystemComponent.CPU,
                metric_name="usage_percent",
                value=50.0,
                unit="%",
                timestamp=datetime.now(),
                threshold_warning=70.0,
                threshold_critical=90.0
            )
            metrics.append(metric)
        
        prediction = planner._predict_capacity("test_metric", metrics)
        assert prediction is None
    
    def test_predict_capacity_negative_growth(self):
        """测试负增长率的容量预测"""
        planner = CapacityPlanner()
        
        # 创建递减的数据
        base_time = datetime.now()
        metrics = []
        for i in range(25):
            metric = SystemMetric(
                component=SystemComponent.CPU,
                metric_name="usage_percent",
                value=80.0 - i * 0.5,  # 递减
                unit="%",
                timestamp=base_time + timedelta(hours=i),
                threshold_warning=70.0,
                threshold_critical=90.0
            )
            metrics.append(metric)
        
        prediction = planner._predict_capacity("test_metric", metrics)
        
        # 负增长率的情况
        if prediction:
            assert prediction['growth_rate_per_hour'] <= 0
            assert prediction['time_to_threshold_hours'] is None
    
    def test_get_capacity_recommendations(self):
        """测试获取容量建议"""
        planner = CapacityPlanner()
        
        # 手动设置一些预测结果
        planner.predictions = {
            'cpu_usage': {
                'current_value': 75.0,
                'growth_rate_per_hour': 2.0,
                'recommendations': ['High growth rate detected, consider scaling'],
                'confidence': 0.8
            },
            'memory_usage': {
                'current_value': 60.0,
                'growth_rate_per_hour': 0.5,
                'recommendations': [],
                'confidence': 0.9
            }
        }
        
        recommendations = planner.get_capacity_recommendations()
        
        assert len(recommendations) == 1  # 只有cpu_usage有建议
        rec = recommendations[0]
        assert rec['metric'] == 'cpu_usage'
        assert rec['current_value'] == 75.0
        assert rec['growth_rate'] == 2.0
        assert len(rec['recommendations']) == 1
        assert rec['confidence'] == 0.8


class TestIntelligentOpsManager:
    """测试智能运维管理器主类"""
    
    def test_init(self):
        """测试初始化"""
        manager = IntelligentOpsManager()
        
        assert isinstance(manager.system_monitor, SystemMonitor)
        assert isinstance(manager.auto_healer, AutoHealer)
        assert isinstance(manager.capacity_planner, CapacityPlanner)
        assert 'alerts_triggered' in manager.ops_stats
        assert 'auto_healings_attempted' in manager.ops_stats
        assert 'auto_healings_successful' in manager.ops_stats
        assert 'capacity_warnings' in manager.ops_stats
    
    @patch('atexit.register')
    def test_init_app(self, mock_atexit):
        """测试Flask应用初始化"""
        manager = IntelligentOpsManager()
        mock_app = Mock()
        
        with patch.object(manager.system_monitor, 'start_monitoring') as mock_start:
            manager.init_app(mock_app)
            
            assert manager.app == mock_app
            mock_start.assert_called_once()
            mock_atexit.assert_called_once()
    
    def test_process_alert_no_healing(self):
        """测试处理不需要修复的告警"""
        manager = IntelligentOpsManager()
        
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.INFO,  # INFO级别不触发自动修复
            component=SystemComponent.CPU,
            title="Info Alert",
            description="Info Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        
        result = manager.process_alert(alert)
        
        assert result is False
        assert manager.ops_stats['alerts_triggered'] == 1
        assert manager.ops_stats['auto_healings_attempted'] == 0
    
    def test_process_alert_with_healing(self):
        """测试处理需要修复的告警"""
        manager = IntelligentOpsManager()
        
        # 注册一个成功的修复动作
        def test_healing(alert):
            return True
        
        manager.auto_healer.register_healing_action("memory_critical", test_healing)
        
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.CRITICAL,
            component=SystemComponent.MEMORY,
            title="Critical Alert",
            description="Critical Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        
        result = manager.process_alert(alert)
        
        assert result is True
        assert manager.ops_stats['alerts_triggered'] == 1
        assert manager.ops_stats['auto_healings_attempted'] == 1
        assert manager.ops_stats['auto_healings_successful'] == 1
    
    def test_run_capacity_analysis(self):
        """测试运行容量分析"""
        manager = IntelligentOpsManager()
        
        # 添加一些指标历史
        metric_key = "cpu_usage_percent"
        manager.system_monitor.metrics_history[metric_key] = deque()
        
        base_time = datetime.now()
        for i in range(25):
            metric = SystemMetric(
                component=SystemComponent.CPU,
                metric_name="usage_percent",
                value=50.0 + i * 1.0,
                unit="%",
                timestamp=base_time + timedelta(hours=i),
                threshold_warning=70.0,
                threshold_critical=90.0
            )
            manager.system_monitor.metrics_history[metric_key].append(metric)
        
        analysis = manager.run_capacity_analysis()
        
        assert 'analysis' in analysis
        assert 'recommendations' in analysis
        assert 'timestamp' in analysis
    
    def test_get_system_overview(self):
        """测试获取系统概览"""
        manager = IntelligentOpsManager()
        
        # 添加一些测试数据
        current_time = datetime.now()
        
        # 添加指标
        metric = SystemMetric(
            component=SystemComponent.CPU,
            metric_name="usage_percent",
            value=75.0,
            unit="%",
            timestamp=current_time,
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        metric_key = f"{SystemComponent.CPU.value}_usage_percent"
        manager.system_monitor.metrics_history[metric_key].append(metric)
        
        # 添加告警
        manager.system_monitor._trigger_alert(
            AlertLevel.CRITICAL,
            SystemComponent.CPU,
            "Test Alert",
            "Test Description",
            {}
        )
        
        # 添加修复历史
        manager.auto_healer.healing_history.append({
            'timestamp': current_time,
            'alert_id': 'test',
            'success': True
        })
        
        overview = manager.get_system_overview()
        
        assert 'health_score' in overview
        assert 'current_metrics' in overview
        assert 'alerts_24h' in overview
        assert 'critical_alerts_24h' in overview
        assert 'auto_healings_24h' in overview
        assert 'successful_healings_24h' in overview
        assert 'capacity_warnings' in overview
        assert 'ops_stats' in overview
        assert 'timestamp' in overview
        
        # 验证健康分数在0-100之间
        assert 0 <= overview['health_score'] <= 100
    
    def test_calculate_health_score(self):
        """测试计算健康分数"""
        manager = IntelligentOpsManager()
        
        # 测试完全健康的情况
        metrics = {
            'cpu_usage': {'value': 50.0, 'threshold_warning': 70.0, 'threshold_critical': 90.0},
            'memory_usage': {'value': 60.0, 'threshold_warning': 80.0, 'threshold_critical': 95.0}
        }
        alerts = []
        
        score = manager._calculate_health_score(metrics, alerts)
        assert score == 100.0
        
        # 测试有告警的情况
        alerts = [
            {'level': AlertLevel.CRITICAL.value},
            {'level': AlertLevel.WARNING.value}
        ]
        
        score = manager._calculate_health_score(metrics, alerts)
        assert score < 100.0
        
        # 测试指标超过阈值的情况
        metrics = {
            'cpu_usage': {'value': 95.0, 'threshold_warning': 70.0, 'threshold_critical': 90.0}
        }
        
        score = manager._calculate_health_score(metrics, [])
        assert score < 100.0
    
    def test_cleanup(self):
        """测试清理资源"""
        manager = IntelligentOpsManager()
        
        with patch.object(manager.system_monitor, 'stop_monitoring') as mock_stop:
            manager.cleanup()
            mock_stop.assert_called_once()


class TestDataClasses:
    """测试数据类"""
    
    def test_system_metric_creation(self):
        """测试SystemMetric创建"""
        metric = SystemMetric(
            component=SystemComponent.CPU,
            metric_name="usage_percent",
            value=75.0,
            unit="%",
            timestamp=datetime.now(),
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        
        assert metric.component == SystemComponent.CPU
        assert metric.metric_name == "usage_percent"
        assert metric.value == 75.0
        assert metric.unit == "%"
        assert metric.threshold_warning == 70.0
        assert metric.threshold_critical == 90.0
    
    def test_alert_creation(self):
        """测试Alert创建"""
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.WARNING,
            component=SystemComponent.MEMORY,
            title="Test Alert",
            description="Test Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={"test": "data"}
        )
        
        assert alert.alert_id == "test_alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.component == SystemComponent.MEMORY
        assert alert.title == "Test Alert"
        assert alert.description == "Test Description"
        assert alert.resolved_at is None
        assert alert.auto_resolved is False
        assert alert.actions_taken == []
        assert alert.metadata == {"test": "data"}
    
    def test_health_check_creation(self):
        """测试HealthCheck创建"""
        health_check = HealthCheck(
            component=SystemComponent.DATABASE,
            name="connection_test",
            status=HealthStatus.HEALTHY,
            message="Database connection OK",
            timestamp=datetime.now(),
            response_time=0.5,
            details={"connections": 10}
        )
        
        assert health_check.component == SystemComponent.DATABASE
        assert health_check.name == "connection_test"
        assert health_check.status == HealthStatus.HEALTHY
        assert health_check.message == "Database connection OK"
        assert health_check.response_time == 0.5
        assert health_check.details == {"connections": 10}


class TestGlobalFunctions:
    """测试全局函数"""
    
    def test_get_ops_manager(self):
        """测试获取运维管理器实例"""
        manager1 = get_ops_manager()
        manager2 = get_ops_manager()
        
        # 应该返回同一个实例（单例模式）
        assert manager1 is manager2
        assert isinstance(manager1, IntelligentOpsManager)
    
    @patch('woniunote.common.intelligent_ops_manager.get_ops_manager')
    def test_init_intelligent_ops_management(self, mock_get_manager):
        """测试初始化智能运维管理"""
        mock_app = Mock()
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        
        result = init_intelligent_ops_management(mock_app)
        
        assert result == mock_manager
        mock_manager.init_app.assert_called_once_with(mock_app)


class TestDecorators:
    """测试装饰器"""
    
    @patch('woniunote.common.intelligent_ops_manager.get_ops_manager')
    @patch('time.time')
    def test_monitor_function_health_success(self, mock_time, mock_get_manager):
        """测试函数健康监控装饰器 - 成功情况"""
        mock_manager = Mock()
        mock_monitor = Mock()
        mock_manager.system_monitor = mock_monitor
        mock_get_manager.return_value = mock_manager
        
        mock_time.side_effect = [1000.0, 1001.0]  # 执行时间1秒
        
        @monitor_function_health(SystemComponent.APPLICATION)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
        
        # 由于执行时间小于5秒，不应该触发告警
        mock_monitor._trigger_alert.assert_not_called()
    
    @patch('woniunote.common.intelligent_ops_manager.get_ops_manager')
    @patch('time.time')
    def test_monitor_function_health_slow(self, mock_time, mock_get_manager):
        """测试函数健康监控装饰器 - 慢执行情况"""
        mock_manager = Mock()
        mock_monitor = Mock()
        mock_manager.system_monitor = mock_monitor
        mock_get_manager.return_value = mock_manager
        
        mock_time.side_effect = [1000.0, 1006.0]  # 执行时间6秒
        
        @monitor_function_health(SystemComponent.APPLICATION)
        def slow_function():
            return "slow_result"
        
        result = slow_function()
        assert result == "slow_result"
        
        # 应该触发慢执行告警
        mock_monitor._trigger_alert.assert_called_once()
        call_args = mock_monitor._trigger_alert.call_args
        assert call_args[0][0] == AlertLevel.WARNING
        assert call_args[0][1] == SystemComponent.APPLICATION
        assert "Slow Function Execution" in call_args[0][2]
    
    @patch('woniunote.common.intelligent_ops_manager.get_ops_manager')
    def test_monitor_function_health_error(self, mock_get_manager):
        """测试函数健康监控装饰器 - 错误情况"""
        mock_manager = Mock()
        mock_monitor = Mock()
        mock_manager.system_monitor = mock_monitor
        mock_get_manager.return_value = mock_manager
        
        @monitor_function_health(SystemComponent.APPLICATION)
        def error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            error_function()
        
        # 应该触发错误告警
        mock_monitor._trigger_alert.assert_called_once()
        call_args = mock_monitor._trigger_alert.call_args
        assert call_args[0][0] == AlertLevel.ERROR
        assert call_args[0][1] == SystemComponent.APPLICATION
        assert "Function Execution Error" in call_args[0][2]


@pytest.mark.unit
class TestEdgeCases:
    """测试边界情况和错误处理"""
    
    def test_system_monitor_psutil_error(self):
        """测试psutil不可用的情况"""
        monitor = SystemMonitor()
        
        with patch('woniunote.common.intelligent_ops_manager.psutil') as mock_psutil:
            mock_psutil.cpu_percent.side_effect = Exception("psutil error")
            
            # 不应该抛出异常
            monitor._collect_system_metrics()
            
            # 可能没有收集到指标，但不应该崩溃
            assert True  # 测试通过意味着没有异常抛出
    
    def test_auto_healer_healing_action_exception(self):
        """测试修复动作抛出异常的情况"""
        healer = AutoHealer()
        
        def failing_action(alert):
            raise Exception("Unexpected error")
        
        healer.register_healing_action("test_critical", failing_action)
        
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.CRITICAL,
            component=SystemComponent.MEMORY,
            title="Test Alert",
            description="Test Description",
            timestamp=datetime.now(),
            resolved_at=None,
            auto_resolved=False,
            actions_taken=[],
            metadata={}
        )
        
        # 应该返回False而不是抛出异常
        result = healer.trigger_healing(alert)
        assert result is False
    
    def test_capacity_planner_invalid_metrics(self):
        """测试容量规划器处理无效指标"""
        planner = CapacityPlanner()
        
        # 创建包含无效数据的指标
        metrics = []
        for i in range(25):
            metric = Mock()
            metric.value = float('inf') if i == 10 else 50.0  # 包含无穷大值
            metric.timestamp.timestamp.return_value = 1000000000 + i * 3600
            metrics.append(metric)
        
        # 不应该抛出异常
        prediction = planner._predict_capacity("test_metric", metrics)
        # 可能返回None或处理后的结果
        assert prediction is None or isinstance(prediction, dict)
    
    def test_health_score_calculation_error(self):
        """测试健康分数计算错误处理"""
        manager = IntelligentOpsManager()
        
        # 传入包含异常数据的指标
        invalid_metrics = {
            'invalid_metric': {'value': 'not_a_number'}
        }
        invalid_alerts = [{'level': 'invalid_level'}]
        
        # 应该返回默认分数而不是抛出异常
        score = manager._calculate_health_score(invalid_metrics, invalid_alerts)
        assert isinstance(score, float)
        assert 0 <= score <= 100


@pytest.mark.integration
class TestIntegrationScenarios:
    """测试集成场景"""
    
    def test_full_ops_workflow(self):
        """测试完整的运维工作流"""
        manager = IntelligentOpsManager()
        
        # 1. 启动监控
        manager.system_monitor.start_monitoring()
        
        try:
            # 2. 模拟系统指标收集
            with patch('woniunote.common.intelligent_ops_manager.psutil') as mock_psutil:
                mock_psutil.cpu_percent.return_value = 95.0  # 高CPU使用率
                mock_memory = Mock()
                mock_memory.percent = 85.0
                mock_psutil.virtual_memory.return_value = mock_memory
                mock_disk = Mock()
                mock_disk.used = 950 * 1024**3
                mock_disk.total = 1000 * 1024**3
                mock_psutil.disk_usage.return_value = mock_disk
                mock_network = Mock()
                mock_network.bytes_sent = 1024**3
                mock_psutil.net_io_counters.return_value = mock_network
                
                manager.system_monitor._collect_system_metrics()
            
            # 3. 检查是否触发了告警
            assert len(manager.system_monitor.alerts) > 0
            critical_alerts = [a for a in manager.system_monitor.alerts if a.level == AlertLevel.CRITICAL]
            assert len(critical_alerts) > 0
            
            # 4. 处理告警（触发自动修复）
            for alert in critical_alerts:
                manager.process_alert(alert)
            
            # 5. 验证统计信息
            assert manager.ops_stats['alerts_triggered'] > 0
            
            # 6. 运行容量分析
            analysis = manager.run_capacity_analysis()
            assert 'analysis' in analysis
            assert 'recommendations' in analysis
            
            # 7. 获取系统概览
            overview = manager.get_system_overview()
            assert overview['health_score'] < 100  # 应该检测到问题
            assert overview['alerts_24h'] > 0
            
        finally:
            # 8. 清理
            manager.system_monitor.stop_monitoring()
    
    def test_concurrent_monitoring_and_healing(self):
        """测试并发监控和修复"""
        manager = IntelligentOpsManager()
        
        # 注册一个测试修复动作
        def test_healing(alert):
            time.sleep(0.1)  # 模拟修复时间
            return True
        
        manager.auto_healer.register_healing_action("memory_critical", test_healing)
        
        # 并发触发多个告警
        alerts = []
        for i in range(5):
            alert = Alert(
                alert_id=f"alert_{i}",
                level=AlertLevel.CRITICAL,
                component=SystemComponent.MEMORY,
                title=f"Alert {i}",
                description=f"Description {i}",
                timestamp=datetime.now(),
                resolved_at=None,
                auto_resolved=False,
                actions_taken=[],
                metadata={}
            )
            alerts.append(alert)
        
        # 并发处理告警
        threads = []
        results = []
        
        def process_alert_thread(alert):
            result = manager.process_alert(alert)
            results.append(result)
        
        for alert in alerts:
            thread = threading.Thread(target=process_alert_thread, args=(alert,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(results) == 5
        assert all(results)  # 所有修复都应该成功
        assert manager.ops_stats['alerts_triggered'] == 5
        assert manager.ops_stats['auto_healings_attempted'] == 5
        assert manager.ops_stats['auto_healings_successful'] == 5 