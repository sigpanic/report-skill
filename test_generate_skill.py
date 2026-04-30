#!/usr/bin/env python3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.skill_generator.generator import generate_skill

profile_path = '/workspace/算法设计实验/parsed/算法设计与分析实验报告模板-最新_1_profile.json'
skill_name = '算法设计实验报告生成器'
output_path = os.path.join('/workspace/算法设计实验', f'{skill_name}.md')

print(f"正在生成特化 Skill: {skill_name}")

try:
    with open(profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    result = generate_skill(
        profile=profile,
        skill_name=skill_name,
        output_path=output_path,
        constraints={
            "禁止内容": {
                "源代码": "报告中不需要列程序源代码，只需要把代码打包发送"
            },
            "格式要求": "字体：宋体小四；正文行间距：固定值22磅；每一段首行缩进2个字符；段前及段后间距均设为0"
        }
    )
    print(f"✓ 特化 Skill 生成成功！")
    print(f"  保存路径: {result}")
    
except Exception as e:
    print(f"✗ 生成失败: {e}")
    import traceback
    traceback.print_exc()
