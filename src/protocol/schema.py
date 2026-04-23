ANALYZE_TEMPLATE_SCHEMA = {
    "name": "analyze_template",
    "description": "分析Word模板文档，生成TemplateProfile。TemplateProfile是模板的完整结构化描述，包含封面字段、表格字段、章节定义、格式规则等。分析结果可用于后续生成报告或生成特化Skill。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "template_path": {
                "type": "string",
                "description": "Word模板文件路径（支持.doc和.docx）"
            },
            "output_path": {
                "type": "string",
                "description": "TemplateProfile JSON保存路径（可选，不提供则不保存）"
            }
        },
        "required": ["template_path"]
    }
}

GENERATE_REPORT_SCHEMA = {
    "name": "generate_report",
    "description": "根据Word模板和TemplateProfile生成报告文档。接受模板路径、Profile、字段值和章节内容，输出格式严格符合模板的Word文档。",
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
                "description": "字段值字典，key对应Profile中的field key，value为要填入的值",
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
            }
        },
        "required": ["template_path", "output_path", "profile_path", "field_values", "sections"]
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
            }
        },
        "required": ["profile_path", "skill_name", "output_path"]
    }
}

PARSE_COURSE_SCHEMA = {
    "name": "parse_course_material",
    "description": "解析课件文件（支持pptx、docx、doc格式），提取文本内容。用于理解实验要求和课件内容。",
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
            }
        },
        "required": ["file_path"]
    }
}

VERIFY_FORMAT_SCHEMA = {
    "name": "verify_format",
    "description": "对比生成的Word文档与模板的格式差异，验证格式是否一致。检查页面设置、段落样式、字体、字号、加粗、斜体、下划线等。",
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
            "output_path": {
                "type": "string",
                "description": "验证结果JSON保存路径（可选）"
            }
        },
        "required": ["template_path", "generated_path"]
    }
}

ALL_TOOLS = [ANALYZE_TEMPLATE_SCHEMA, GENERATE_REPORT_SCHEMA, GENERATE_SKILL_SCHEMA, PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA]
