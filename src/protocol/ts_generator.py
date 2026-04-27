from typing import get_origin, get_args, Union, Literal, Any
from pydantic import BaseModel


def _python_type_to_ts(annotation) -> str:
    origin = get_origin(annotation)

    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        has_none = type(None) in get_args(annotation)
        if len(args) == 1:
            inner = _python_type_to_ts(args[0])
        else:
            inner = " | ".join(_python_type_to_ts(a) for a in args)
        return f"{inner} | null" if has_none else inner

    if origin is Literal:
        args = get_args(annotation)
        return " | ".join(f'"{a}"' if isinstance(a, str) else str(a) for a in args)

    if origin is list:
        args = get_args(annotation)
        inner = _python_type_to_ts(args[0]) if args else "any"
        return f"{inner}[]"

    if origin is dict or annotation is dict:
        args = get_args(annotation)
        if args and len(args) == 2:
            key_ts = _python_type_to_ts(args[0])
            val_ts = _python_type_to_ts(args[1])
            return f"Record<{key_ts}, {val_ts}>"
        return "Record<string, any>"

    if annotation is str:
        return "string"
    if annotation is int:
        return "number"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is Any:
        return "any"

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation.__name__

    return "any"


def _get_default_comment(field_info) -> str:
    if field_info.is_required():
        return ""
    try:
        default = field_info.default
        if default is not None and str(default) != 'PydanticUndefined' and default is not ...:
            if isinstance(default, str):
                return f'  // default: "{default}"'
            elif isinstance(default, bool):
                return f"  // default: {str(default).lower()}"
            elif isinstance(default, (int, float)):
                return f"  // default: {default}"
            elif isinstance(default, list):
                return "  // default: []"
            elif isinstance(default, dict):
                return "  // default: {{}}"
    except Exception:
        pass
    if field_info.default_factory is not None:
        return "  // has default"
    return ""


def pydantic_model_to_ts(model_class: type[BaseModel]) -> str:
    extra = model_class.model_config.get("extra", "ignore")
    extra_note = "  // extra fields allowed" if extra == "allow" else ""
    lines = [f"interface {model_class.__name__} {{{extra_note}"]

    for field_name, field_info in model_class.model_fields.items():
        ts_type = _python_type_to_ts(field_info.annotation)
        is_opt = not field_info.is_required()
        comment = _get_default_comment(field_info)
        opt_mark = "?" if is_opt else ""
        lines.append(f"  {field_name}{opt_mark}: {ts_type};{comment}")

    lines.append("}")
    return "\n".join(lines)


def generate_all_ts_interfaces() -> str:
    from src.protocol.profile_schema import (
        PageSetup, CoverTitle, CoverCollege, CoverField, CoverPage,
        TableField, TableInfo, SectionStyle, ContentStyle, SectionRequirement, SectionInfo,
        BodyTextStyle, SectionHeaderStyle, FormatRules,
        FieldEntry, TemplateProfile
    )

    models = [
        PageSetup, CoverTitle, CoverCollege, CoverField, CoverPage,
        TableField, TableInfo, SectionStyle, ContentStyle, SectionRequirement, SectionInfo,
        BodyTextStyle, SectionHeaderStyle, FormatRules,
        FieldEntry, TemplateProfile
    ]

    interfaces = []
    for model in models:
        interfaces.append(pydantic_model_to_ts(model))

    return "\n\n".join(interfaces)
