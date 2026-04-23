import os
import json
import re
import tempfile
from pathlib import Path
from typing import Optional

from src.template_parser.parser import doc_to_docx, parse_template

DEFAULT_LABEL_MAPPINGS = {
    "实验课程": "course_name",
    "课程名称": "course_name",
    "课程": "course_name",
    "学生姓名": "student_name",
    "姓名": "student_name",
    "学    号": "student_id",
    "学号": "student_id",
    "专业班级": "student_class",
    "班级": "student_class",
    "指导教师": "teacher",
    "指导老师": "teacher",
    "教师": "teacher",
    "老师": "teacher",
    "实验名称": "experiment_name",
    "名称": "experiment_name",
    "实验日期": "experiment_date",
    "日期": "experiment_date",
    "年月日": "experiment_date",
    "实验地点": "experiment_location",
    "地点": "experiment_location",
    "实验成绩": "score",
    "成绩": "score",
    "评语": "comment",
    "学院": "college",
    "大学": "university",
    "学校": "school",
}

DEFAULT_LABEL_KEYWORDS = [
    "实验名称", "实验日期", "实验地点", "指导老师", "指导教师",
    "实验成绩", "评语", "实验课程", "学生姓名", "学号", "专业班级",
    "姓名", "班级", "日期", "地点", "老师", "教师", "成绩",
    "课程", "实验", "学院", "大学", "学校",
]

DEFAULT_COLLEGE_KEYWORDS = ["学院", "大学", "学校", "系", "College", "University", "School"]


def analyze_template(template_path: str, label_mappings: dict = None) -> dict:
    profile = {
        "template_path": template_path,
        "page_setup": {},
        "cover_page": {"title": None, "fields": [], "college": None},
        "tables": [],
        "sections": [],
        "format_rules": {},
        "annotation_patterns": [],
        "removal_patterns": [],
        "fields": []
    }

    raw = parse_template(template_path)
    profile["page_setup"] = raw.get("page_setup", {})
    profile["cover_page"] = _analyze_cover_page(raw, label_mappings)
    profile["tables"] = _analyze_tables(raw, label_mappings)
    profile["sections"] = _analyze_sections(raw)
    profile["format_rules"] = _analyze_format_rules(raw)
    profile["annotation_patterns"] = _detect_annotation_patterns(raw)
    profile["removal_patterns"] = _detect_removal_patterns(raw)
    profile["fields"] = _collect_all_fields(profile)

    return profile


def _analyze_cover_page(raw: dict, label_mappings: dict = None) -> dict:
    cover = {"title": None, "fields": [], "college": None}

    for elem in raw.get("elements", []):
        text = elem.get("text", "").strip()
        runs = elem.get("runs", [])

        if not text:
            continue

        if _is_title(text, runs):
            cover["title"] = {
                "text": text,
                "style": _extract_run_style(runs[0]) if runs else {}
            }
            continue

        field = _detect_labeled_field(text, runs, elem, label_mappings)
        if field:
            cover["fields"].append(field)
            continue

        if _is_college_line(text, runs):
            cover["college"] = {
                "text": text,
                "style": _extract_run_style(runs[0]) if runs else {}
            }

    return cover


def _is_title(text: str, runs: list) -> bool:
    if not runs:
        return False
    for run in runs:
        if run.get("font_size_pt") and run["font_size_pt"] >= 30:
            return True
    return False


def _detect_labeled_field(text: str, runs: list, elem: dict, label_mappings: dict = None) -> Optional[dict]:
    patterns = [r'^([^：:]+[：:])(.*)$']

    has_underline = any(r.get("underline") for r in runs)

    for pattern in patterns:
        m = re.match(pattern, text.strip())
        if m:
            label = m.group(1).strip()
            value_part = m.group(2).strip()

            if has_underline or not value_part or value_part.isspace():
                key = _label_to_key(label, label_mappings)
                return {
                    "key": key,
                    "label": label,
                    "type": "text_with_underline" if has_underline else "text",
                    "default": value_part if value_part and not value_part.isspace() else "",
                    "style": _extract_paragraph_style(elem)
                }

    return None


def _is_college_line(text: str, runs: list) -> bool:
    has_bold = any(r.get("bold") for r in runs)
    return any(kw in text for kw in DEFAULT_COLLEGE_KEYWORDS) and has_bold


def _label_to_key(label: str, label_mappings: dict = None) -> str:
    label = label.rstrip("：:")
    mappings = label_mappings or DEFAULT_LABEL_MAPPINGS
    clean = label.replace(" ", "")
    for cn, en in mappings.items():
        cn_clean = cn.replace(" ", "")
        if clean == cn_clean:
            return en

    key = re.sub(r'[^\w]', '_', label)
    key = key.strip('_')
    return key.lower() if key else "field_unknown"


def _analyze_tables(raw: dict, label_mappings: dict = None) -> list:
    tables_info = []

    for table_idx, table_data in enumerate(raw.get("tables", [])):
        table_info = {
            "index": table_idx,
            "rows": table_data.get("rows", 0),
            "cols": table_data.get("cols", 0),
            "column_widths_cm": table_data.get("column_widths_cm", []),
            "fields": []
        }

        seen_tc = set()
        for cell in table_data.get("cells", []):
            row, col = cell["row"], cell["col"]

            tc_id = cell.get("tc_id")
            if tc_id and tc_id in seen_tc:
                continue
            if tc_id:
                seen_tc.add(tc_id)

            cell_text = cell.get("text", "").strip()
            paras = cell.get("paragraphs", [])

            is_label = _is_label_cell(paras, cell_text, label_mappings)
            is_hint = _is_hint_cell(paras)

            if is_label and not is_hint:
                continue

            if is_hint or (not is_label and cell_text):
                adjacent_label = _find_adjacent_label(table_data, row, col)
                key = _determine_field_key(cell_text, adjacent_label, is_hint, row, col, table_data, label_mappings)
                field = {
                    "key": key,
                    "cell": f"{row},{col}",
                    "label": adjacent_label if adjacent_label else cell_text,
                    "type": "table_cell",
                    "is_hint": is_hint,
                    "style": _extract_cell_style(paras)
                }
                if cell.get("colspan"):
                    field["colspan"] = cell["colspan"]
                table_info["fields"].append(field)
            elif not is_label and not cell_text:
                adjacent_label = _find_adjacent_label(table_data, row, col)
                if adjacent_label:
                    key = _determine_field_key("", adjacent_label, False, row, col, table_data, label_mappings)
                    field = {
                        "key": key,
                        "cell": f"{row},{col}",
                        "label": adjacent_label,
                        "type": "table_cell",
                        "is_hint": False,
                        "style": _extract_cell_style(paras)
                    }
                    table_info["fields"].append(field)

        deduped = {}
        for f in table_info["fields"]:
            if f["key"] not in deduped:
                deduped[f["key"]] = f
        table_info["fields"] = list(deduped.values())

        tables_info.append(table_info)

    return tables_info


def _determine_field_key(cell_text: str, adjacent_label: str, is_hint: bool,
                          row: int, col: int, table_data: dict,
                          label_mappings: dict = None) -> str:
    mappings = label_mappings or DEFAULT_LABEL_MAPPINGS

    if adjacent_label:
        label_clean = re.sub(r'[：:]', '', adjacent_label).replace(" ", "")
        for cn, en in mappings.items():
            cn_clean = cn.replace(" ", "")
            if cn_clean in label_clean or label_clean in cn_clean:
                return en

    if cell_text:
        text_clean = re.sub(r'[^\w\u4e00-\u9fff]', '', cell_text)
        for cn, en in mappings.items():
            cn_clean = cn.replace(" ", "")
            if cn_clean in text_clean or text_clean in cn_clean:
                return en

    if not cell_text or not cell_text.strip():
        return f"cell_r{row}c{col}"

    clean = re.sub(r'[^\w\u4e00-\u9fff]', '', cell_text)
    if clean:
        return f"cell_{clean[:10]}"

    return f"cell_r{row}c{col}"


def _is_label_cell(paras: list, cell_text: str, label_mappings: dict = None) -> bool:
    keywords = label_mappings.keys() if label_mappings else DEFAULT_LABEL_KEYWORDS
    for kw in keywords:
        if cell_text == kw or cell_text.replace(" ", "") == kw.replace(" ", ""):
            return True
    return False


def _is_hint_cell(paras: list) -> bool:
    return any(
        r.get("italic") or r.get("font_color") in ["FF0000", "ff0000"]
        for p in paras for r in p.get("runs", [])
    )


def _find_adjacent_label(table_data: dict, row: int, col: int) -> str:
    cells = table_data.get("cells", [])
    if col > 0:
        for c in cells:
            if c["row"] == row and c["col"] == col - 1:
                return c.get("text", "").strip()
    return ""


def _analyze_sections(raw: dict) -> list:
    sections = []
    elements = raw.get("elements", [])
    seen_titles = set()

    i = 0
    while i < len(elements):
        elem = elements[i]
        text = elem.get("text", "").strip()
        runs = elem.get("runs", [])

        if _is_section_header(text, runs):
            if text not in seen_titles:
                section = {
                    "title": text,
                    "style": _extract_run_style(runs[0]) if runs else {},
                    "note": "",
                    "content_style": {}
                }

                j = i + 1
                notes = []
                while j < len(elements):
                    next_elem = elements[j]
                    next_text = next_elem.get("text", "").strip()
                    next_runs = next_elem.get("runs", [])

                    if _is_section_header(next_text, next_runs):
                        break

                    if _is_annotation(next_elem):
                        notes.append(next_text)

                    j += 1

                section["note"] = " ".join(notes)
                sections.append(section)
                seen_titles.add(text)

        i += 1

    return sections


def _is_section_header(text: str, runs: list) -> bool:
    if not text or not runs:
        return False

    patterns = [
        r'^[一二三四五六七八九十]+[、．.\s]',
        r'^\d+[、．.\s]',
        r'^[A-Za-z]+[、．.\s]',
        r'^Part\s+\d',
        r'^Chapter\s+\d',
        r'^Section\s+\d',
        r'^\(\d+\)',
        r'^\[\d+\]',
        r'^\d+\)',
        r'^[（(][一二三四五六七八九十]+[）)]',
        r'^Step\s+\d',
        r'^Procedure\s+\d',
    ]

    for pattern in patterns:
        if re.match(pattern, text, re.IGNORECASE):
            has_bold = any(r.get("bold") for r in runs)
            font_size = runs[0].get("font_size_pt", 0)
            return has_bold or font_size >= 13

    has_bold = any(r.get("bold") for r in runs)
    font_size = runs[0].get("font_size_pt", 0) if runs else 0
    if has_bold and 16 <= font_size < 26:
        if len(text) <= 30 and not text.endswith(('。', '，', '：', '.', ',', ':', '；', ';')):
            if any(kw in text for kw in DEFAULT_COLLEGE_KEYWORDS):
                return False
            return True

    return False


def _is_annotation(elem: dict) -> bool:
    runs = elem.get("runs", [])
    if not runs:
        return False

    if any(r.get("italic") for r in runs):
        return True

    for r in runs:
        font_color = r.get("font_color", "").upper()
        if font_color in ["FF0000", "CC0000", "FF3333", "FF6666", "CC3333"]:
            return True

    text = elem.get("text", "").strip()
    hint_patterns = [
        r'[（(]\s*(注|说明|提示|注意|Note|Hint|Remark|Attention)\s*[：:)]',
        r'^(注|说明|提示|注意|Note|Hint|Remark)\s*[：:]',
    ]
    for pattern in hint_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


def _analyze_format_rules(raw: dict) -> dict:
    rules = raw.get("format_rules", {})

    for elem in raw.get("elements", []):
        text = elem.get("text", "")
        format_keywords = [
            "格式要求", "行间距", "字体要求", "字号要求",
            "format requirement", "line spacing", "font size",
            "首行缩进", "段间距", "排版要求", "排版格式",
        ]
        for kw in format_keywords:
            if kw in text.lower() or kw in text:
                break

    if not rules.get("body_text"):
        rules["body_text"] = {"font_name": "宋体", "font_size_pt": 12.0}

    if not rules.get("section_header"):
        rules["section_header"] = {"font_name": "黑体", "font_size_pt": 14.0, "bold": True}

    if not rules.get("line_spacing_pt"):
        rules["line_spacing_pt"] = 22

    if not rules.get("first_line_indent_chars"):
        rules["first_line_indent_chars"] = 2

    rules["space_before"] = 0
    rules["space_after"] = 0

    return rules


def _detect_annotation_patterns(raw: dict) -> list:
    patterns = set()
    for elem in raw.get("elements", []):
        text = elem.get("text", "").strip()
        if _is_annotation(elem) and text:
            delete_keywords = [
                ("删除此注释", "删除此注释"), ("删除注释", "删除注释"),
                ("删除此说明", "删除此说明"), ("删除说明", "删除说明"),
                ("delete this note", "delete this note"),
                ("remove this", "remove this"),
                ("delete this", "delete this"),
                ("请删除", "请删除"),
                ("可删除", "可删除"),
                ("可以删除", "可以删除"),
            ]
            for keyword, pattern in delete_keywords:
                if keyword in text.lower():
                    patterns.add(pattern)

    return list(patterns)


def _detect_removal_patterns(raw: dict) -> list:
    patterns = []
    seen = set()
    for elem in raw.get("elements", []):
        text = elem.get("text", "").strip()
        removal_keywords = [
            "不需要列程序源代码", "不需要列源代码",
            "do not include source code", "no source code needed",
            "打包", "命名格式",
        ]
        for kw in removal_keywords:
            if kw in text and kw not in seen:
                patterns.append(kw)
                seen.add(kw)

    return patterns


def _collect_all_fields(profile: dict) -> list:
    fields = []
    seen_keys = set()

    for f in profile.get("cover_page", {}).get("fields", []):
        key = f.get("key", "")
        if key not in seen_keys:
            fields.append({"source": "cover_page", **f})
            seen_keys.add(key)

    for table in profile.get("tables", []):
        for f in table.get("fields", []):
            key = f.get("key", "")
            unique_key = f"{key}_t{table['index']}_{f.get('cell', '')}"
            if unique_key not in seen_keys:
                fields.append({"source": f"table_{table['index']}", **f})
                seen_keys.add(unique_key)

    return fields


def _extract_run_style(run: dict) -> dict:
    style = {}
    for key in ["font_name", "font_size_pt", "bold", "italic", "underline", "font_color"]:
        if key in run:
            style[key] = run[key]
    return style


def _extract_paragraph_style(elem: dict) -> dict:
    style = {}
    for key in ["alignment", "first_line_indent_cm", "line_spacing", "space_before_pt", "space_after_pt"]:
        if key in elem:
            style[key] = elem[key]
    return style


def _extract_cell_style(paras: list) -> dict:
    if not paras:
        return {}
    p = paras[0]
    style = _extract_paragraph_style(p)
    if p.get("runs"):
        style.update(_extract_run_style(p["runs"][0]))
    return style


def save_profile(profile: dict, output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
