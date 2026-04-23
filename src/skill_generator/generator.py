import os
import json
from typing import Optional


def generate_skill(
    profile: dict,
    skill_name: str,
    output_path: str,
    constraints: Optional[dict] = None
) -> str:
    template_name = _infer_template_name(profile)
    fields_desc = _generate_fields_description(profile)
    sections_desc = _generate_sections_description(profile)
    format_desc = _generate_format_description(profile)
    constraints_desc = _generate_constraints_description(constraints)
    workflow_desc = _generate_workflow(profile, skill_name)
    template_rules = _generate_template_rules(profile)

    skill_content = f"""# {skill_name}

## 概述
本Skill用于自动生成「{template_name}」Word文档，严格遵循模板格式。

## 模板信息
- 模板文件: `{profile.get('template_path', '')}`
- 纸张大小: {_page_size_desc(profile)}
- 页边距: {_margin_desc(profile)}

## 模板规则

{template_rules}

## 工作流程

{workflow_desc}

## 字段定义

{fields_desc}

## 章节定义

{sections_desc}

## 格式规则

{format_desc}

## 约束规则

{constraints_desc}

## MCP工具调用

### 1. analyze_template（首次使用时调用）
分析Word模板，生成TemplateProfile。

参数：
- template_path (必需): 模板文件路径
- output_path (可选): Profile保存路径

### 2. generate_report（每次生成报告时调用）
生成报告Word文档。

参数：
- template_path (必需): 模板文件路径
- output_path (必需): 输出文件路径
- profile_path (必需): TemplateProfile JSON文件路径
- field_values (必需): 字段值字典，包含上述所有字段
- sections (必需): 章节内容数组，每项含title和content
- result_images (可选): 结果截图路径列表

### 3. verify_format（生成后验证）
对比生成的Word文档与模板的格式差异。

参数：
- template_path (必需): 模板文件路径
- generated_path (必需): 生成的文档路径

## 关键注意事项
- 生成的Word文档格式必须与模板完全一致，这是最高优先级
- 所有注释段落会被自动删除
- 章节内容按模板格式规则排版
- 图片居中插入，宽度12cm
- 如果有任何不确定的信息，直接询问用户，不要自己编造
- 模板中的注释和说明（如"写实验报告时删除此注释"）必须遵守
"""

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(skill_content)

    return output_path


def _infer_template_name(profile: dict) -> str:
    cover = profile.get("cover_page", {})
    title = cover.get("title", {})
    if title and title.get("text"):
        return title["text"].replace("  ", "").strip()

    for field in cover.get("fields", []):
        if "课程" in field.get("label", ""):
            return field.get("default", "") + "实验报告"

    return "实验报告"


def _generate_template_rules(profile: dict) -> str:
    lines = []
    annotation_patterns = profile.get("annotation_patterns", [])
    removal_patterns = profile.get("removal_patterns", [])
    sections = profile.get("sections", [])

    lines.append("### 必须遵守的规则")
    lines.append("")

    if annotation_patterns:
        lines.append("- 模板中包含需要删除的注释段落，系统会自动删除包含以下关键词的段落：")
        for p in annotation_patterns:
            lines.append(f"  - 「{p}」")
        lines.append("")

    if removal_patterns:
        lines.append("- 模板中包含需要删除的说明段落，系统会自动删除包含以下关键词的段落：")
        for p in removal_patterns:
            lines.append(f"  - 「{p}」")
        lines.append("")

    notes_found = []
    for sec in sections:
        note = sec.get("note", "")
        if note:
            notes_found.append(f"  - {sec['title']}: {note[:150]}{'...' if len(note) > 150 else ''}")

    if notes_found:
        lines.append("### 各章节模板说明（必须遵守）")
        lines.append("")
        for n in notes_found:
            lines.append(n)
        lines.append("")

    return "\n".join(lines)


def _generate_fields_description(profile: dict) -> str:
    lines = []
    fields = profile.get("fields", [])

    if not fields:
        return "（模板中无可填充字段）"

    cover_fields = [f for f in fields if f.get("source") == "cover_page"]
    table_fields = [f for f in fields if f.get("source", "").startswith("table_")]

    if cover_fields:
        lines.append("### 封面页字段")
        lines.append("")
        lines.append("| 字段Key | 标签 | 类型 | 默认值 |")
        lines.append("|---------|------|------|--------|")
        seen = set()
        for f in cover_fields:
            if f["key"] not in seen:
                lines.append(f"| `{f['key']}` | {f.get('label', '')} | {f.get('type', '')} | {f.get('default', '')} |")
                seen.add(f["key"])
        lines.append("")

    if table_fields:
        lines.append("### 表格字段")
        lines.append("")
        lines.append("| 字段Key | 标签 | 单元格 | 类型 |")
        lines.append("|---------|------|--------|------|")
        seen = set()
        for f in table_fields:
            unique = f"{f['key']}_{f.get('cell', '')}"
            if unique not in seen:
                lines.append(f"| `{f['key']}` | {f.get('label', '')} | {f.get('cell', '')} | {f.get('type', '')} |")
                seen.add(unique)
        lines.append("")

    return "\n".join(lines)


def _generate_sections_description(profile: dict) -> str:
    sections = profile.get("sections", [])

    if not sections:
        return "（模板中无章节定义）"

    lines = []
    for i, sec in enumerate(sections):
        lines.append(f"### {sec['title']}")
        if sec.get("note"):
            lines.append(f"- 模板说明: {sec['note'][:150]}{'...' if len(sec.get('note', '')) > 150 else ''}")
        style = sec.get("style", {})
        if style:
            style_parts = []
            if style.get("font_name"):
                style_parts.append(f"字体={style['font_name']}")
            if style.get("font_size_pt"):
                style_parts.append(f"字号={style['font_size_pt']}pt")
            if style.get("bold"):
                style_parts.append("加粗")
            if style_parts:
                lines.append(f"- 标题样式: {', '.join(style_parts)}")
        lines.append("")

    return "\n".join(lines)


def _generate_format_description(profile: dict) -> str:
    rules = profile.get("format_rules", {})
    lines = []

    body = rules.get("body_text", {})
    header = rules.get("section_header", {})

    body_parts = []
    if body.get("font_name"):
        body_parts.append(f"字体={body['font_name']}")
    if body.get("font_size_pt"):
        body_parts.append(f"字号={body['font_size_pt']}pt")
    lines.append(f"- 正文: {', '.join(body_parts) if body_parts else '宋体, 12pt'}")

    header_parts = []
    if header.get("font_name"):
        header_parts.append(f"字体={header['font_name']}")
    if header.get("font_size_pt"):
        header_parts.append(f"字号={header['font_size_pt']}pt")
    if header.get("bold"):
        header_parts.append("加粗")
    lines.append(f"- 章节标题: {', '.join(header_parts) if header_parts else '黑体, 14pt, 加粗'}")

    lines.append(f"- 行间距: 固定值{rules.get('line_spacing_pt', 22)}磅")
    lines.append(f"- 首行缩进: {rules.get('first_line_indent_chars', 2)}个字符")
    lines.append(f"- 段前段后间距: {rules.get('space_before', 0)}pt / {rules.get('space_after', 0)}pt")

    return "\n".join(lines)


def _generate_constraints_description(constraints: Optional[dict]) -> str:
    if not constraints:
        return "（无特殊约束，按通用学术报告风格撰写）"

    lines = []
    for category, rules in constraints.items():
        lines.append(f"### {category}")
        if isinstance(rules, dict):
            for key, value in rules.items():
                lines.append(f"- {key}: {value}")
        elif isinstance(rules, str):
            lines.append(rules)
        lines.append("")

    return "\n".join(lines)


def _generate_workflow(profile: dict, skill_name: str) -> str:
    sections = profile.get("sections", [])
    fields = profile.get("fields", [])

    section_list = "\n".join(f"   - {s['title']}" for s in sections)

    field_list = "\n".join(
        f"   - {f['key']}: 根据实际情况填写"
        for f in _deduplicate_fields(fields)
    )

    return f"""### 步骤1：理解任务
- 读取用户提供的课件/资料，理解实验/报告要求
- 提取关键信息：名称、目的、方法等
- 如果有任何不确定的信息，直接询问用户，不要自己编造

### 步骤2：准备内容
- 根据课件内容，准备各章节的文字内容
- 章节列表：
{section_list}
- 每个章节的内容必须遵守模板中的说明（见上方"各章节模板说明"）
- 内容风格应自然，避免AI感

### 步骤3：准备字段值
- 收集所有需要填写的字段：
{field_list}
- 不确定的字段值必须询问用户

### 步骤4：调用MCP工具生成文档
- 调用 generate_report 工具，传入：
  - template_path: 模板文件路径
  - output_path: 输出路径
  - profile_path: TemplateProfile JSON路径
  - field_values: 字段值字典
  - sections: 章节内容数组
- sections数组中每项的title必须与Profile中的section title完全匹配

### 步骤5：验证输出
- 调用 verify_format 工具验证格式一致性
- 检查所有字段是否正确填充
- 如果格式不一致，分析原因并修正"""


def _deduplicate_fields(fields: list) -> list:
    seen = set()
    result = []
    for f in fields:
        key = f.get("key", "")
        if key not in seen:
            result.append(f)
            seen.add(key)
    return result


def _page_size_desc(profile: dict) -> str:
    ps = profile.get("page_setup", {})
    w = ps.get("page_width_cm")
    h = ps.get("page_height_cm")
    if w and h:
        return f"{w}cm x {h}cm"
    return "未知"


def _margin_desc(profile: dict) -> str:
    ps = profile.get("page_setup", {})
    parts = []
    for key, label in [("left_margin_cm", "左"), ("right_margin_cm", "右"),
                        ("top_margin_cm", "上"), ("bottom_margin_cm", "下")]:
        if ps.get(key):
            parts.append(f"{label}{ps[key]}cm")
    return " ".join(parts) if parts else "未知"
