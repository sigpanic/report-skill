import os
import json
import re
import tempfile
from typing import Optional

from src.template_parser.parser import doc_to_docx, parse_template
from src.protocol.ts_generator import generate_all_ts_interfaces


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
        fid = f"f{fmt_counter[0]}"
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
        "formats": fmt_catalog,
        "content": []
    }

    for elem in raw.get("elements", []):
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

            if run_fmt_id:
                compact_runs.append({"t": run_text, "f": run_fmt_id})
            else:
                compact_runs.append(run_text)

        elem_compact = {}
        if text:
            elem_compact["text"] = text
        if para_fmt_id:
            elem_compact["pf"] = para_fmt_id
        if compact_runs:
            elem_compact["runs"] = compact_runs

        if elem_compact:
            elem_compact["type"] = "p"
            compact["content"].append(elem_compact)

    for table_data in raw.get("tables", []):
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
                    if rfmt_id:
                        cell_run_fmts.append({"t": rtext, "f": rfmt_id})
                    else:
                        cell_run_fmts.append(rtext)

            if cell_run_fmts:
                cell_info["runs"] = cell_run_fmts

            compact_cells.append(cell_info)

        table_compact["cells"] = compact_cells
        compact["content"].append(table_compact)

    compact["formats"] = fmt_catalog

    return compact


def get_analysis_guide() -> str:
    ts_interfaces = generate_all_ts_interfaces()
    return f"""请根据以上紧凑模板数据，分析模板结构并生成TemplateProfile JSON。

## 数据格式说明
- `formats`: 格式目录，键为格式ID(如f1,f2)，值为格式属性
- `content`: 内容数组，每项type为"p"(段落)或"table"(表格)
- 段落中`pf`引用段落格式，runs中`f`引用run格式
- runs中的字符串表示纯文本(无特殊格式)
- 表格cells中`r`=行,`c`=列,`cs`=列跨,`rs`=行跨

## 分析步骤
1. **识别封面页**: 文档开头，包含大字标题(font_size_pt>=30)、学院名称、带冒号的标签字段
2. **识别表格字段**: 表格中左侧列通常是标签(如"实验名称")，右侧列是值区域
3. **识别章节标题**: 加粗+编号的段落(如"一、实验目的"、"1. Introduction")
4. **识别注释/说明**: 斜体(italic)、红色(font_color=FF0000)、含"删除"/"注"等关键词的段落
5. **识别格式要求**: 含"字体"/"字号"/"行间距"/"缩进"等关键词的段落

## ⚠️ 必须严格按照以下TypeScript接口定义输出JSON
以下接口定义由Pydantic模型自动生成，是数据结构的唯一标准：

```typescript
{ts_interfaces}
```

## 关键规则
- key必须用英文: student_name, student_id, student_class, course_name, experiment_name, experiment_date, experiment_location, teacher, score, comment
- 封面字段带下划线时type为"text_with_underline"
- 表格字段的cell格式为"行,列"(如"0,1")，label取相邻左侧单元格文本
- 章节note是该标题后、下一标题前的注释文本
- fields数组留空即可，系统会自动从cover_page和tables中汇总
- 如有不确定信息，询问用户"""


def save_compact(compact: dict, output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)


def save_profile(profile: dict, output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
