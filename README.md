# 📝 报告.skill

> 一个模板驱动的实验报告自动生成系统。扔掉重复劳动，让AI帮你写报告。

## 它能做什么？

给你一个Word模板，它能：

1. 🔍 **自动分析模板** — 提取封面字段、表格字段、章节结构、格式规则
2. 🎯 **生成专属Skill** — 基于模板结构自动生成特化Skill描述
3. 📄 **生成格式完美的Word** — 严格保持模板格式，run级别对齐
4. 📚 **解析课件内容** — 支持PPT/Word课件，提取关键信息
5. ✅ **验证格式一致性** — 自动对比生成文档与模板的格式差异

## 快速开始

```bash
# 安装
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 运行MCP Server
.venv\Scripts\python.exe src\mcp_server\server.py
```

## 工作流程

```
模板 ──→ analyze_template ──→ TemplateProfile
                                    │
约束(可选) ────────────────→ generate_skill ──→ 特化Skill
                                    │
课件 ──→ parse_course_material ──→ 课件内容
                                    │
特化Skill + 课件 + 字段值 ──→ generate_report ──→ Word文档
                                    │
                          verify_format ──→ 格式验证
```

**两阶段使用：**

| 阶段 | 做什么 | 频率 |
|------|--------|------|
| 特化 | 分析模板 → 生成Skill | 一次 |
| 生成 | 解析课件 → 生成报告 | 每次 |

## 支持的格式

| 模板 | 课件 |
|------|------|
| .doc, .docx | .ppt, .pptx, .doc, .docx |

输出格式自动与模板一致：模板.doc → 输出.doc，模板.docx → 输出.docx

## MCP工具

| 工具 | 功能 |
|------|------|
| `analyze_template` | 分析Word模板，提取结构化描述 |
| `generate_report` | 基于模板+Profile生成报告（支持章节内插入表格） |
| `generate_skill` | 基于Profile生成特化Skill |
| `parse_course_material` | 解析课件文件（支持OCR） |
| `verify_format` | 验证格式一致性 |

## 跨Agent可用

基于MCP标准协议，任何支持MCP的Agent都能用：

| Agent | 配置方式 |
|-------|----------|
| Trae | .trae配置中添加MCP Server |
| Claude Code | claude_desktop_config.json中添加 |
| 其他MCP客户端 | 配置stdio连接 |

## 配置

编辑 `config.yaml`：

```yaml
student_id: "你的学号"
student_name: "你的姓名"
student_class: "你的班级"
naming_format: "{student_id}-{student_name}-{student_class}"
template_path: "模板文件名.doc"
```

## 项目结构

```
src/
├── template_parser/       # 模板层：解析模板+课件
├── doc_generator/         # 工作层：生成Word+格式验证
├── skill_generator/       # Skill生成器
├── protocol/              # 协议层：MCP工具Schema
├── constraints/           # 约束层：规则管理
└── mcp_server/            # MCP Server入口
```

## 不确定就问用户

系统遵循一个原则：**不确定的信息直接问用户，不编造**。

- 不知道学号姓名？问用户
- 课件图片有文字？提示用户提供
- 不确定实验要求？问用户

## License

MIT
