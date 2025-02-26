from locust import HttpUser, task, between

class WoniunoteUser(HttpUser):
    wait_time = between(1, 3)  # 每个任务之间等待1-3秒
    
    def on_start(self):
        """用户开始测试前的初始化"""
        # 登录
        self.client.post("/login", {
            "username": "testuser",
            "password": "testpass123",
            "vcode": "0000"
        })
    
    @task(3)
    def view_homepage(self):
        """访问首页"""
        self.client.get("/")
    
    @task(2)
    def view_article(self):
        """查看文章详情"""
        self.client.get("/article/1")
    
    @task(1)
    def search_article(self):
        """搜索文章"""
        self.client.get("/search?keyword=测试")
    
    @task(1)
    def view_user_center(self):
        """访问用户中心"""
        self.client.get("/ucenter")
    
    @task(1)
    def add_comment(self):
        """添加评论"""
        self.client.post("/comment/create", {
            "articleid": 1,
            "content": "性能测试评论"
        })

# 运行方式：
# locust -f test_performance.py --host=http://localhost:5000
