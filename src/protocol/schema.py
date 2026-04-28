ANALYZE_TEMPLATE_SCHEMA = {
    "name": "analyze_template",
    "description": "分析Word模板文档，提取紧凑格式的原始数据(compact)和TypeScript接口定义。返回的compact数据是原始解析结果，不是TemplateProfile JSON。你必须根据compact数据和TS接口定义，自己编写TemplateProfile JSON，然后调用save_profile保存。需要传入skill_key凭据（从通用Skill文件中获取）。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "template_path": {
                "type": "string",
                "description": "Word模板文件路径（支持.doc和.docx）"
            },
            "output_path": {
                "type": "string",
                "description": "compact原始数据JSON保存路径（可选，不提供则不保存）"
            },
            "skill_key": {
                "type": "string",
                "description": "凭据（从Skill文件中获取，证明你已阅读Skill）"
            }
        },
        "required": ["template_path", "skill_key"]
    }
}

GENERATE_REPORT_SCHEMA = {
    "name": "generate_report",
    "description": "根据Word模板和TemplateProfile生成报告文档。⚠️ 必须先读取特化Skill文件（Agent框架skills/rules目录下的对应Skill），按Skill规定的工作流程调用本工具。不要跳过Skill直接调用本工具，否则可能遗漏字段、章节或格式要求。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "template_path": {
                "type": "string",
                "description": "Word模板文件路径（支持.doc和.docx）"
            },
            "output_path": {
                "type": "string",
                "description": "输出Word文档路径"
            },
            "profile_path": {
                "type": "string",
                "description": "TemplateProfile JSON文件路径"
            },
            "field_values": {
                "type": "object",
                "description": "字段值字典，key对应Profile中的field key，value为要填入的值。已知的env字段（student_id, student_name, student_class）若未提供会自动从.env填充。",
                "additionalProperties": {"type": "string"}
            },
            "sections": {
                "type": "array",
                "description": "各章节内容列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "章节标题，必须与Profile中的section title完全匹配"
                        },
                        "content": {
                            "type": "string",
                            "description": "章节内容（纯文本，支持换行符）"
                        },
                        "images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "图片路径列表（可选）"
                        },
                        "tables": {
                            "type": "array",
                            "description": "章节内表格列表（可选）",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "headers": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "表头行"
                                    },
                                    "rows": {
                                        "type": "array",
                                        "items": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "description": "数据行"
                                    }
                                },
                                "required": ["headers", "rows"]
                            }
                        }
                    },
                    "required": ["title", "content"]
                }
            },
            "result_images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "全局结果图片路径列表（可选）"
            },
            "skill_key": {
                "type": "string",
                "description": "凭据（从特化Skill文件中获取，证明你已阅读Skill）"
            }
        },
        "required": ["template_path", "output_path", "profile_path", "field_values", "sections", "skill_key"]
    }
}

GENERATE_SKILL_SCHEMA = {
    "name": "generate_skill",
    "description": "基于TemplateProfile生成特化的Skill描述文件。生成的Skill包含该模板特有的字段定义、章节结构、格式规则和约束，其他Agent可直接使用该Skill生成报告。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "profile_path": {
                "type": "string",
                "description": "TemplateProfile JSON文件路径"
            },
            "skill_name": {
                "type": "string",
                "description": "Skill名称，如'算法设计实验报告'"
            },
            "output_path": {
                "type": "string",
                "description": "Skill描述文件输出路径（.md）"
            },
            "constraints": {
                "type": "object",
                "description": "自定义约束规则（可选），如代码风格、命名规则等",
                "additionalProperties": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object", "additionalProperties": {"type": "string"}}
                    ]
                }
            },
            "skill_key": {
                "type": "string",
                "description": "凭据（从通用Skill文件中获取，证明你已阅读Skill）"
            }
        },
        "required": ["profile_path", "skill_name", "output_path", "skill_key"]
    }
}

PARSE_COURSE_SCHEMA = {
    "name": "parse_course_material",
    "description": "解析课件文件（支持pptx、docx、doc格式），提取文本内容。⚠️ 本工具仅在报告生成阶段使用，特化阶段不要调用。需要传入skill_key凭据（从特化Skill文件中获取）。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "课件文件路径（支持.pptx, .docx, .doc）"
            },
            "output_path": {
                "type": "string",
                "description": "解析结果JSON保存路径（可选）"
            },
            "skill_key": {
                "type": "string",
                "description": "凭据（从特化Skill文件中获取，证明你已阅读Skill）"
            }
        },
        "required": ["file_path", "skill_key"]
    }
}

VERIFY_FORMAT_SCHEMA = {
    "name": "verify_format",
    "description": "对比生成的Word文档与模板的格式差异，验证格式是否一致。检查页面设置、段落样式、字体、字号、加粗、斜体、下划线等。如果提供profile_path，还会检查内容是否满足requirements约束（代码辅助检查，结果仅供参考）。需要传入skill_key凭据（从特化Skill文件中获取）。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "template_path": {
                "type": "string",
                "description": "模板文件路径"
            },
            "generated_path": {
                "type": "string",
                "description": "生成的文档路径"
            },
            "profile_path": {
                "type": "string",
                "description": "TemplateProfile JSON文件路径（可选，提供后会检查requirements约束）"
            },
            "output_path": {
                "type": "string",
                "description": "验证结果JSON保存路径（可选）"
            },
            "skill_key": {
                "type": "string",
                "description": "凭据（从特化Skill文件中获取，证明你已阅读Skill）"
            }
        },
        "required": ["template_path", "generated_path", "skill_key"]
    }
}

SAVE_PROFILE_SCHEMA = {
    "name": "save_profile",
    "description": "保存TemplateProfile JSON到文件，并自动验证格式。你必须根据analyze_template返回的TypeScript接口定义编写TemplateProfile JSON，然后调用此工具保存。系统会自动验证格式并补全缺失字段。如果验证失败，会返回具体错误信息和TS接口定义供修正。⚠️ annotation_patterns和removal_patterns不能为空，必须识别模板中的注释/提示文本模式。需要传入skill_key凭据（从通用Skill文件中获取）。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "profile_json": {
                "type": "object",
                "description": "TemplateProfile JSON对象。必须严格遵循analyze_template返回的TypeScript接口定义。关键字段：template_path(string), page_setup(PageSetup), cover_page(CoverPage), format_rules(FormatRules)为必需；tables, sections, annotation_patterns, removal_patterns, fields为可选但重要。fields数组留空[]即可，系统自动从cover_page和tables汇总。"
            },
            "output_path": {
                "type": "string",
                "description": "Profile JSON保存路径"
            },
            "skill_key": {
                "type": "string",
                "description": "凭据（从通用Skill文件中获取，证明你已阅读Skill）"
            }
        },
        "required": ["profile_json", "output_path", "skill_key"]
    }
}

ALL_TOOLS = [ANALYZE_TEMPLATE_SCHEMA, GENERATE_REPORT_SCHEMA, GENERATE_SKILL_SCHEMA, PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA, SAVE_PROFILE_SCHEMA]
