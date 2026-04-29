from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError


class PageSetup(BaseModel):
    page_width_cm: float
    page_height_cm: float
    left_margin_cm: float
    right_margin_cm: float
    top_margin_cm: float
    bottom_margin_cm: float

    model_config = {"extra": "forbid"}


class HeaderFooterSection(BaseModel):
    section_index: int = 0
    header_text: list[str] = Field(default_factory=list)
    footer_text: list[str] = Field(default_factory=list)
    first_page_header_text: list[str] = Field(default_factory=list)
    first_page_footer_text: list[str] = Field(default_factory=list)
    different_first_page: bool = False

    model_config = {"extra": "forbid"}


class HeaderFooter(BaseModel):
    sections: list[HeaderFooterSection] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class CoverText(BaseModel):
    text: str

    model_config = {"extra": "forbid"}


class CoverField(BaseModel):
    key: str
    label: str
    type: Literal["text_with_underline", "text"]
    default: str = ""

    model_config = {"extra": "forbid"}


class CoverPage(BaseModel):
    title: Optional[CoverText] = None
    fields: list[CoverField] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class TableField(BaseModel):
    key: str
    cell: str
    label: str
    type: Literal["table_cell"] = "table_cell"
    is_hint: bool = False
    default: str = ""
    style: dict = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class TableInfo(BaseModel):
    rows: int
    cols: int
    column_widths_cm: list[float] = Field(default_factory=list)
    fields: list[TableField] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class HeaderStyle(BaseModel):
    font_name: str
    font_size_pt: float
    bold: bool

    model_config = {"extra": "forbid"}


class BodyTextStyle(BaseModel):
    font_name: str
    font_size_pt: float

    model_config = {"extra": "forbid"}


class ContentStyle(BaseModel):
    font_name: str = ""
    font_size_pt: float = 0
    italic: bool = False
    underline: bool = False
    alignment: Literal["LEFT", "CENTER", "RIGHT", "JUSTIFY", "DISTRIBUTE", ""] = ""

    model_config = {"extra": "forbid"}


class SectionRequirement(BaseModel):
    type: Literal["min_count", "font", "table_structure", "format", "content", "forbidden", "other"]
    description: str
    value: str = ""

    model_config = {"extra": "forbid"}


class SectionInfo(BaseModel):
    title: str
    style: HeaderStyle
    content_style: Optional[ContentStyle] = None
    requirements: list[SectionRequirement] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class FormatRules(BaseModel):
    body_text: BodyTextStyle
    section_header: Optional[HeaderStyle] = None
    line_spacing_pt: float
    first_line_indent_chars: int
    space_before: float
    space_after: float
    image_width_cm: float = 0
    table_header_bg_color: str = ""

    model_config = {"extra": "forbid"}


class FieldEntry(BaseModel):
    key: str
    source: str
    label: str = ""
    type: Literal["text_with_underline", "text", "table_cell"] = "text"
    default: str = ""
    style: dict = Field(default_factory=dict)
    cell: Optional[str] = None
    is_hint: Optional[bool] = None

    model_config = {"extra": "forbid"}


class TemplateProfile(BaseModel):
    template_path: str
    page_setup: PageSetup
    header_footer: HeaderFooter = Field(default_factory=HeaderFooter)
    cover_page: CoverPage
    tables: list[TableInfo] = Field(default_factory=list)
    sections: list[SectionInfo] = Field(default_factory=list)
    format_rules: FormatRules
    annotation_patterns: list[str] = Field(default_factory=list)
    removal_patterns: list[str] = Field(default_factory=list)
    fields: list[FieldEntry] = Field(default_factory=list, description="Auto-populated from cover_page + tables, leave empty")

    model_config = {"extra": "forbid"}


def validate_profile_pydantic(data: dict) -> dict:
    try:
        profile = TemplateProfile.model_validate(data)
        return {"valid": True, "errors": [], "profile": profile.model_dump()}
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = ".".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "")
            errors.append(f"{loc}: {msg}")
        return {"valid": False, "errors": errors, "profile": None}


def _clean_section_content_styles(profile: dict):
    sections = profile.get("sections", [])
    if not isinstance(sections, list):
        return
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        cs = sec.get("content_style")
        if cs is None:
            sec.pop("content_style", None)


def fix_profile_pydantic(data: dict) -> dict:
    result = validate_profile_pydantic(data)
    if result["valid"]:
        profile = result["profile"]
    else:
        _clean_section_content_styles(data)
        profile = {
            "template_path": data.get("template_path", ""),
            "page_setup": data.get("page_setup", {}),
            "header_footer": data.get("header_footer", {}),
            "cover_page": data.get("cover_page", {}),
            "tables": data.get("tables", []),
            "sections": data.get("sections", []),
            "format_rules": data.get("format_rules", {}),
            "annotation_patterns": data.get("annotation_patterns", []),
            "removal_patterns": data.get("removal_patterns", []),
            "fields": data.get("fields", []),
        }

    _clean_section_content_styles(profile)

    all_fields = []
    seen_keys = set()
    cover_page = profile.get("cover_page", {})
    if isinstance(cover_page, dict):
        for f in cover_page.get("fields", []):
            if isinstance(f, dict) and f.get("key") and f["key"] not in seen_keys:
                all_fields.append({"source": "cover_page", **f})
                seen_keys.add(f["key"])
    tables = profile.get("tables", [])
    if isinstance(tables, list):
        for idx, t in enumerate(tables):
            if isinstance(t, dict):
                for f in t.get("fields", []):
                    if isinstance(f, dict) and f.get("key"):
                        unique = f"{f['key']}_t{idx}_{f.get('cell', '')}"
                        if unique not in seen_keys:
                            all_fields.append({"source": f"table_{idx}", **f})
                            seen_keys.add(unique)
    profile["fields"] = all_fields

    return profile
