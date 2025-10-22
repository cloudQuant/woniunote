#!/usr/bin/env python3
"""
测试缩略图创建功能
验证缺失缩略图的自动创建功能
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path.cwd()))

def test_thumbnail_creation():
    """测试缩略图创建功能"""
    try:
        from woniunote.common.utils import create_thumb_png
        
        print("测试缩略图创建功能...")
        
        # 测试创建不同类型的缩略图
        test_cases = [
            (11, "教育"),
            (12, "体育"), 
            (13, "音乐"),
            (101, "技术"),
            (201, "生活"),
            (999, "未知")
        ]
        
        thumb_dir = Path("woniunote/resource/thumb")
        
        for type_id, text in test_cases:
            filename = f"{type_id}.png"
            file_path = thumb_dir / filename
            
            # 如果文件不存在，创建它
            if not file_path.exists():
                print(f"创建缺失的缩略图: {filename}")
                
                # 创建缩略图
                thumbnail = create_thumb_png(width=226, height=136, text=text)
                
                # 保存文件
                thumbnail.save(str(file_path), 'PNG')
                print(f"✓ 成功创建: {filename}")
            else:
                print(f"✓ 文件已存在: {filename}")
        
        print("\n缩略图创建测试完成!")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

def check_missing_thumbnails():
    """检查缺失的缩略图文件"""
    thumb_dir = Path("woniunote/resource/thumb")
    
    if not thumb_dir.exists():
        print(f"缩略图目录不存在: {thumb_dir}")
        return []
    
    # 检查1-20的基础类型缩略图
    missing_files = []
    for i in range(1, 21):
        filename = f"{i}.png"
        file_path = thumb_dir / filename
        if not file_path.exists():
            missing_files.append((i, filename))
    
    # 检查一些常见的子类型缩略图
    common_subtypes = [101, 102, 103, 201, 202, 203, 301, 302, 303]
    for subtype in common_subtypes:
        filename = f"{subtype}.png"
        file_path = thumb_dir / filename
        if not file_path.exists():
            missing_files.append((subtype, filename))
    
    return missing_files

def create_missing_thumbnails():
    """创建所有缺失的缩略图"""
    missing = check_missing_thumbnails()
    
    if not missing:
        print("没有发现缺失的缩略图文件")
        return True
    
    print(f"发现 {len(missing)} 个缺失的缩略图文件:")
    
    # 类型文字映射
    type_text_map = {
        1: "技术", 2: "生活", 3: "学习", 4: "工作", 5: "娱乐",
        6: "旅行", 7: "美食", 8: "健康", 9: "财经", 10: "科技",
        11: "教育", 12: "体育", 13: "音乐", 14: "电影", 15: "游戏",
        16: "新闻", 17: "社交", 18: "购物", 19: "工具", 20: "其他"
    }
    
    try:
        from woniunote.common.utils import create_thumb_png
        thumb_dir = Path("woniunote/resource/thumb")
        
        created_count = 0
        for type_id, filename in missing:
            # 确定文字内容
            category_id = type_id // 100 if type_id >= 100 else type_id
            text = type_text_map.get(category_id, f"类型{type_id}")
            
            print(f"创建: {filename} (文字: {text})")
            
            # 创建缩略图
            thumbnail = create_thumb_png(width=226, height=136, text=text)
            
            # 保存文件
            file_path = thumb_dir / filename
            thumbnail.save(str(file_path), 'PNG')
            
            created_count += 1
            print(f"✓ 成功创建: {filename}")
        
        print(f"\n成功创建了 {created_count} 个缩略图文件!")
        return True
        
    except Exception as e:
        print(f"创建缩略图失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("缩略图创建工具")
    print("="*60)
    
    # 检查缺失的文件
    print("1. 检查缺失的缩略图文件...")
    missing = check_missing_thumbnails()
    
    if missing:
        print(f"发现 {len(missing)} 个缺失的文件:")
        for type_id, filename in missing[:10]:  # 只显示前10个
            print(f"  - {filename}")
        if len(missing) > 10:
            print(f"  ... 还有 {len(missing) - 10} 个文件")
        
        # 询问是否创建
        create = input("\n是否创建这些缺失的缩略图? (y/n): ").lower()
        if create == 'y':
            print("\n2. 创建缺失的缩略图...")
            success = create_missing_thumbnails()
            if success:
                print("✅ 所有缺失的缩略图已创建完成!")
            else:
                print("❌ 创建过程中出现错误")
        else:
            print("跳过创建步骤")
    else:
        print("✅ 没有发现缺失的缩略图文件")
    
    # 测试创建功能
    print("\n3. 测试缩略图创建功能...")
    test_success = test_thumbnail_creation()
    
    if test_success:
        print("✅ 缩略图创建功能测试通过")
    else:
        print("❌ 缩略图创建功能测试失败")
    
    return test_success

if __name__ == "__main__":
    try:
        success = main()
        input("\n按回车键退出...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n操作被用户取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        sys.exit(1)
