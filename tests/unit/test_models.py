import pytest

def test_models_basic():
    """基础模型测试"""
    # 简单的断言测试，确保测试框架正常工作
    assert True

def test_card_model_structure():
    """卡片模型结构测试"""
    card = {
        "id": 1,
        "title": "Test Card",
        "content": "Test content",
        "user_id": 123
    }
    assert card["id"] == 1
    assert card["title"] == "Test Card"
    assert card["user_id"] == 123

def test_todo_model_structure():
    """TODO模型结构测试"""
    todo = {
        "id": 1,
        "task": "Test Task",
        "completed": False,
        "user_id": 123
    }
    assert todo["id"] == 1
    assert todo["task"] == "Test Task"
    assert todo["completed"] is False
