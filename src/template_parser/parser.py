import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional

def doc_to_docx(doc_path: str) -> Optional[str]:
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        docx_path = None
        try:
            doc = word.Documents.Open(
                os.path.abspath(doc_path),
                ReadOnly=True,
                AddToRecentFiles=False,
                Visible=False
            )
            try:
                tmp_dir = tempfile.mkdtemp()
                docx_path = os.path.join(tmp_dir, "converted.docx")
                doc.SaveAs2(os.path.abspath(docx_path), FileFormat=16)
            finally:
                try:
                    doc.Close(False)
                except Exception:
                    pass
        finally:
            try:
                word.Quit()
            except Exception:
                pass
        return docx_path
    except Exception as e:
        print(f"doc转docx失败: {e}")
        return None

def parse_template(template_path: str) -> dict:
    """
    解析Word模板文档，返回结构化描述。
    
    返回结构：
    {
        "page_setup": {...},
        "cover_page": {
            "title": {...},
            "info_lines": [...],
            "college": {...},
            "table": {...}
        },
        "content_sections": [
            {"title": "一、实验目的", "style": {...}, "note": "..."},
            ...
        ],
        "format_rules": {...},
        "tables": [...]
    }
    """
    path = Path(template_path)
    actual_path = template_path
    
    if path.suffix.lower() == '.doc':
        converted = doc_to_docx(template_path)
        if converted:
            actual_path = converted
        else:
            raise ValueError(f"无法转换.doc文件: {template_path}")
    
    from docx import Document
    from docx.shared import Cm, Pt, Emu
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    doc = Document(actual_path)
    
    result = {
        "page_setup": _parse_page_setup(doc),
        "elements": [],
        "tables": [],
        "format_rules": {}
    }
    
    for element in doc.element.body:
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        if tag == 'p':
            para = None
            for p in doc.paragraphs:
                if p._element is element:
                    para = p
                    break
            if para is not None:
                result["elements"].append(_parse_paragraph(para))
        elif tag == 'tbl':
            table = None
            for t in doc.tables:
                if t._element is element:
                    table = t
                    break
            if table is not None:
                result["tables"].append(_parse_table(table))
    
    result["format_rules"] = _extract_format_rules(result)
    
    return result

def _parse_page_setup(doc) -> dict:
    """解析页面设置"""
    if doc.sections:
        section = doc.sections[0]
        return {
            "page_width_cm": round(section.page_width / 360000, 2) if section.page_width else None,
            "page_height_cm": round(section.page_height / 360000, 2) if section.page_height else None,
            "left_margin_cm": round(section.left_margin / 360000, 2) if section.left_margin else None,
            "right_margin_cm": round(section.right_margin / 360000, 2) if section.right_margin else None,
            "top_margin_cm": round(section.top_margin / 360000, 2) if section.top_margin else None,
            "bottom_margin_cm": round(section.bottom_margin / 360000, 2) if section.bottom_margin else None,
        }
    return {}

def _parse_paragraph(para) -> dict:
    """解析段落"""
    result = {
        "type": "paragraph",
        "text": para.text,
        "style": para.style.name if para.style else None,
        "alignment": str(para.alignment) if para.alignment else None,
        "runs": []
    }
    
    pf = para.paragraph_format
    if pf.first_line_indent:
        result["first_line_indent_cm"] = round(pf.first_line_indent / 360000, 2)
    if pf.space_before:
        result["space_before_pt"] = round(pf.space_before / 12700, 1)
    if pf.space_after:
        result["space_after_pt"] = round(pf.space_after / 12700, 1)
    if pf.line_spacing:
        result["line_spacing"] = pf.line_spacing
    if pf.line_spacing_rule:
        result["line_spacing_rule"] = str(pf.line_spacing_rule)
    
    for run in para.runs:
        run_info = {"text": run.text}
        if run.font.name:
            run_info["font_name"] = run.font.name
        if run.font.size:
            run_info["font_size_pt"] = round(run.font.size / 12700, 1)
        if run.font.bold:
            run_info["bold"] = True
        if run.font.italic:
            run_info["italic"] = True
        if run.font.underline:
            run_info["underline"] = True
        if run.font.color and run.font.color.rgb:
            run_info["font_color"] = str(run.font.color.rgb)
        result["runs"].append(run_info)
    
    return result

def _parse_table(table) -> dict:
    """解析表格"""
    result = {
        "type": "table",
        "rows": len(table.rows),
        "cols": len(table.columns),
        "cells": [],
        "column_widths_cm": []
    }
    
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell_info = {
                "row": row_idx,
                "col": col_idx,
                "text": cell.text.strip()
            }
            actual_cell = table.cell(row_idx, col_idx)
            for span_col in range(col_idx + 1, len(row.cells)):
                try:
                    if row.cells[span_col]._tc is actual_cell._tc:
                        cell_info["colspan"] = span_col - col_idx + 1
                        break
                except:
                    pass
            
            cell_info["paragraphs"] = []
            for p in cell.paragraphs:
                cell_info["paragraphs"].append(_parse_paragraph(p))
            result["cells"].append(cell_info)
    
    for col in table.columns:
        if col.width:
            result["column_widths_cm"].append(round(col.width / 360000, 2))
    
    return result

def _extract_format_rules(parsed: dict) -> dict:
    """从解析结果中提取格式规则"""
    rules = {
        "section_header": {"font_name": "黑体", "font_size_pt": 14.0, "bold": True},
        "body_text": {"font_name": "宋体", "font_size_pt": 12.0},
        "line_spacing_pt": 22,
        "first_line_indent_chars": 2,
        "space_before": 0,
        "space_after": 0
    }
    
    for elem in parsed["elements"]:
        if elem.get("text", "").startswith("一、"):
            for run in elem.get("runs", []):
                if run.get("font_name"):
                    rules["section_header"]["font_name"] = run["font_name"]
                if run.get("font_size_pt"):
                    rules["section_header"]["font_size_pt"] = run["font_size_pt"]
                if run.get("bold"):
                    rules["section_header"]["bold"] = run["bold"]
            break
    
    return rules

def save_parsed_template(parsed: dict, output_path: str):
    """保存解析结果为JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
