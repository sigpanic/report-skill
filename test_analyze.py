#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.template_parser.analyzer import analyze_template_compact, save_compact, get_analysis_guide

template_path = '/workspace/算法设计实验/算法设计与分析实验报告模板-最新_1.docx'

print(f"正在分析模板: {template_path}")

try:
    compact = analyze_template_compact(template_path)
    
    output_dir = '/workspace/算法设计实验/parsed'
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(template_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_compact.json")
    
    save_compact(compact, output_path)
    print(f"✓ compact 数据已保存到: {output_path}")
    
    guide = get_analysis_guide()
    guide_path = os.path.join(output_dir, f"{base_name}_guide.md")
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide)
    print(f"✓ 分析指导已保存到: {guide_path}")
    
    print("\n分析完成！请读取以下文件继续操作：")
    print(f"  1. {output_path}")
    print(f"  2. {guide_path}")
    
except Exception as e:
    print(f"✗ 分析失败: {e}")
    import traceback
    traceback.print_exc()
