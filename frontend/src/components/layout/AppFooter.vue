<template>
  <footer class="app-footer">
    <div class="footer-container">
      <div class="footer-row">
        <!-- 版权信息 -->
        <div class="footer-col">
          <p class="footer-title">版权所有 © 云金杞</p>
          <p>
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
              京 ICP 备 2021040304号
            </a>
          </p>
          <p>
            <a href="http://www.beian.gov.cn/portal/registerSystemInfo?recordcode=11010702002337" 
               target="_blank" rel="noopener noreferrer">
              京公网安备 11010702002337 号
            </a>
          </p>
        </div>
        
        <!-- 友情链接 -->
        <div class="footer-col">
          <p class="footer-title">友情链接</p>
          <p>
            <a href="https://blog.csdn.net/qq_26948675/category_11503023.html" target="_blank">CSDN博客</a>
            <a href="https://www.zhihu.com/people/yun-jin-qi" target="_blank">个人知乎</a>
          </p>
        </div>
        
        <!-- 联系博主 -->
        <div class="footer-col">
          <p class="footer-title">联系博主</p>
          <p>北京★孵化园&nbsp;&nbsp;&nbsp;微信：tianjixuetu</p>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
</script>

<style scoped>
.app-footer {
  background: #343a40;
  color: #adb5bd;
  padding: 30px 0;
  margin-top: auto;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.footer-row {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 30px;
}

.footer-col {
  flex: 1;
  min-width: 200px;
}

.footer-title {
  color: #fff;
  font-size: 15px;
  margin-bottom: 12px;
  font-weight: 500;
}

.footer-col p {
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.6;
}

.footer-col a {
  color: #adb5bd;
  text-decoration: none;
  margin-right: 15px;
  transition: color 0.3s;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.footer-col a:hover {
  color: #17a2b8;
}

@media (max-width: 768px) {
  .footer-row {
    flex-direction: column;
    text-align: center;
  }
  
  .footer-col {
    min-width: 100%;
  }
}
</style>
