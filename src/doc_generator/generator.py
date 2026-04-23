import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from docx.text.paragraph import Paragraph

from src.template_parser.parser import doc_to_docx


def generate_report(
    template_path: str,
    output_path: str,
    profile: dict,
    field_values: dict,
    sections: list,
    result_images: Optional[list] = None
) -> str:
    path = Path(template_path)
    work_docx = None
    template_is_doc = path.suffix.lower() == '.doc'

    if template_is_doc:
        converted = doc_to_docx(template_path)
        if converted:
            work_docx = converted
        else:
            raise ValueError(f"无法转换.doc文件: {template_path}")
    else:
        tmp_dir = tempfile.mkdtemp()
        work_docx = os.path.join(tmp_dir, "template_copy.docx")
        shutil.copy2(template_path, work_docx)

    doc = Document(work_docx)

    _fill_cover_fields(doc, profile, field_values)
    _fill_table_fields(doc, profile, field_values)
    _fill_sections(doc, profile, sections)
    _remove_annotations(doc, profile)

    out_path = Path(output_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    docx_output = output_path
    doc.save(docx_output)

    if template_is_doc and out_path.suffix.lower() == '.doc':
        doc_to_save = _docx_to_doc(docx_output, output_path)
        if doc_to_save:
            try:
                os.remove(docx_output)
            except:
                pass
            return doc_to_save
        return docx_output

    return docx_output


def _docx_to_doc(docx_path: str, doc_output_path: str) -> Optional[str]:
    """使用COM将docx转回doc格式"""
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(docx_path))
        doc.SaveAs2(os.path.abspath(doc_output_path), FileFormat=0)
        doc.Close()
        word.Quit()
        return doc_output_path
    except Exception as e:
        print(f"docx转doc失败: {e}")
        return None


def _fill_cover_fields(doc, profile: dict, field_values: dict):
    cover = profile.get("cover_page", {})

    for para in doc.paragraphs:
        text = para.text.strip()

        for field in cover.get("fields", []):
            label = field.get("label", "")
            key = field.get("key", "")
            value = field_values.get(key, field.get("default", ""))

            if not value:
                continue

            if text.startswith(label) or _fuzzy_match_label(text, label):
                _replace_cover_field_run_level(para, label, value, field)
                break


def _fuzzy_match_label(text: str, label: str) -> bool:
    text_clean = re.sub(r'\s+', '', text)
    label_clean = re.sub(r'\s+', '', label)
    return text_clean.startswith(label_clean)


def _replace_cover_field_run_level(para, label: str, value: str, field: dict):
    """
    Run级别精确替换封面字段值，保持原始格式。
    
    模板中的典型结构：
    Run[0]: "实验课程：" (无下划线) - 标签
    Run[1]: " " (下划线) - 值开始
    Run[2]: "  " (下划线) - 值区域
    Run[3]: "算法设计与分析" (下划线) - 实际值
    Run[4]: "   " (下划线) - 填充空格
    
    策略：保留标签run不变，在值区域runs中替换值，保持下划线格式。
    """
    if not para.runs:
        return

    label_runs = []
    value_runs = []
    found_label_end = False

    for run in para.runs:
        if not found_label_end:
            label_runs.append(run)
            if label.rstrip("：:") in run.text or run.text.rstrip().endswith("：") or run.text.rstrip().endswith(":"):
                found_label_end = True
        else:
            value_runs.append(run)

    if not value_runs:
        label_text = "".join(r.text for r in label_runs)
        clean_label = label_text.rstrip("：: ").rstrip()
        for run in label_runs:
            run_text_clean = run.text.rstrip("：: ").rstrip()
            if run_text_clean == clean_label or clean_label.endswith(run_text_clean):
                found_label_end = True
                continue
            if found_label_end:
                value_runs.append(run)

    if not value_runs:
        _replace_para_simple(para, label, value, field)
        return

    total_value_len = sum(len(r.text) for r in value_runs)
    original_value = "".join(r.text for r in value_runs)
    original_value_stripped = original_value.strip()

    new_value = value
    padding_needed = max(0, total_value_len - len(new_value))
    padded_value = new_value + " " * padding_needed

    if len(padded_value) <= 0:
        for run in value_runs:
            run.text = ""
        return

    char_idx = 0
    for i, run in enumerate(value_runs):
        run_len = len(run.text)
        if i < len(value_runs) - 1:
            run.text = padded_value[char_idx:char_idx + run_len]
            char_idx += run_len
        else:
            run.text = padded_value[char_idx:]
            if len(run.text) < len(new_value) and char_idx < len(new_value):
                run.text = new_value[char_idx:]


def _replace_para_simple(para, label: str, value: str, field: dict):
    """简单替换（fallback）"""
    has_underline = field.get("type") == "text_with_underline" or any(
        r.font.underline for r in para.runs
    )

    for run in para.runs:
        run.text = ""

    para.runs[0].text = label + value
    if has_underline:
        para.runs[0].font.underline = True


def _fill_table_fields(doc, profile: dict, field_values: dict):
    tables_profile = profile.get("tables", [])

    for table_idx, table in enumerate(doc.tables):
        if table_idx >= len(tables_profile):
            break

        table_profile = tables_profile[table_idx]

        for field in table_profile.get("fields", []):
            key = field.get("key", "")
            value = field_values.get(key, "")

            if not value:
                continue

            cell_pos = field.get("cell", "").split(",")
            if len(cell_pos) != 2:
                continue

            row, col = int(cell_pos[0]), int(cell_pos[1])

            try:
                cell = table.cell(row, col)
                _fill_cell_preserving_style(cell, value, field)
            except Exception:
                pass


def _fill_cell_preserving_style(cell, value: str, field: dict):
    """填充表格单元格，保持原有run格式"""
    if not cell.paragraphs:
        return

    p = cell.paragraphs[0]

    if p.runs:
        hint_runs = [r for r in p.runs if r.font.italic or _is_hint_run(r)]
        if hint_runs:
            for r in hint_runs:
                r.text = ""
            hint_runs[0].text = value
            hint_runs[0].font.italic = False
            for attr in ['font_color', 'color']:
                try:
                    hint_runs[0].font.color.rgb = None
                except:
                    pass
            return

        for r in p.runs:
            r.text = ""
        p.runs[0].text = value
    else:
        run = p.add_run(value)
        style = field.get("style", {})
        font_name = style.get("font_name", "宋体")
        font_size = style.get("font_size_pt", 14)
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
        run.font.size = Pt(font_size)
        run.font.bold = True

    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _is_hint_run(run) -> bool:
    """判断是否是提示性run（需要被替换的）"""
    try:
        if run.font.color and run.font.color.rgb:
            rgb = str(run.font.color.rgb).upper()
            if rgb in ["FF0000", "CC0000", "FF3333"]:
                return True
    except:
        pass
    return False


def _fill_sections(doc, profile: dict, sections: list):
    format_rules = profile.get("format_rules", {})
    section_titles = {}
    for sec in sections:
        section_titles[sec["title"]] = sec

    for para in doc.paragraphs:
        text = para.text.strip()
        if text in section_titles:
            sec = section_titles[text]
            _insert_section_content(para, sec.get("content", ""), sec.get("images", []), sec.get("tables", []), format_rules)


def _insert_section_content(title_para, content: str, images: list, content_tables: list, format_rules: dict):
    body_style = format_rules.get("body_text", {})
    font_name = body_style.get("font_name", "宋体")
    font_size_pt = body_style.get("font_size_pt", 12)
    line_spacing_pt = format_rules.get("line_spacing_pt", 22)
    indent_chars = format_rules.get("first_line_indent_chars", 2)
    indent_cm = indent_chars * 0.42

    insert_after = title_para._element

    if content:
        content_lines = content.split('\n')
        for line in content_lines:
            new_para_xml = parse_xml(
                f'<w:p {nsdecls("w")}>'
                f'<w:pPr>'
                f'<w:rPr><w:rFonts w:eastAsia="{font_name}"/><w:sz w:val="{int(font_size_pt * 2)}"/></w:rPr>'
                f'</w:pPr>'
                f'</w:p>'
            )
            insert_after.addnext(new_para_xml)
            insert_after = new_para_xml

            new_p = Paragraph(new_para_xml, title_para._element.getparent())

            if line.strip():
                run = new_p.add_run(line)
                run.font.name = font_name
                run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
                run.font.size = Pt(font_size_pt)

                pf = new_p.paragraph_format
                pf.first_line_indent = Cm(indent_cm)
                pf.line_spacing = Pt(line_spacing_pt)
                pf.space_before = Pt(0)
                pf.space_after = Pt(0)

    if content_tables:
        for table_data in content_tables:
            tbl_element = _create_table_element(table_data, font_name, font_size_pt)
            insert_after.addnext(tbl_element)
            insert_after = tbl_element

    if images:
        for img_path in images:
            if os.path.exists(img_path):
                img_para_xml = parse_xml(
                    f'<w:p {nsdecls("w")}><w:pPr><w:jc w:val="center"/></w:pPr></w:p>'
                )
                insert_after.addnext(img_para_xml)
                insert_after = img_para_xml

                img_para = Paragraph(img_para_xml, title_para._element.getparent())
                run = img_para.add_run()
                run.add_picture(img_path, width=Cm(12))


def _remove_annotations(doc, profile: dict):
    annotation_patterns = profile.get("annotation_patterns", [])
    removal_patterns = profile.get("removal_patterns", [])

    paras_to_remove = []
    for para in doc.paragraphs:
        text = para.text.strip()

        should_remove = False
        for pattern in annotation_patterns:
            if pattern in text:
                should_remove = True
                break

        if not should_remove:
            for pattern in removal_patterns:
                try:
                    if re.search(pattern, text):
                        should_remove = True
                        break
                except re.error:
                    if pattern in text:
                        should_remove = True
                        break

        if should_remove:
            paras_to_remove.append(para)

    for para in paras_to_remove:
        p_element = para._element
        p_element.getparent().remove(p_element)


def _create_table_element(table_data: dict, font_name: str, font_size_pt: float):
    """
    创建Word表格的XML元素。
    table_data格式: {"headers": ["列1", "列2"], "rows": [["值1", "值2"], ...]}
    """
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    num_cols = len(headers) if headers else (len(rows[0]) if rows else 0)

    if num_cols == 0:
        return parse_xml(f'<w:p {nsdecls("w")}></w:p>')

    ns = nsdecls("w")
    sz = int(font_size_pt * 2)

    tbl_xml = f'<w:tbl {ns}>'
    tbl_xml += f'<w:tblPr><w:tblBorders>'
    tbl_xml += f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    tbl_xml += f'<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    tbl_xml += f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    tbl_xml += f'<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    tbl_xml += f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    tbl_xml += f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    tbl_xml += f'</w:tblBorders><w:jc w:val="center"/></w:tblPr>'

    if headers:
        tbl_xml += '<w:tr>'
        for h in headers:
            h_escaped = h.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            tbl_xml += f'<w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="D9E2F3"/></w:tcPr>'
            tbl_xml += f'<w:p><w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:eastAsia="{font_name}"/><w:sz w:val="{sz}"/><w:b/></w:rPr></w:pPr>'
            tbl_xml += f'<w:r><w:rPr><w:rFonts w:eastAsia="{font_name}"/><w:sz w:val="{sz}"/><w:b/></w:rPr><w:t>{h_escaped}</w:t></w:r>'
            tbl_xml += f'</w:p></w:tc>'
        tbl_xml += '</w:tr>'

    for row in rows:
        tbl_xml += '<w:tr>'
        for cell in row:
            cell_escaped = str(cell).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            tbl_xml += f'<w:tc><w:p><w:pPr><w:jc w:val="center"/><w:rPr><w:rFonts w:eastAsia="{font_name}"/><w:sz w:val="{sz}"/></w:rPr></w:pPr>'
            tbl_xml += f'<w:r><w:rPr><w:rFonts w:eastAsia="{font_name}"/><w:sz w:val="{sz}"/></w:rPr><w:t>{cell_escaped}</w:t></w:r>'
            tbl_xml += f'</w:p></w:tc>'
        tbl_xml += '</w:tr>'

    tbl_xml += '</w:tbl>'
    return parse_xml(tbl_xml)
