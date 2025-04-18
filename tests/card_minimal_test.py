#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
极简卡片功能测试

这个脚本完全避开pytest框架，以独立程序的方式验证卡片功能
专注于测试最基础的卡片操作，确保模型和控制器正常工作
"""

import os
import sys
import logging
import datetime
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('card_minimal_tester')

# 确保能找到项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

class TestResult:
    """测试结果类"""
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
    
    def record_pass(self, test_name):
        """记录测试通过"""
        self.tests_run += 1
        self.tests_passed += 1
        logger.info(f"✅ 通过: {test_name}")
    
    def record_fail(self, test_name, error=None):
        """记录测试失败"""
        self.tests_run += 1
        self.tests_failed += 1
        failure_info = {'test': test_name, 'error': str(error) if error else None}
        self.failures.append(failure_info)
        logger.error(f"❌ 失败: {test_name}")
        if error:
            logger.error(f"错误: {error}")
    
    def summary(self):
        """返回测试结果摘要"""
        return f"运行了{self.tests_run}个测试，通过{self.tests_passed}个，失败{self.tests_failed}个"

def run_tests():
    """运行所有测试"""
    result = TestResult()
    
    # 导入必要的模块
    try:
        from woniunote.app import app
        from woniunote.models.card import Card, CardCategory
        from woniunote.common.database import db
    except ImportError as e:
        logger.critical(f"导入必要模块失败: {e}")
        return 1
    
    # 准备测试环境和数据
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = None
    app.config['WTF_CSRF_ENABLED'] = False
    
    # 测试数据
    test_resources = []
    
    # ===== 测试1: 验证数据库连接 =====
    def test_database_connection():
        """验证数据库连接正常"""
        with app.app_context():
            try:
                db.engine.connect()
                return True, "数据库连接成功"
            except Exception as e:
                return False, f"数据库连接失败: {e}"
    
    success, message = test_database_connection()
    if success:
        result.record_pass("数据库连接测试")
    else:
        result.record_fail("数据库连接测试", message)
        # 如果数据库连接失败，后续测试无法进行
        return 1
    
    # ===== 测试2: 创建和查询卡片分类 =====
    def test_create_query_category():
        """测试创建和查询卡片分类"""
        try:
            with app.app_context():
                # 创建唯一分类名
                cat_name = f"测试分类_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                category = CardCategory(name=cat_name)
                db.session.add(category)
                db.session.commit()
                
                # 记录资源ID以便清理
                category_id = category.id
                test_resources.append(("category", category_id))
                
                # 查询验证
                queried = CardCategory.query.filter_by(id=category_id).first()
                if not queried or queried.name != cat_name:
                    return False, "分类查询结果不一致"
                
                return True, f"分类创建和查询成功，ID: {category_id}"
        except Exception as e:
            return False, f"分类创建或查询失败: {e}"
    
    success, message = test_create_query_category()
    if success:
        result.record_pass("创建查询分类测试")
    else:
        result.record_fail("创建查询分类测试", message)
    
    # ===== 测试3: 创建和查询卡片 =====
    def test_create_query_card():
        """测试创建和查询卡片"""
        try:
            with app.app_context():
                # 获取一个存在的分类
                category = CardCategory.query.first()
                if not category:
                    return False, "无可用分类"
                
                # 创建卡片
                card_title = f"测试卡片_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                card = Card(
                    headline=card_title,
                    createtime=datetime.datetime.now(),
                    updatetime=datetime.datetime.now(),
                    cardcategory_id=category.id,
                    usedtime=0,
                    type=1
                )
                db.session.add(card)
                db.session.commit()
                
                # 记录资源ID以便清理
                card_id = card.id
                test_resources.append(("card", card_id))
                
                # 查询验证
                queried = Card.query.filter_by(id=card_id).first()
                if not queried or queried.headline != card_title:
                    return False, "卡片查询结果不一致"
                
                return True, f"卡片创建和查询成功，ID: {card_id}"
        except Exception as e:
            return False, f"卡片创建或查询失败: {e}"
    
    success, message = test_create_query_card()
    if success:
        result.record_pass("创建查询卡片测试")
    else:
        result.record_fail("创建查询卡片测试", message)
    
    # ===== 测试4: 卡片更新 =====
    def test_update_card():
        """测试更新卡片"""
        try:
            with app.app_context():
                # 找到最后创建的卡片
                card = None
                for res_type, res_id in test_resources:
                    if res_type == "card":
                        card = Card.query.filter_by(id=res_id).first()
                        if card:
                            break
                
                if not card:
                    return False, "找不到可用于测试的卡片"
                
                # 记录原标题
                original_title = card.headline
                
                # 更新标题
                new_title = f"{original_title}_已更新"
                card.headline = new_title
                db.session.commit()
                
                # 验证更新
                updated = Card.query.filter_by(id=card.id).first()
                if not updated or updated.headline != new_title:
                    return False, "卡片更新失败"
                
                return True, "卡片更新成功"
        except Exception as e:
            return False, f"卡片更新失败: {e}"
    
    success, message = test_update_card()
    if success:
        result.record_pass("更新卡片测试")
    else:
        result.record_fail("更新卡片测试", message)
    
    # ===== 测试5: 卡片开始和结束 =====
    def test_card_begin_end():
        """测试卡片开始和结束功能"""
        try:
            with app.app_context():
                # 找到最后创建的卡片
                card = None
                for res_type, res_id in test_resources:
                    if res_type == "card":
                        card = Card.query.filter_by(id=res_id).first()
                        if card:
                            break
                
                if not card:
                    return False, "找不到可用于测试的卡片"
                
                # 设置开始时间
                card.begintime = datetime.datetime.now()
                db.session.commit()
                
                # 验证开始时间
                begun_card = Card.query.filter_by(id=card.id).first()
                if not begun_card or begun_card.begintime is None:
                    return False, "卡片开始时间设置失败"
                
                # 设置结束时间并清除开始时间
                begun_card.endtime = datetime.datetime.now()
                begun_card.begintime = None
                begun_card.usedtime = 60  # 60秒
                db.session.commit()
                
                # 验证结束时间
                ended_card = Card.query.filter_by(id=card.id).first()
                if (not ended_card or 
                    ended_card.endtime is None or 
                    ended_card.begintime is not None or
                    ended_card.usedtime != 60):
                    return False, "卡片结束时间设置失败"
                
                return True, "卡片开始结束功能正常"
        except Exception as e:
            return False, f"卡片开始结束测试失败: {e}"
    
    success, message = test_card_begin_end()
    if success:
        result.record_pass("卡片开始结束测试")
    else:
        result.record_fail("卡片开始结束测试", message)
    
    # 清理测试资源
    try:
        with app.app_context():
            for res_type, res_id in reversed(test_resources):
                try:
                    if res_type == "card":
                        card = Card.query.filter_by(id=res_id).first()
                        if card:
                            db.session.delete(card)
                    elif res_type == "category":
                        # 不删除ID为1或2的受保护分类
                        if res_id in [1, 2]:
                            continue
                        category = CardCategory.query.filter_by(id=res_id).first()
                        if category:
                            db.session.delete(category)
                except Exception as e:
                    logger.warning(f"清理资源{res_type}:{res_id}失败: {e}")
            
            db.session.commit()
    except Exception as e:
        logger.error(f"清理测试资源时出错: {e}")
    
    # 输出测试结果摘要
    logger.info("\n=== 测试结果摘要 ===")
    logger.info(result.summary())
    
    if result.tests_failed > 0:
        for failure in result.failures:
            logger.error(f"失败的测试: {failure['test']}")
            if failure['error']:
                logger.error(f"错误: {failure['error']}")
        
        return 1
    
    logger.info("🎉 所有测试通过！")
    return 0

if __name__ == "__main__":
    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"测试执行过程出错: {e}")
        traceback.print_exc()
        sys.exit(1)
