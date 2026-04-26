GENERAL_KEY = "RPT-GEN-2026-QX7M"

AGENT_FRAMEWORKS = [
    {
        "dir": ".trae",
        "subdir": "skills",
        "ext": ".md",
        "filename": "SKILL.md",
        "frontmatter_type": "trae",
        "nested": True,
    },
    {
        "dir": ".claude",
        "subdir": "commands",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "claude",
        "nested": False,
    },
    {
        "dir": ".cursor",
        "subdir": "rules",
        "ext": ".mdc",
        "filename": None,
        "frontmatter_type": "cursor",
        "nested": False,
    },
    {
        "dir": ".cline",
        "subdir": "rules",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "plain",
        "nested": False,
    },
    {
        "dir": ".windsurf",
        "subdir": "",
        "ext": "",
        "filename": ".windsurfrules",
        "frontmatter_type": "plain",
        "nested": False,
        "single_file": True,
    },
    {
        "dir": ".roo",
        "subdir": "rules",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "plain",
        "nested": False,
    },
    {
        "dir": ".aider",
        "subdir": "conventions",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "plain",
        "nested": False,
    },
    {
        "dir": ".continue",
        "subdir": "rules",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "plain",
        "nested": False,
    },
    {
        "dir": ".augment",
        "subdir": "rules",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "plain",
        "nested": False,
    },
    {
        "dir": ".kiro",
        "subdir": "specs",
        "ext": ".md",
        "filename": None,
        "frontmatter_type": "plain",
        "nested": False,
    },
]

KEY_ERROR_GENERAL = "❌ 凭据无效。请完整阅读report-skill-generator Skill文件，找到文件中的凭据（分为两部分，需拼接），然后传入skill_key参数。不阅读Skill文件将无法使用任何工具。"
KEY_ERROR_SPECIALIZED = "❌ 凭据无效。请完整阅读特化Skill文件，找到文件中的凭据（分为两部分，需拼接），然后传入skill_key参数。不阅读Skill文件将无法使用任何工具。"
