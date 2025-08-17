#!/usr/bin/env python3
"""
前端资源优化脚本
统一jQuery版本，移除重复加载，优化资源引用
"""
import os
import re
from pathlib import Path

class FrontendOptimizer:
    """前端资源优化器"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.template_dir = self.project_root / 'woniunote' / 'template'
        self.changes_made = []
    
    def scan_jquery_usage(self):
        """扫描jQuery使用情况"""
        jquery_files = {}
        
        for template_file in self.template_dir.glob('*.html'):
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找jQuery引用
                jquery_patterns = [
                    r'<script[^>]*src="[^"]*jquery[^"]*"[^>]*>',
                    r'<script[^>]*src=\'[^\']*jquery[^\']*\'[^>]*>',
                ]
                
                jquery_refs = []
                for pattern in jquery_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    jquery_refs.extend(matches)
                
                if jquery_refs:
                    jquery_files[template_file.name] = jquery_refs
        
        return jquery_files
    
    def standardize_jquery(self):
        """标准化jQuery版本"""
        print("🔧 标准化jQuery版本...")
        
        # 推荐的jQuery版本
        recommended_jquery = 'https://code.jquery.com/jquery-3.6.0.min.js'
        
        # 要替换的jQuery模式
        old_patterns = [
            r'<script[^>]*src="https://code\.jquery\.com/jquery-1\.12\.4\.min\.js"[^>]*>',
            r'<script[^>]*src="/js/jquery-3\.4\.1\.min\.js"[^>]*>',
            r'<script[^>]*defer[^>]*src="/js/jquery-3\.4\.1\.min\.js"[^>]*>',
        ]
        
        new_script = f'<script src="{recommended_jquery}"></script>'
        
        for template_file in self.template_dir.glob('*.html'):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                changed = False
                
                # 替换旧的jQuery引用
                for pattern in old_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        content = re.sub(pattern, new_script, content, flags=re.IGNORECASE)
                        changed = True
                
                # 如果文件被修改，写回文件
                if changed:
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.changes_made.append(f"✓ 更新 {template_file.name} 的jQuery版本")
                    print(f"  ✓ 更新 {template_file.name}")
                
            except Exception as e:
                print(f"  ❌ 处理 {template_file.name} 时出错: {e}")
    
    def remove_duplicate_jquery(self):
        """移除重复的jQuery加载"""
        print("\n🔧 移除重复的jQuery加载...")
        
        for template_file in self.template_dir.glob('*.html'):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # 查找所有jQuery引用
                jquery_pattern = r'<script[^>]*src="[^"]*jquery[^"]*"[^>]*>'
                jquery_matches = re.findall(jquery_pattern, content, re.IGNORECASE)
                
                if len(jquery_matches) > 1:
                    print(f"  发现 {template_file.name} 中有 {len(jquery_matches)} 个jQuery引用")
                    
                    # 保留第一个，移除其他的
                    first_match = jquery_matches[0]
                    for i in range(1, len(jquery_matches)):
                        content = content.replace(jquery_matches[i], '', 1)
                    
                    # 写回文件
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.changes_made.append(f"✓ 移除 {template_file.name} 中的重复jQuery")
                    print(f"  ✓ 已清理 {template_file.name}")
                
            except Exception as e:
                print(f"  ❌ 处理 {template_file.name} 时出错: {e}")
    
    def optimize_css_loading(self):
        """优化CSS加载"""
        print("\n🔧 优化CSS加载...")
        
        # 查找重复的CSS引用
        css_patterns = [
            r'<link[^>]*href="[^"]*bootstrap[^"]*"[^>]*>',
            r'<link[^>]*href="[^"]*woniunote\.css[^"]*"[^>]*>',
        ]
        
        for template_file in self.template_dir.glob('*.html'):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                changed = False
                
                # 检查每种CSS类型的重复
                for pattern in css_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if len(matches) > 1:
                        # 保留第一个，移除其他的
                        for i in range(1, len(matches)):
                            content = content.replace(matches[i], '', 1)
                        changed = True
                
                if changed:
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.changes_made.append(f"✓ 优化 {template_file.name} 的CSS加载")
                    print(f"  ✓ 优化 {template_file.name}")
                
            except Exception as e:
                print(f"  ❌ 处理 {template_file.name} 时出错: {e}")
    
    def add_resource_optimization(self):
        """添加资源优化标签"""
        print("\n🔧 添加资源优化标签...")
        
        # 在base.html中添加资源优化
        base_html = self.template_dir / 'base.html'
        if base_html.exists():
            try:
                with open(base_html, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 添加资源预加载和缓存控制
                optimization_tags = '''
    <!-- 资源优化 -->
    <link rel="preconnect" href="https://code.jquery.com">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <meta http-equiv="Cache-Control" content="public, max-age=31536000">'''
                
                # 在head标签结束前添加优化标签
                if '</head>' in content and optimization_tags not in content:
                    content = content.replace('</head>', f'{optimization_tags}\n</head>')
                    
                    with open(base_html, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.changes_made.append("✓ 添加了资源预加载优化")
                    print(f"  ✓ 添加资源优化标签到 base.html")
                
            except Exception as e:
                print(f"  ❌ 优化 base.html 时出错: {e}")
    
    def generate_report(self):
        """生成优化报告"""
        print("\n📊 前端资源优化报告")
        print("=" * 50)
        
        if not self.changes_made:
            print("✅ 没有发现需要优化的问题")
            return
        
        print(f"共完成 {len(self.changes_made)} 项优化:")
        for change in self.changes_made:
            print(f"  {change}")
        
        print("\n✅ 前端资源优化完成!")
        print("\n📝 建议:")
        print("  1. 测试所有页面确保功能正常")
        print("  2. 检查JavaScript控制台是否有错误")
        print("  3. 验证所有交互功能正常工作")
    
    def run_optimization(self):
        """运行完整的优化流程"""
        print("🚀 开始前端资源优化...")
        
        # 扫描当前状态
        print("\n🔍 扫描jQuery使用情况...")
        jquery_usage = self.scan_jquery_usage()
        
        if jquery_usage:
            print("发现以下文件使用jQuery:")
            for file, refs in jquery_usage.items():
                print(f"  {file}: {len(refs)} 个引用")
        
        # 执行优化步骤
        self.standardize_jquery()
        self.remove_duplicate_jquery()
        self.optimize_css_loading()
        self.add_resource_optimization()
        
        # 生成报告
        self.generate_report()

def main():
    """主函数"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    print("🎯 WoniuNote 前端资源优化工具")
    print("=" * 50)
    
    # 创建优化器并运行
    optimizer = FrontendOptimizer(project_root)
    optimizer.run_optimization()

if __name__ == '__main__':
    main()