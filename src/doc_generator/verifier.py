import os
import json
import tempfile
import shutil
from typing import Optional

from docx import Document

from src.template_parser.parser import doc_to_docx


def verify_format(template_path: str, generated_path: str, output_path: Optional[str] = None) -> dict:
    template_docx = _ensure_docx(template_path)
    generated_docx = _ensure_docx(generated_path)

    try:
        template_doc = Document(template_docx)
        generated_doc = Document(generated_docx)

        results = {
            "page_setup": _verify_page_setup(template_doc, generated_doc),
            "paragraphs": _verify_paragraphs(template_doc, generated_doc),
            "tables": _verify_tables(template_doc, generated_doc),
            "passed": True,
            "issues": []
        }

        for category, checks in results.items():
            if category in ["passed", "issues"]:
                continue
            if isinstance(checks, dict):
                for key, value in checks.items():
                    if value is False:
                        results["passed"] = False
                        results["issues"].append(f"{category}.{key}: 不一致")
            elif isinstance(checks, list):
                for i, check in enumerate(checks):
                    if isinstance(check, dict):
                        for key, value in check.items():
                            if value is False and key != "text_match":
                                results["passed"] = False
                                results["issues"].append(f"{category}[{i}].{key}: 不一致")

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return results
    finally:
        if template_docx != template_path and os.path.exists(template_docx):
            try:
                os.remove(template_docx)
            except Exception:
                pass
        if generated_docx != generated_path and os.path.exists(generated_docx):
            try:
                os.remove(generated_docx)
            except Exception:
                pass


def _ensure_docx(file_path: str) -> str:
    if file_path.lower().endswith('.docx'):
        return file_path

    converted = doc_to_docx(file_path)
    if converted:
        return converted

    tmp_dir = tempfile.mkdtemp()
    docx_path = os.path.join(tmp_dir, "converted.docx")
    shutil.copy2(file_path, docx_path)
    return docx_path


def _verify_page_setup(template_doc, generated_doc) -> dict:
    t_sec = template_doc.sections[0] if template_doc.sections else None
    g_sec = generated_doc.sections[0] if generated_doc.sections else None

    if not t_sec or not g_sec:
        return {"has_sections": t_sec is not None and g_sec is not None}

    return {
        "page_width": _compare_emu(t_sec.page_width, g_sec.page_width, "page_width"),
        "page_height": _compare_emu(t_sec.page_height, g_sec.page_height, "page_height"),
        "left_margin": _compare_emu(t_sec.left_margin, g_sec.left_margin, "left_margin"),
        "right_margin": _compare_emu(t_sec.right_margin, g_sec.right_margin, "right_margin"),
        "top_margin": _compare_emu(t_sec.top_margin, g_sec.top_margin, "top_margin"),
        "bottom_margin": _compare_emu(t_sec.bottom_margin, g_sec.bottom_margin, "bottom_margin"),
    }


def _compare_emu(a, b, name: str, tolerance: int = 10000) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) < tolerance


def _verify_paragraphs(template_doc, generated_doc) -> list:
    results = []
    t_paras = template_doc.paragraphs
    g_paras = generated_doc.paragraphs

    min_len = min(len(t_paras), len(g_paras))
    for i in range(min_len):
        t_para = t_paras[i]
        g_para = g_paras[i]

        t_text = t_para.text.strip()
        g_text = g_para.text.strip()

        if not t_text and not g_text:
            continue

        result = {
            "index": i,
            "template_text": t_text[:50],
            "generated_text": g_text[:50],
            "text_match": t_text == g_text,
        }

        if t_text == g_text:
            result["alignment_match"] = t_para.alignment == g_para.alignment

            t_runs = t_para.runs
            g_runs = g_para.runs

            if t_runs and g_runs:
                result["font_name_match"] = _compare_font_name(t_runs[0], g_runs[0])
                result["font_size_match"] = _compare_font_size(t_runs[0], g_runs[0])
                result["bold_match"] = t_runs[0].font.bold == g_runs[0].font.bold
                result["italic_match"] = t_runs[0].font.italic == g_runs[0].font.italic
                result["underline_match"] = t_runs[0].font.underline == g_runs[0].font.underline

        results.append(result)

    return results


def _compare_font_name(run_a, run_b) -> bool:
    a_name = run_a.font.name
    b_name = run_b.font.name
    if a_name == b_name:
        return True
    try:
        a_east = run_a._element.rPr.rFonts.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia')
        b_east = run_b._element.rPr.rFonts.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia')
        return a_east == b_east
    except Exception:
        return False


def _compare_font_size(run_a, run_b, tolerance: int = 12700) -> bool:
    a_size = run_a.font.size
    b_size = run_b.font.size
    if a_size is None or b_size is None:
        return a_size is None and b_size is None
    return abs(a_size - b_size) < tolerance


def _verify_tables(template_doc, generated_doc) -> list:
    results = []
    t_tables = template_doc.tables
    g_tables = generated_doc.tables

    min_len = min(len(t_tables), len(g_tables))
    for i in range(min_len):
        t_table = t_tables[i]
        g_table = g_tables[i]

        result = {
            "index": i,
            "rows_match": len(t_table.rows) == len(g_table.rows),
            "cols_match": len(t_table.columns) == len(g_table.columns),
        }

        results.append(result)

    return results
