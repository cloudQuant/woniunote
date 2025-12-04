"""
后端 API 基础测试
测试核心功能是否正常工作
"""
import pytest
import httpx
import asyncio

BASE_URL = "http://localhost:8888"

class TestHealthAPI:
    """健康检查测试"""
    
    def test_root(self):
        """测试根路径"""
        response = httpx.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "WoniuNote" in data["message"]
    
    def test_health(self):
        """测试健康检查端点"""
        response = httpx.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestArticlesAPI:
    """文章 API 测试"""
    
    def test_get_articles_list(self):
        """测试获取文章列表"""
        response = httpx.get(f"{BASE_URL}/api/articles/")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)
    
    def test_get_articles_with_pagination(self):
        """测试分页获取文章"""
        response = httpx.get(f"{BASE_URL}/api/articles/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 5
    
    def test_get_article_types(self):
        """测试获取文章类型"""
        response = httpx.get(f"{BASE_URL}/api/articles/types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestCaptchaAPI:
    """验证码 API 测试"""
    
    def test_generate_captcha(self):
        """测试生成验证码"""
        response = httpx.get(f"{BASE_URL}/api/captcha/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "captcha_id" in data["data"]
        assert "image" in data["data"]


class TestUEditorAPI:
    """UEditor API 测试"""
    
    def test_ueditor_config(self):
        """测试 UEditor 配置接口"""
        response = httpx.get(f"{BASE_URL}/api/uedit?action=config")
        assert response.status_code == 200
        data = response.json()
        assert "imageActionName" in data
        assert "imageMaxSize" in data


class TestRecommendAPI:
    """推荐文章 API 测试"""
    
    def test_hot_articles(self):
        """测试热门文章接口"""
        response = httpx.get(f"{BASE_URL}/api/articles/hot")
        assert response.status_code == 200
        data = response.json()
        # 检查返回数据结构
        assert isinstance(data, dict) or isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
