import os
import json
from typing import Optional


SKILL_TEMPLATE = """---
name: "{skill_name}"
description: "Generate '{template_name}' Word documents following template format strictly. Invoke when user wants to create this type of report."
---

# {skill_name}

生成「{template_name}」Word文档，严格遵循模板格式。
Profile JSON已就绪，本Skill指导你完成报告生成。

## 模板信息
- 模板文件: `{template_filename}`
- 纸张大小: {page_size}
- 页边距: {margins}

## 自动删除规则

{delete_rules}

## 字段定义

{fields_section}

## 章节结构

{sections_section}

## 格式规则

{format_section}

## 约束规则

{constraints_section}

## 工作流程

{workflow_section}

## MCP工具

### parse_course_material
解析课件文件（pptx/ppt/docx/doc），提取文本内容。
- file_path（必需）: 课件文件路径
- output_path（可选）: 解析结果保存路径（默认保存在课件所在目录）

### generate_report
生成报告Word文档（输出格式自动与模板一致）。
- template_path（必需）: 模板文件路径
- output_path（必需）: 输出文件路径（保存到实验子目录）
- profile_path（必需）: TemplateProfile JSON文件路径
- field_values（必需）: 字段值字典
- sections（必需）: 章节内容数组，每项含title和content
- result_images（可选）: 结果截图路径列表

### verify_format
对比生成的Word文档与模板的格式差异。
- template_path（必需）: 模板文件路径
- generated_path（必需）: 生成的文档路径

## 关键注意事项
- 生成的Word文档格式必须与模板完全一致——最高优先级
- 所有注释段落会被自动删除（根据annotation_patterns/removal_patterns）
- 章节内容按Profile中的格式规则排版
- 图片居中插入，宽度12cm
- 如果有任何不确定的信息，直接询问用户，不要自己编造
- 模板中的注释和说明必须遵守
- 输出文件后缀由工具自动保证（.doc模板→.doc输出，.docx→.docx）
- 读取.env文件获取个人信息（STUDENT_ID, STUDENT_NAME, STUDENT_CLASS）
"""


def generate_skill(
    profile: dict,
    skill_name: str,
    output_path: str,
    constraints: Optional[dict] = None
) -> str:
    template_name = _infer_template_name(profile)
    template_filename = os.path.basename(profile.get('template_path', ''))
    page_size = _page_size_desc(profile)
    margins = _margin_desc(profile)
    delete_rules = _generate_delete_rules(profile)
    fields_section = _generate_fields_description(profile)
    sections_section = _generate_sections_description(profile)
    format_section = _generate_format_description(profile)
    constraints_section = _generate_constraints_description(constraints)
    workflow_section = _generate_workflow(profile, skill_name)

    skill_content = SKILL_TEMPLATE.format(
        skill_name=skill_name,
        template_name=template_name,
        template_filename=template_filename,
        page_size=page_size,
        margins=margins,
        delete_rules=delete_rules,
        fields_section=fields_section,
        sections_section=sections_section,
        format_section=format_section,
        constraints_section=constraints_section,
        workflow_section=workflow_section,
    )

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
        label = field.get("label", "")
        if "课程" in label or "course" in label.lower():
            return field.get("default", "") + "报告"

    return "文档报告"


def _generate_delete_rules(profile: dict) -> str:
    lines = []
    annotation_patterns = profile.get("annotation_patterns", [])
    removal_patterns = profile.get("removal_patterns", [])

    if annotation_patterns or removal_patterns:
        for p in annotation_patterns:
            lines.append(f"- 包含「{p}」的段落将被自动删除")
        for p in removal_patterns:
            lines.append(f"- 匹配「{p}」的段落将被自动删除")
    else:
        lines.append("- ⚠️ 未检测到自动删除规则！如果模板中有注释/提示文本（红色/斜体），请手动补充annotation_patterns")
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
    for sec in sections:
        style = sec.get("style", {})
        style_parts = []
        if style.get("font_name"):
            style_parts.append(style["font_name"])
        if style.get("font_size_pt"):
            style_parts.append(f"{style['font_size_pt']}pt")
        if style.get("bold"):
            style_parts.append("加粗")
        style_str = ", ".join(style_parts) if style_parts else "默认"

        note = sec.get("note", "")
        if note:
            lines.append(f"- **{sec['title']}** (样式: {style_str})")
            lines.append(f"  - 要求: {note}")
        else:
            lines.append(f"- **{sec['title']}** (样式: {style_str})")

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

    return f"""### 步骤1：获取用户信息
- 读取项目根目录的`.env`文件获取个人信息（STUDENT_ID, STUDENT_NAME, STUDENT_CLASS等）
- 如果.env中存在对应信息，直接使用，不需要询问用户
- .env中不存在的字段值才需要询问用户

### 步骤2：创建实验目录
- 在类别目录下创建本次实验的子目录（英文简写命名，如maxsum/、sort/、graph/）
- 课件文件放入实验子目录
- 生成的报告和源代码也输出到实验子目录

### 步骤3：读取课件（如有）
- 如果用户提供了课件文件，调用`parse_course_material`解析课件
- 解析结果默认保存在课件所在目录
- 根据课件内容理解报告要求
- 如果没有课件，根据用户描述理解要求

### 步骤4：准备内容
- 根据课件/资料内容，准备各章节的文字内容
- 章节列表：
{section_list}
- 每个章节的内容必须遵守上方"各章节要求"中的说明
- 内容风格应自然，避免AI感

### 步骤5：准备字段值
- 收集所有需要填写的字段：
{field_list}
- 优先使用.env中的信息
- 不确定的字段值必须询问用户

### 步骤6：调用MCP工具生成文档
- 调用 generate_report 工具，传入：
  - template_path: 模板文件路径
  - output_path: 输出路径（保存到实验子目录，后缀由工具自动处理）
  - profile_path: TemplateProfile JSON路径
  - field_values: 字段值字典
  - sections: 章节内容数组
- sections数组中每项的title必须与Profile中的section title完全匹配

### 步骤7：验证输出
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
