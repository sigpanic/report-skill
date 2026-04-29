import os
import json
import re

from src.template_parser.parser import parse_template
from src.protocol.ts_generator import generate_all_ts_interfaces


def _is_hint_format(fmt: dict) -> bool:
    if fmt.get("italic"):
        return True
    color = fmt.get("font_color", "")
    if color and color.upper() in ("FF0000", "FF0000FF"):
        return True
    return False


def _detect_format_keywords(text: str) -> list[str]:
    hints = []
    checks = [
        ("字体", ["宋体", "黑体", "楷体", "仿宋", "Times New Roman", "Arial", "Consolas"]),
        ("字号", ["小四", "小五", "四号", "五号", "小三", "三号", "12pt", "14pt", "10.5pt"]),
        ("行间距", ["行间距", "行距", "固定值", "多倍"]),
        ("缩进", ["首行缩进", "缩进"]),
        ("段间距", ["段前", "段后"]),
        ("对齐", ["居中", "左对齐", "右对齐", "两端对齐"]),
        ("加粗", ["加粗"]),
        ("磅", ["磅"]),
    ]
    for category, keywords in checks:
        matched = [kw for kw in keywords if kw in text]
        if matched:
            hints.append(f"{category}({','.join(matched)})")
    return hints


def analyze_template_compact(template_path: str) -> dict:
    raw = parse_template(template_path)

    compact = {
        "page_setup": raw.get("page_setup", {}),
        "header_footer": raw.get("header_footer", {}),
        "content": [],
        "_draft_format_rules": raw.get("format_rules", {})
    }

    for elem in raw.get("content", []):
        if elem.get("type") == "table":
            table_data = elem
            table_compact = {
                "type": "table",
                "rows": table_data.get("rows", 0),
                "cols": table_data.get("cols", 0),
            }
            if table_data.get("column_widths_cm"):
                table_compact["col_widths"] = table_data["column_widths_cm"]

            compact_cells = []
            for cell in table_data.get("cells", []):
                cell_info = {"r": cell["row"], "c": cell["col"]}
                cell_text = cell.get("text", "").strip()
                if cell_text:
                    cell_info["text"] = cell_text
                if cell.get("colspan"):
                    cell_info["cs"] = cell["colspan"]
                if cell.get("rowspan"):
                    cell_info["rs"] = cell["rowspan"]

                for p in cell.get("paragraphs", []):
                    for r in p.get("runs", []):
                        rfmt = {}
                        for key in ["font_name", "font_size_pt", "bold", "italic", "underline", "font_color"]:
                            val = r.get(key)
                            if val is not None and val != False and val != "":
                                rfmt[key] = val
                        if rfmt and _is_hint_format(rfmt):
                            cell_info["hint"] = True

                compact_cells.append(cell_info)

            table_compact["cells"] = compact_cells
            compact["content"].append(table_compact)
            continue

        text = elem.get("text", "").strip()
        runs = elem.get("runs", [])
        is_hint = False

        for run in runs:
            rfmt = {}
            for key in ["font_name", "font_size_pt", "bold", "italic", "underline", "font_color"]:
                val = run.get(key)
                if val is not None and val != False and val != "":
                    rfmt[key] = val
            if rfmt and _is_hint_format(rfmt):
                is_hint = True
                break

        elem_compact = {"type": "p"}
        if text:
            elem_compact["text"] = text
        if is_hint:
            elem_compact["hint"] = True

        compact["content"].append(elem_compact)

    _add_content_types(compact)
    _add_structure_summary(compact)
    _detect_format_notes(compact)

    return compact


_SECTION_PATTERN = re.compile(
    r'^[一二三四五六七八九十]+、'
    r'|^(?:Chapter|Section|Part|Lesson|Unit|Topic|Module)\s+\d'
    r'|^\d+[\.\)、]\s'
    r'|^\d+\.\d+(?:\s|$)'
    r'|^Appendix\s+[A-Z]'
    r'|^(?:Introduction|Background|Purpose|Objectives?|Methods?|Results?|Discussion|Conclusions?|Summary|References?|Abstract)'
    r'(?:[：:\.\s]|$)',
    re.IGNORECASE
)
_COVER_FIELD_PATTERN = re.compile(r'[：:]')
_FORMAT_NOTE_KEYWORDS = [
    "字体", "字号", "行间距", "行距", "缩进", "首行缩进",
    "格式要求", "报告格式", "排版", "版式", "段距", "段前", "段后",
    "页边距", "页眉", "页脚", "页码", "字距", "字符间距",
    "对齐方式", "加粗", "居中",
    "font", "spacing", "indent", "margin", "format",
]


def _add_content_types(compact: dict):
    content = compact.get("content", [])
    if not content:
        return

    found_title = False
    found_first_section = False

    for item in content:
        if item.get("type") == "table":
            item["content_type"] = "table"
            continue

        text = item.get("text", "").strip()

        if not text and not found_title:
            item["content_type"] = "cover_spacer"
            continue

        if not found_title and len(text) <= 30:
            is_centered = False  # can't determine alignment without para_fmt
            item["content_type"] = "cover_title"
            found_title = True
            continue

        if item.get("hint"):
            item["content_type"] = "section_note"
            continue

        if _SECTION_PATTERN.match(text):
            item["content_type"] = "section_title"
            found_first_section = True
            continue

        if not found_first_section and text and not _SECTION_PATTERN.match(text) and "：" not in text and ":" not in text:
            item["content_type"] = "cover_college"
            continue

        has_colon = "：" in text or ":" in text
        if has_colon and found_title:
            item["content_type"] = "cover_field"
            continue

        if any(kw in text.lower() for kw in _FORMAT_NOTE_KEYWORDS):
            item["content_type"] = "format_note"
            continue

        item["content_type"] = "section_body"


def _add_structure_summary(compact: dict):
    content = compact.get("content", [])
    summary = {
        "cover_title": "",
        "cover_fields": [],
        "cover_college": "",
        "sections": [],
        "tables_count": 0,
        "notes_count": 0,
    }

    for item in content:
        ct = item.get("content_type", "")
        text = item.get("text", "")
        if ct == "cover_title":
            summary["cover_title"] = text
        elif ct == "cover_field":
            label = text.split("：")[0].split(":")[0] if "：" in text or ":" in text else text
            summary["cover_fields"].append(label or text)
        elif ct == "cover_college":
            summary["cover_college"] = text
        elif ct == "section_title":
            summary["sections"].append(text)
        elif ct == "table":
            summary["tables_count"] += 1
        elif ct in ("section_note", "format_note"):
            summary["notes_count"] += 1

    compact["_summary"] = summary


def _find_next_non_blank(compact: dict, start_idx: int) -> dict:
    content = compact.get("content", [])
    for i in range(start_idx, len(content)):
        item = content[i]
        if item.get("type") == "p" and item.get("text", "").strip():
            return item
    return {}


def _detect_format_notes(compact: dict):
    content = compact.get("content", [])
    all_hints = []

    for i, item in enumerate(content):
        if item.get("content_type") in ("section_note", "format_note"):
            text = item.get("text", "")
            found = _detect_format_keywords(text)
            if found:
                all_hints.append({
                    "index": i,
                    "type": item["content_type"],
                    "text": text[:80] + "..." if len(text) > 80 else text,
                    "format_keywords": found,
                })

    if all_hints:
        compact["_format_notes"] = all_hints


def check_profile_completeness(profile: dict, compact: dict) -> list:
    # toagent: 此处必须保持中文，严禁改成英文
    warnings = []

    if not profile.get("annotation_patterns"):
        warnings.append("⚠️ annotation_patterns为空！模板中的注释/提示文本可能不会被删除。请检查模板中的斜体/红色/含'注'/'删除'的段落")

    if not profile.get("removal_patterns"):
        warnings.append("⚠️ removal_patterns为空！模板中的'删除此注释'等文本可能不会被删除")

    cover_fields = profile.get("cover_page", {}).get("fields", [])
    if not cover_fields:
        warnings.append("⚠️ cover_page.fields为空！封面字段未识别")

    tables = profile.get("tables", [])
    for table in tables:
        table_fields = table.get("fields", [])
        for field in table_fields:
            if field.get("is_hint") is None:
                warnings.append(f"⚠️ 表格字段 '{field.get('key', '')}' 的is_hint未设置")
            cell = field.get("cell", "")
            if "_" in cell and "," not in cell:
                warnings.append(f"⚠️ 表格字段 '{field.get('key', '')}' 的cell格式可能错误：'{cell}'，应为'行,列'格式如'0,1'")

    sections = profile.get("sections", [])
    if not sections:
        warnings.append("⚠️ sections为空！章节未识别")

    for section in sections:
        has_annotation = False
        for idx, elem in enumerate(compact.get("content", [])):
            if elem.get("type") == "p" and elem.get("text", "").strip() == section.get("title", ""):
                next_elem = _find_next_non_blank(compact, idx + 1)
                if next_elem and next_elem.get("hint"):
                    has_annotation = True
                break
        if has_annotation and not section.get("requirements"):
            warnings.append(f"⚠️ 章节 '{section.get('title', '')}' 后有注释文本，但requirements为空！必须将约束提取到requirements数组中")

    format_rules = profile.get("format_rules", {})
    if not format_rules.get("body_text", {}).get("font_name"):
        warnings.append("⚠️ format_rules.body_text.font_name未设置")
    if not format_rules.get("section_header") or not format_rules.get("section_header", {}).get("font_name"):
        warnings.append("⚠️ format_rules.section_header.font_name未设置（描述性字段，不影响文档生成）")

    for section in sections:
        requirements = section.get("requirements", [])
        if not requirements:
            title = section.get("title", "")
            for idx, elem in enumerate(compact.get("content", [])):
                if elem.get("type") == "p" and elem.get("text", "").strip() == title:
                    next_elem = _find_next_non_blank(compact, idx + 1)
                    if next_elem:
                        next_text = next_elem.get("text", "")
                        hints = []
                        if "不少于" in next_text or "至少" in next_text or "以上" in next_text:
                            hints.append("数量约束")
                        if "字体" in next_text or "font" in next_text.lower():
                            hints.append("字体要求")
                        if "表格" in next_text or "列" in next_text:
                            hints.append("表格结构")
                        if "截图" in next_text or "流程图" in next_text or "图" in next_text:
                            hints.append("内容要求")
                        if "不需要" in next_text or "不要" in next_text or "禁止" in next_text or "不可" in next_text or "不能" in next_text or "无需" in next_text:
                            hints.append("禁止内容")
                        if hints:
                            warnings.append(f"⚠️ 章节 '{title}' 后有注释文本包含约束（{', '.join(hints)}），但requirements为空！必须将约束提取到requirements数组中")
                    break

    compact_tables = [e for e in compact.get("content", []) if e.get("type") == "table"]
    if compact_tables and not tables:
        warnings.append("⚠️ compact数据中有表格但Profile的tables为空！表格信息可能遗漏")

    return warnings


def get_analysis_guide() -> str:
    # toagent: 此处必须保持中文，严禁改成英文
    ts_interfaces = generate_all_ts_interfaces()
    return f"""请根据以上compact数据，分析模板结构并编写TemplateProfile JSON。

## 📋 模板结构概览（_summary字段）
compact数据中的`_summary`字段已自动提取模板的核心结构：
- `cover_title`: 封面标题文本
- `cover_fields`: 封面字段标签列表
- `cover_college`: 学院/学校名称
- `sections`: 章节标题列表
- `tables_count`: 表格数量
- `notes_count`: 注释/说明段落数量

## 📋 格式要求检测（_format_notes字段 + _draft_format_rules字段）
- `_draft_format_rules`: 代码已自动从文档正文中提取了一份格式规则（统计最常用字体字号作为body_text，统计加粗大字号作为section_header）
  **此为参考值，LLM需根据注释原文确认或修正。**
- `_format_notes`: 注释文字中检测到的格式关键词列表，提醒你有哪些格式相关约束需要处理
  **注意：自动检测仅供参考，不一定完整，你需要自己阅读注释原文确认所有格式要求。**
- 格式决定原则：注释原文有明确说明的按注释走，没有说明的用_draft_format_rules的提取值

## 数据格式说明
- `content`: 内容数组，每项type为"p"(段落)或"table"(表格)
- 每个内容项已自动标注`content_type`字段：
  - `cover_spacer` — 封面空白段落
  - `cover_title` — 封面标题
  - `cover_field` — 封面字段行（标签+下划线区域）
  - `cover_college` — 学院/学校名称行
  - `section_title` — 章节标题
  - `section_note` — 注释说明段落（斜体/红色文本，会被自动删除）
  - `format_note` — 格式要求说明段落（会被自动删除）
  - `section_body` — 正文引导段落
  - `table` — 表格
- `hint: true` 表示该段落是注释/提示文本
- 表格cells中`r`=行,`c`=列,`cs`=列跨,`rs`=行跨，`hint: true` 表示该cell是提示文本

## 分析步骤
1. **识别封面页**: 阅读开头段落，找到封面标题和字段
2. **识别表格字段**: 表格中左侧列通常是标签，右侧列是值区域。`hint: true` 的cell是提示不是默认值
3. **识别章节**: 阅读 section_title 列表获取章节结构
4. **阅读注释**: section_note/format_note 包含约束和格式要求，提取到 requirements
5. **格式要求**: 阅读 _format_notes 检测到的格式关键词 + 注释原文，决定 format_rules 和 content_style
6. **识别自然语言需求**: 约束类型有 min_count / font / table_structure / format / content / forbidden / other

## 关键规则
- 字段key用英文: student_name, student_id, student_class, course_name, experiment_name 等
- 封面字段带下划线时type为"text_with_underline"，不带为"text"
- 表格cell格式为"行,列"(如"0,1")，label取相邻左侧单元格文本
- 表格中`hint: true` 的cell对应字段的 is_hint 必须设为 true
- 表格中标签列不是字段，只有值列才是字段
- annotation_patterns和removal_patterns不能为空！
- fields不需要填写，系统会自动从cover_page.fields和tables[].fields中汇总
- 确定格式规则时：模板注释中有明确说明的优先，没有的用代码提取的默认值
- 如有不确定信息，询问用户"""


def save_compact(compact: dict, output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)
