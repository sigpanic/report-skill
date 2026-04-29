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


def _describe_format_id(fmt: dict, seq: int) -> str:
    parts = []
    fn = fmt.get("font_name", "")
    if fn:
        label = fn[:6]
        parts.append(label)
    fs = fmt.get("font_size_pt", 0)
    if fs:
        parts.append(f"{int(fs)}pt")
    if fmt.get("bold"):
        parts.append("b")
    if fmt.get("italic"):
        parts.append("i")
    if fmt.get("underline"):
        parts.append("u")
    color = fmt.get("font_color", "")
    if color and color.upper() in ("FF0000", "FF0000FF"):
        parts.append("red")
    if not parts:
        return f"f{seq}"
    return "_".join(parts) + f"_{seq}"


def analyze_template_compact(template_path: str) -> dict:
    raw = parse_template(template_path)

    fmt_catalog = {}
    fmt_key_to_id = {}
    fmt_counter = [0]

    def get_fmt_id(fmt_dict: dict) -> str:
        if not fmt_dict:
            return ""
        key = json.dumps(fmt_dict, sort_keys=True, ensure_ascii=False)
        if key in fmt_key_to_id:
            return fmt_key_to_id[key]
        fmt_counter[0] += 1
        fid = _describe_format_id(fmt_dict, fmt_counter[0])
        fmt_catalog[fid] = fmt_dict
        fmt_key_to_id[key] = fid
        return fid

    def extract_run_fmt(run: dict) -> dict:
        fmt = {}
        for key in ["font_name", "font_size_pt", "bold", "italic", "underline", "font_color"]:
            val = run.get(key)
            if val is not None and val != False and val != "":
                fmt[key] = val
        return fmt

    def extract_para_fmt(elem: dict) -> dict:
        fmt = {}
        for key in ["alignment", "first_line_indent_cm", "line_spacing",
                     "space_before_pt", "space_after_pt"]:
            val = elem.get(key)
            if val is not None and val != 0 and val != "":
                fmt[key] = val
        return fmt

    compact = {
        "page_setup": raw.get("page_setup", {}),
        "header_footer": raw.get("header_footer", {}),
        "formats": fmt_catalog,
        "content": []
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

                paras = cell.get("paragraphs", [])
                cell_run_fmts = []
                for p in paras:
                    for r in p.get("runs", []):
                        rtext = r.get("text", "")
                        if not rtext:
                            continue
                        rfmt = extract_run_fmt(r)
                        rfmt_id = get_fmt_id(rfmt)
                        is_hint = rfmt_id and _is_hint_format(rfmt)

                        if cell_run_fmts and isinstance(cell_run_fmts[-1], dict) and cell_run_fmts[-1].get("f") == rfmt_id and cell_run_fmts[-1].get("hint") == is_hint:
                            cell_run_fmts[-1]["t"] += rtext
                        else:
                            if rfmt_id:
                                entry = {"t": rtext, "f": rfmt_id}
                                if is_hint:
                                    entry["hint"] = True
                                cell_run_fmts.append(entry)
                            else:
                                cell_run_fmts.append({"t": rtext})

                if cell_run_fmts:
                    cell_info["runs"] = cell_run_fmts

                compact_cells.append(cell_info)

            table_compact["cells"] = compact_cells
            compact["content"].append(table_compact)
            continue

        text = elem.get("text", "").strip()
        runs = elem.get("runs", [])

        para_fmt_id = get_fmt_id(extract_para_fmt(elem))

        compact_runs = []
        for run in runs:
            run_text = run.get("text", "")
            if not run_text and not run.get("underline"):
                continue
            run_fmt = extract_run_fmt(run)
            run_fmt_id = get_fmt_id(run_fmt)

            is_hint = run_fmt_id and _is_hint_format(run_fmt)

            is_trailing_space = run_text.strip() == "" and not run.get("underline") and not is_hint
            if is_trailing_space and compact_runs:
                continue

            if compact_runs and compact_runs[-1].get("f") == run_fmt_id and bool(compact_runs[-1].get("hint")) == bool(is_hint):
                compact_runs[-1]["t"] += run_text
            else:
                entry = {}
                if run_fmt_id:
                    entry["f"] = run_fmt_id
                    if is_hint:
                        entry["hint"] = True
                compact_runs.append({"t": run_text, **entry} if entry else {"t": run_text})

        elem_compact = {}
        if text:
            elem_compact["text"] = text
        if para_fmt_id:
            elem_compact["pf"] = para_fmt_id
        if compact_runs:
            if len(compact_runs) == 1 and compact_runs[0].get("t", "").strip() == text and not compact_runs[0].get("hint"):
                pass
            else:
                elem_compact["runs"] = compact_runs

        if not text and not compact_runs:
            continue

        if elem_compact:
            elem_compact["type"] = "p"
            compact["content"].append(elem_compact)

    compact["formats"] = fmt_catalog

    _add_content_types(compact)
    _add_structure_summary(compact)
    compact["_text_overview"] = _generate_text_overview(compact)

    return compact


_SECTION_PATTERN = re.compile(r'^[一二三四五六七八九十]+、|^(?:Chapter|Section)\s+\d|^(\d+[\.\)])\s')
_COVER_FIELD_PATTERN = re.compile(r'[：:]')


def _add_content_types(compact: dict):
    fmt = compact.get("formats", {})
    content = compact.get("content", [])
    if not content:
        return

    cover_field_count = 0
    found_title = False
    found_first_section = False
    current_section = None

    _FORMAT_NOTE_KEYWORDS = [
        "字体", "字号", "行间距", "行距", "缩进", "首行缩进",
        "格式要求", "报告格式", "排版", "版式", "段距", "段前", "段后",
        "页边距", "页眉", "页脚", "页码", "字距", "字符间距",
        "对齐方式", "加粗", "居中",
        "font", "spacing", "indent", "margin", "format",
    ]

    for item in content:
        if item.get("type") == "table":
            item["content_type"] = "table"
            continue

        text = item.get("text", "").strip()
        pf = item.get("pf", "")
        pf_info = fmt.get(pf, {})
        runs = item.get("runs", [])

        if not text and not found_title:
            item["content_type"] = "cover_spacer"
            continue

        if not found_title and len(text) <= 30:
            max_font_size = 0
            for r in runs:
                if isinstance(r, dict):
                    rf = fmt.get(r.get("f", ""), {})
                    fs = rf.get("font_size_pt", 0)
                    if fs and fs > max_font_size:
                        max_font_size = fs
            is_centered = pf_info.get("alignment") and "CENTER" in str(pf_info.get("alignment", "")).upper()
            if max_font_size >= 16 or (not max_font_size and is_centered and not _COVER_FIELD_PATTERN.search(text) and not _SECTION_PATTERN.match(text)):
                item["content_type"] = "cover_title"
                found_title = True
                continue

        if not found_first_section and text and not _SECTION_PATTERN.match(text) and "：" not in text and ":" not in text:
            pf_info2 = fmt.get(item.get("pf", ""), {})
            if pf_info2.get("alignment") and "CENTER" in str(pf_info2.get("alignment", "")).upper():
                item["content_type"] = "cover_college"
                continue

        has_underline = False
        has_colon = False
        for r in runs:
            if isinstance(r, dict):
                rf = fmt.get(r.get("f", ""), {})
                if rf.get("underline"):
                    has_underline = True
                if "：" in r.get("t", "") or ":" in r.get("t", ""):
                    has_colon = True
        if has_colon and has_underline:
            item["content_type"] = "cover_field"
            cover_field_count += 1
            continue

        if _SECTION_PATTERN.match(text):
            item["content_type"] = "section_title"
            current_section = text
            found_first_section = True
            continue

        has_italic = any(
            fmt.get(r.get("f", ""), {}).get("italic") for r in runs if isinstance(r, dict)
        )
        has_red = False
        for r in runs:
            if isinstance(r, dict):
                rf = fmt.get(r.get("f", ""), {})
                color = rf.get("font_color", "")
                if color and color.upper() in ("FF0000", "FF0000FF"):
                    has_red = True
                    break
        if has_italic or has_red:
            item["content_type"] = "section_note"
            continue

        if any(kw in text.lower() for kw in _FORMAT_NOTE_KEYWORDS):
            item["content_type"] = "format_note"
            continue

        item["content_type"] = "section_body"


def _add_structure_summary(compact: dict):
    content = compact.get("content", [])
    fmt = compact.get("formats", {})

    cover_title = ""
    cover_fields = []
    cover_college = ""
    sections = []
    tables_count = 0
    notes_count = 0

    for item in content:
        ct = item.get("content_type", "")
        if ct == "cover_title":
            cover_title = item.get("text", "")
        elif ct == "cover_field":
            text = item.get("text", "")
            label = ""
            for r in item.get("runs", []):
                if isinstance(r, dict):
                    rt = r.get("t", "")
                    if "：" in rt or ":" in rt:
                        label = rt
                        break
            cover_fields.append(label or text)
        elif ct == "cover_college":
            cover_college = item.get("text", "")
        elif ct == "section_title":
            sections.append(item.get("text", ""))
        elif ct == "table":
            tables_count += 1
        elif ct in ("section_note", "format_note"):
            notes_count += 1

    summary = {
        "cover_title": cover_title,
        "cover_fields": cover_fields,
        "cover_college": cover_college,
        "sections": sections,
        "tables_count": tables_count,
        "notes_count": notes_count,
    }

    compact["_summary"] = summary


def _find_next_non_blank(compact: dict, start_idx: int) -> dict:
    content = compact.get("content", [])
    for i in range(start_idx, len(content)):
        item = content[i]
        if item.get("type") == "p" and item.get("text", "").strip():
            return item
    return {}


def _generate_text_overview(compact: dict) -> str:
    fmt = compact.get("formats", {})
    content = compact.get("content", [])
    lines = []
    section_counter = [0]

    for item in content:
        ct = item.get("content_type", "")
        text = item.get("text", "")

        if ct == "cover_spacer":
            lines.append("")

        elif ct == "cover_title":
            lines.append(f"[COVER TITLE] {text}")

        elif ct == "cover_field":
            tag = "[COVER FIELD]"
            runs = item.get("runs", [])
            has_ul = any(
                fmt.get(r.get("f", ""), {}).get("underline")
                for r in runs if isinstance(r, dict)
            )
            if has_ul:
                tag = "[COVER FIELD (underline)]"
            lines.append(f"  {tag} {text}")

        elif ct == "cover_college":
            lines.append(f"  [COVER FIELD] {text}")

        elif ct == "section_title":
            section_counter[0] += 1
            lines.append("")
            lines.append(f"[SECTION {section_counter[0]}] {text}")

        elif ct == "section_note":
            lines.append(f"  [HINT] {text}")

        elif ct == "format_note":
            lines.append(f"  [FORMAT] {text}")

        elif ct == "section_body":
            short = text[:120] + "..." if len(text) > 120 else text
            lines.append(f"  [BODY] {short}")

        elif ct == "table":
            rows = item.get("rows", 0)
            cols = item.get("cols", 0)
            lines.append(f"  [TABLE: {rows}x{cols}]")
            cells = item.get("cells", [])
            if cells:
                grid = {}
                for cell in cells:
                    grid[(cell["r"], cell["c"])] = cell.get("text", "")
                for r in range(min(rows, 8)):
                    row_cells = []
                    for c in range(cols):
                        val = grid.get((r, c), "")
                        short_val = val[:20]
                        row_cells.append(short_val)
                    lines.append(f"    | {' | '.join(row_cells)} |")
                if rows > 8:
                    lines.append(f"    ... ({rows - 8} more rows)")

    return "\n".join(lines)


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
                if next_elem:
                    next_runs = next_elem.get("runs", [])
                    formats = compact.get("formats", {})
                    for r in next_runs:
                        if isinstance(r, dict):
                            f = formats.get(r.get("f", ""), {})
                            if f.get("italic"):
                                has_annotation = True
                            color = f.get("font_color", "")
                            if color and color.upper() in ("FF0000", "FF0000FF"):
                                has_annotation = True
                break
        if has_annotation and not section.get("requirements"):
            warnings.append(f"⚠️ 章节 '{section.get('title', '')}' 后有斜体注释文本，但requirements为空！必须将注释中的约束提取到requirements数组中")

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
compact数据中的`_summary`字段已自动提取模板的核心结构，你可以直接参考它快速了解模板：
- `cover_title`: 封面标题文本
- `cover_fields`: 封面字段标签列表（如["实验课程：", "学生姓名："]）
- `cover_college`: 学院/学校名称
- `sections`: 章节标题列表（如["一、实验目的", "二、实验环境"]）
- `tables_count`: 表格数量
- `notes_count`: 注释/说明段落数量

⚠️ _summary仅供参考，你仍需仔细阅读content数组中的详细数据来提取格式、约束等细节信息。

## 数据格式说明
- `formats`: 格式目录，键为格式ID(如f1,f2)，值为格式属性
- `content`: 内容数组，每项type为"p"(段落)或"table"(表格)
- 每个内容项已自动标注`content_type`字段，帮助你快速理解其语义角色：
  - `cover_spacer` — 封面空白段落
  - `cover_title` — 封面标题（如"实  验  报  告"）
  - `cover_field` — 封面字段行（如"学生姓名："）
  - `cover_college` — 学院/学校名称行（应作为cover_page.fields中的一个字段）
  - `section_title` — 章节标题（如"一、实验目的"）
  - `section_note` — 斜体/红色注释说明段落（会被自动删除）
  - `format_note` — 格式要求说明段落（会被自动删除）
  - `section_body` — 正文引导段落
  - `table` — 表格
- 段落中`pf`引用段落格式，runs中`f`引用run格式
- runs中的字符串表示纯文本(无特殊格式)
- 红色斜体运行的run条目已自动标注`"hint": true`，表示这是提示/注释文本
- 表格cells中`r`=行,`c`=列,`cs`=列跨,`rs`=行跨
- `header_footer`: 页眉页脚信息，包含header和footer数组，每个条目有section_index、header_text/footer_text、different_first_page

## 分析步骤
1. **识别封面页**: 文档开头，包含大字标题(font_size_pt>=16)、带冒号的标签字段
2. **识别表格字段**: 表格中左侧列通常是标签(如"实验名称")，右侧列是值区域。红色/斜体文本是提示
3. **识别章节标题**: 加粗+编号的段落(如"一、实验目的"、"1. Introduction")
4. **识别注释/说明**: 斜体(italic)、红色(font_color=FF0000)、含"删除"/"注"等关键词的段落
5. **识别格式要求**: 含"字体"/"字号"/"行间距"/"缩进"等关键词的段落
6. **识别自然语言需求**: 模板中可能包含以下类型的自然语言约束，必须提取到对应章节的requirements数组中：
   - **数量约束** (type="min_count"): 如"不少于4个实验目的"、"至少3种方法" → description="不少于4个实验目的", value="4"
   - **字体要求** (type="font"): 如"代码部分请使用Consolas字体"、"英文用Times New Roman" → description="代码部分请使用Consolas字体", value="Consolas"
   - **表格结构** (type="table_structure"): 如"表格需包含3列：方法、时间复杂度、空间复杂度" → description="表格需包含3列：方法、时间复杂度、空间复杂度"
   - **格式要求** (type="format"): 如"此部分首行缩进2字符"、"行间距固定值20磅" → description="此部分首行缩进2字符"
   - **内容要求** (type="content"): 如"需要包含算法流程图"、"需附运行结果截图" → description="需要包含算法流程图"
   - **禁止内容** (type="forbidden"): 如"不需要列程序源代码"、"不要附源代码"、"禁止使用图片" → description="不需要列程序源代码"
     ⚠️ 仅用于章节级禁止。全局禁止（适用于整篇报告）应通过constraints参数传入，不放在requirements中
   - **其他约束** (type="other"): 不属于以上类别的约束
   ⚠️ **所有约束必须提取到requirements数组中。SectionInfo没有note字段——所有约束信息必须以结构化方式放入requirements。**
7. **识别per-section内容样式**: 如果模板中某个章节有特殊的格式要求（如代码用等宽字体、摘要用楷体），在content_style中指定。content_style为空时使用全局body_text样式。content_style中的字段会覆盖body_text中的对应字段（继承+覆盖语义）
8. **识别隐式需求**: 约束不一定以独立段落出现，还可能隐藏在以下位置：
   - **章节标题中的括号内容**: 如"实验目的（不少于4个）" → 提取为min_count, value="4"
   - **章节标题中的数量词**: 如"三种算法比较" → 提取为min_count, value="3"
   - **表格单元格中的提示**: 如"此处填写代码（需可运行）" → 提取为content类型requirement
   - **下划线区域的格式暗示**: 如封面下划线区域暗示此处需填写内容
   - **章节间的说明段落**: 如"以下各节均需包含运行结果截图" → 对后续每个章节添加content类型requirement
   - 识别到隐式需求后，同样提取到对应章节的requirements数组中
9. **识别全局约束**: 模板中有些约束适用于整篇报告而非特定章节（如"报告中不需要列程序源代码"、"所有图表需编号"等）。这些全局约束不应放在某个章节的requirements中，而应在调用generate_skill时通过constraints参数传入。constraints是一个字典，key为约束类别，value为约束内容（字符串、字典或列表）。例如：
   ```json
   {{"禁止内容": {{"源代码": "报告中不需要列程序源代码", "附件": "不需要附源代码电子版"}}, "格式要求": "所有图表必须编号"}}
   ```
   ⚠️ **constraints仅用于全局约束。章节级约束（如"实验目的不能少于4个"）必须放在对应章节的requirements中，不要放入constraints，否则会导致约束在Skill中重复出现**

## ⚠️ 必须严格按照以下TypeScript接口定义输出JSON
以下接口定义由Pydantic模型自动生成，是数据结构的唯一标准：

```typescript
{ts_interfaces}
```

## 关键规则
- key必须用英文: student_name, student_id, student_class, course_name, experiment_name, experiment_date, experiment_location, teacher, score, comment
- 封面字段带下划线时type为"text_with_underline"
- 表格字段的cell格式为"行,列"(如"0,1")，label取相邻左侧单元格文本
- 表格中红色(font_color=FF0000)或斜体(italic)的文本是提示，is_hint必须设为true
- 表格中标签列(如"实验名称")不是字段，只有值列才是字段
- ⚠️ annotation_patterns和removal_patterns不能为空！必须识别模板中的注释/提示文本模式
- fields不需要填写，系统会自动从cover_page.fields和tables[].fields中汇总
- 如有不确定信息，询问用户"""


def save_compact(compact: dict, output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)
