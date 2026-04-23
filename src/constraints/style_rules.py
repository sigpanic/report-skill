from typing import Optional


def get_style_rules(constraints: Optional[dict] = None) -> dict:
    if constraints:
        return constraints
    return {}


def get_style_rules_text(constraints: Optional[dict] = None) -> str:
    if not constraints:
        return "（无特殊约束，按通用学术报告风格撰写）"

    lines = ["# 约束规则\n"]
    for category, rules in constraints.items():
        lines.append(f"## {category}")
        if isinstance(rules, dict):
            for key, value in rules.items():
                lines.append(f"- {key}: {value}")
        elif isinstance(rules, str):
            lines.append(rules)
        lines.append("")
    return "\n".join(lines)
