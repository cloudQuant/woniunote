"""
文章API测试
"""
import pytest
from httpx import AsyncClient


class TestArticlesList:
    """文章列表测试"""
    
    @pytest.mark.asyncio
    async def test_get_articles_list(self, client: AsyncClient):
        """测试获取文章列表"""
        response = await client.get("/api/articles/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_articles_with_pagination(self, client: AsyncClient):
        """测试分页参数"""
        response = await client.get("/api/articles/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    @pytest.mark.asyncio
    async def test_get_articles_invalid_page(self, client: AsyncClient):
        """测试无效页码"""
        response = await client.get("/api/articles/?page=0")
        assert response.status_code == 422  # 验证失败
    
    @pytest.mark.asyncio
    async def test_get_articles_by_type(self, client: AsyncClient):
        """测试按类型筛选"""
        response = await client.get("/api/articles/?type=701")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_articles_by_keyword(self, client: AsyncClient):
        """测试关键词搜索"""
        response = await client.get("/api/articles/?keyword=python")
        assert response.status_code == 200


class TestArticleTypes:
    """文章类型测试"""
    
    @pytest.mark.asyncio
    async def test_get_article_types(self, client: AsyncClient):
        """测试获取文章类型"""
        response = await client.get("/api/articles/types")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "types" in data["data"]
        assert isinstance(data["data"]["types"], dict)


class TestHotArticles:
    """热门文章测试"""
    
    @pytest.mark.asyncio
    async def test_get_hot_articles(self, client: AsyncClient):
        """测试获取热门文章"""
        response = await client.get("/api/articles/hot")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "latest" in data["data"]
        assert "most" in data["data"]
        assert "recommended" in data["data"]


class TestArticleDetail:
    """文章详情测试"""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_article(self, client: AsyncClient):
        """测试获取不存在的文章"""
        response = await client.get("/api/articles/99999")
        assert response.status_code == 404


class TestArticleCRUD:
    """文章CRUD测试（需要认证）"""
    
    @pytest.mark.asyncio
    async def test_create_article_without_auth(self, client: AsyncClient, test_article_data):
        """测试未认证创建文章"""
        response = await client.post("/api/articles/", json=test_article_data)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_update_article_without_auth(self, client: AsyncClient):
        """测试未认证更新文章"""
        response = await client.put("/api/articles/1", json={"headline": "新标题"})
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_delete_article_without_auth(self, client: AsyncClient):
        """测试未认证删除文章"""
        response = await client.delete("/api/articles/1")
        assert response.status_code == 403
