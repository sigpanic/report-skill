from typing import Optional, Literal
from pydantic import BaseModel, Field


class PageSetup(BaseModel):
    page_width_cm: float
    page_height_cm: float
    left_margin_cm: float
    right_margin_cm: float
    top_margin_cm: float
    bottom_margin_cm: float

    model_config = {"extra": "forbid"}


class CoverTitle(BaseModel):
    text: str
    style: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class CoverCollege(BaseModel):
    text: str
    style: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class CoverField(BaseModel):
    key: str
    label: str
    type: Literal["text_with_underline", "text"]
    default: str = ""
    style: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class CoverPage(BaseModel):
    title: Optional[CoverTitle] = None
    fields: list[CoverField] = Field(default_factory=list)
    college: Optional[CoverCollege] = None

    model_config = {"extra": "allow"}


class TableField(BaseModel):
    key: str
    cell: str
    label: str
    type: Literal["table_cell"] = "table_cell"
    is_hint: bool = False
    style: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class TableInfo(BaseModel):
    index: int
    rows: int
    cols: int
    column_widths_cm: list[float] = Field(default_factory=list)
    fields: list[TableField] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class SectionStyle(BaseModel):
    font_name: str
    font_size_pt: float
    bold: bool

    model_config = {"extra": "allow"}


class SectionInfo(BaseModel):
    title: str
    style: SectionStyle
    note: str = ""

    model_config = {"extra": "allow"}


class BodyTextStyle(BaseModel):
    font_name: str
    font_size_pt: float

    model_config = {"extra": "allow"}


class SectionHeaderStyle(BaseModel):
    font_name: str
    font_size_pt: float
    bold: bool

    model_config = {"extra": "allow"}


class FormatRules(BaseModel):
    body_text: BodyTextStyle
    section_header: SectionHeaderStyle
    line_spacing_pt: int
    first_line_indent_chars: int
    space_before: int
    space_after: int

    model_config = {"extra": "allow"}


class FieldEntry(BaseModel):
    key: str
    source: str
    label: str = ""
    type: str = ""
    default: str = ""
    style: dict = Field(default_factory=dict)
    cell: Optional[str] = None
    is_hint: Optional[bool] = None

    model_config = {"extra": "allow"}


class TemplateProfile(BaseModel):
    template_path: str
    page_setup: PageSetup
    cover_page: CoverPage
    tables: list[TableInfo] = Field(default_factory=list)
    sections: list[SectionInfo] = Field(default_factory=list)
    format_rules: FormatRules
    annotation_patterns: list[str] = Field(default_factory=list)
    removal_patterns: list[str] = Field(default_factory=list)
    fields: list[FieldEntry] = Field(default_factory=list)

    model_config = {"extra": "allow"}


def validate_profile_pydantic(data: dict) -> dict:
    try:
        profile = TemplateProfile.model_validate(data)
        return {"valid": True, "errors": [], "profile": profile.model_dump()}
    except Exception as e:
        errors = []
        if hasattr(e, 'errors'):
            for err in e.errors():
                loc = ".".join(str(l) for l in err.get("loc", []))
                msg = err.get("msg", "")
                errors.append(f"{loc}: {msg}")
        else:
            errors.append(str(e))
        return {"valid": False, "errors": errors, "profile": None}


def fix_profile_pydantic(data: dict) -> dict:
    result = validate_profile_pydantic(data)
    if result["valid"]:
        profile = result["profile"]
    else:
        profile = TemplateProfile(
            template_path=data.get("template_path", ""),
            page_setup=data.get("page_setup", {}),
            format_rules=data.get("format_rules", {}),
        ).model_dump()
        for key in ["cover_page", "tables", "sections",
                     "annotation_patterns", "removal_patterns"]:
            if key in data:
                profile[key] = data[key]

    if not profile.get("fields"):
        all_fields = []
        seen_keys = set()
        for f in profile.get("cover_page", {}).get("fields", []):
            if isinstance(f, dict) and f.get("key") and f["key"] not in seen_keys:
                all_fields.append({"source": "cover_page", **f})
                seen_keys.add(f["key"])
        for t in profile.get("tables", []):
            if isinstance(t, dict):
                for f in t.get("fields", []):
                    if isinstance(f, dict) and f.get("key"):
                        unique = f"{f['key']}_t{t.get('index', 0)}_{f.get('cell', '')}"
                        if unique not in seen_keys:
                            all_fields.append({"source": f"table_{t.get('index', 0)}", **f})
                            seen_keys.add(unique)
        profile["fields"] = all_fields

    return profile
