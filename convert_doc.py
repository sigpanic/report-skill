#!/usr/bin/env python3
import os
import subprocess
import sys

doc_path = '/workspace/算法设计实验/算法设计与分析实验报告模板-最新_1.doc'
docx_path = '/workspace/算法设计实验/算法设计与分析实验报告模板-最新_1.docx'

print(f"尝试使用 LibreOffice 转换: {doc_path}")

try:
    result = subprocess.run([
        'libreoffice', '--headless', '--convert-to', 'docx',
        '--outdir', '/workspace/算法设计实验',
        doc_path
    ], capture_output=True, text=True, timeout=60)
    
    print(f"返回码: {result.returncode}")
    
    if result.returncode == 0:
        print(f"✓ 转换成功！输出文件: {docx_path}")
        if os.path.exists(docx_path):
            print(f"✓ 文件已生成，大小: {os.path.getsize(docx_path)} 字节")
    else:
        print(f"✗ 转换失败")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        
except FileNotFoundError:
    print("✗ LibreOffice 未安装")
    # 尝试 unoconv
    try:
        result = subprocess.run([
            'unoconv', '-f', 'docx', '-o', docx_path, doc_path
        ], capture_output=True, text=True, timeout=60)
        
        print(f"unoconv 返回码: {result.returncode}")
        
    except FileNotFoundError:
        print("✗ unoconv 也未安装")
        
except Exception as e:
    print(f"✗ 转换过程出错: {e}")
    import traceback
    traceback.print_exc()
