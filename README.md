# 📝 报告 Skill 生成器

> **让 AI Agent 根据 Word 模板自动生成格式完全一致的 Word 文档。**  
> 你只需要提供一份模板和课件，AI 就能按模板要求填写封面、表格、章节，生成排版完美的报告。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0%2B-8A2BE2)](https://modelcontextprotocol.io/)
[![Cross-Agent](https://img.shields.io/badge/Agent-Trae%20%7C%20Claude%20%7C%20Cursor-green)](#跨agent支持)

***

## 💡 一句话理解

**扔给 AI 一个 Word 模板 + 课件 → AI 自动按模板格式生成报告。**

不需要你告诉 AI 怎么排版、怎么写表格、怎么保持格式，你只需要提供模板，它就能理解模板的结构要求并严格按照模板生成。

## ✨ 核心亮点

- **🔥 一份模板，无限复用** — 分析一次模板，生成专属 Skill，后续每次只需提供课件，Agent 自动生成报告
- **🎯 run 级格式保真** — 复制模板后修改，下划线、字体、单元格样式逐 run 替换，格式与模板完全一致
- **🔐 Skill 密钥认证** — 强制 Agent 必须先阅读 Skill 文件才能调用工具，杜绝跳过步骤导致的内容错误
- **🌐 基于 MCP 标准协议** — 零门槛接入 Trae、Claude Code、Cursor 等主流 Agent，无需手动启动服务
- **🔄 Pydantic 校验闭环** — Profile JSON 校验失败自动返回错误 + TS 接口定义，Agent 可自行修正
- **📐 单一真相源** — TypeScript 接口从 Pydantic 模型自动生成，绝不会出现定义不一致

***

## 🚀 它能做什么

1. **🔍 分析模板** — 解析任意 `.doc` / `.docx` 模板，提取封面字段、表格字段、章节结构、格式规则
2. **🎯 生成专属 Skill** — 基于模板结构生成特化 Skill 文件，编码完整的字段定义、工作流程和约束
3. **📄 生成格式完美的报告** — run 级替换，严格保持模板格式（下划线、字体、缩进、行距全部保留）
4. **📚 解析课件** — 支持 `.pptx` / `.ppt` / `.docx` / `.doc` 课件，提取文本内容（支持 OCR）
5. **✅ 验证格式一致性** — 自动生成后对比模板，检查页面设置、段落样式、字体字号等是否一致

***

## 📦 快速开始

### 1. 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置 MCP（以 Trae 为例）

在项目的 `.trae/mcp.json` 中添加(需要去设置中手动打开加载项目级MCP，并手动从设置启动本MCP工具)：

```json
{
  "mcpServers": {
    "report-skill-generator": {
      "command": "python",
      "args": ["src/mcp_server/server.py"],
      "env": {}
    }
  }
}
```

**无需手动启动服务！** Trae 会在需要时自动连接 MCP Server。Claude Code、Cursor 等其他 Agent 同理，只需在对应配置文件中添加 stdio 连接。

### 3. 开始使用

重启 Agent 后即可看到 6 个 MCP 工具，按照**两阶段工作流**操作即可。

***

## 🔧 两阶段工作流

### 第一阶段：特化（每个模板只需一次）

| 步骤 | 操作                                | 工具                 |
| -- | --------------------------------- | ------------------ |
| 1  | 分析 Word 模板                        | `analyze_template` |
| 2  | 根据 TS 接口定义编写 TemplateProfile JSON | —                  |
| 3  | 保存并校验 Profile                     | `save_profile`     |
| 4  | 生成特化 Skill                        | `generate_skill`   |

**产出：** 一个特化的 Skill 文件，后续所有报告生成都基于此 Skill。

### 第二阶段：报告生成（每次实验重复）

| 步骤 | 操作         | 工具                      |
| -- | ---------- | ----------------------- |
| 1  | 解析课件（如有）   | `parse_course_material` |
| 2  | 准备章节内容和字段值 | —                       |
| 3  | 生成报告文档     | `generate_report`       |
| 4  | 验证格式一致性    | `verify_format`         |

**产出：** 格式完美的 Word 报告文件。

***

## 🤖 MCP 工具一览

| 工具                      | 功能                               | 关键参数                                                                                    |
| ----------------------- | -------------------------------- | --------------------------------------------------------------------------------------- |
| `analyze_template`      | 分析模板，生成 compact 数据 + TS 接口       | `template_path`, `skill_key`                                                            |
| `save_profile`          | 保存 Profile，自动 Pydantic 校验 + 补全字段 | `profile_json`, `output_path`, `skill_key`                                              |
| `generate_skill`        | 生成特化 Skill，自动注册到 Agent 目录        | `profile_path`, `skill_name`, `output_path`, `skill_key`                                |
| `generate_report`       | 生成格式完美的 Word 报告                  | `template_path`, `output_path`, `profile_path`, `field_values`, `sections`, `skill_key` |
| `parse_course_material` | 解析课件（支持 OCR）                     | `file_path`, `skill_key`                                                                |
| `verify_format`         | 验证生成文档与模板的格式一致性                  | `template_path`, `generated_path`, `skill_key`                                          |

### 关于 Skill 密钥

每个工具都要求传入 `skill_key` 参数。密钥被拆分为两部分分布在 Skill 文件中，强制 Agent 必须**完整阅读 Skill** 才能获取密钥。这确保了 Agent 不会跳过工作流程直接调用工具。

***

## 🌐 跨 Agent 支持

基于 **MCP（Model Context Protocol）** 标准协议，支持所有 MCP 客户端：

| Agent           | 配置方式                                       |
| --------------- | ------------------------------------------ |
| **Trae**        | `.trae/mcp.json` 添加 stdio 配置               |
| **Claude Code** | `claude_desktop_config.json` 添加 MCP Server |
| **Cursor**      | 配置 MCP stdio 连接                            |
| **其他 MCP 客户端**  | 通过 stdio 连接即可                              |

**特化 Skill 自动注册** — `generate_skill` 会自动检测 `.trae/skills/`、`.claude/skills/`、`.cursor/skills/` 等目录并复制 Skill 文件，无需手动操作。

***

## 📁 项目结构

```
src/
├── mcp_server/          # MCP Server 入口 + 工具实现
├── protocol/            # 协议层：MCP Schema + Pydantic 模型 + TS 接口生成
├── template_parser/     # 模板解析 + 课件解析
├── doc_generator/       # Word 报告生成 + 格式验证
├── skill_generator/     # 特化 Skill 生成
└── constraints/         # 约束管理（用户定义，永不硬编码）
```

***

## 📋 支持的格式

| 类型 | 格式                               |
| -- | -------------------------------- |
| 模板 | `.doc`, `.docx`                  |
| 课件 | `.pptx`, `.ppt`, `.docx`, `.doc` |
| 输出 | 自动匹配模板格式（`.doc` 模板 → `.doc` 输出）  |

***

## ⚙️ 配置

**个人信息** 放在 `.env` 文件：

```env
STUDENT_ID=你的学号
STUDENT_NAME=你的姓名
STUDENT_CLASS=你的班级
```

**项目设置** 在 `config.yaml`：

```yaml
naming_format: "{student_id}-{student_name}-{student_class}"
template_path: "你的模板文件名.docx"
output_base_dir: "."
```

***

## ⚠️ 已知限制

- OCR 依赖 Tesseract（需用户自行安装）
- 复杂的 Word 元素（文本框、艺术字）可能无法完美保持
- 合并单元格检测依赖 python-docx 实现，可能存在边界情况
- `.doc` 格式转换需要 Windows COM 接口（Word 应用）
- 格式验证器按段落索引对比，内容增删后可能导致偏移
- 章节标题匹配要求精确字符串匹配

***---

## ⚖️ 免责声明

本项目仅供学习 MCP 协议和 AI Agent 工作流开发参考，**不得用于任何学术不端行为**。使用本工具生成的报告内容并不代表用户的真实实验过程和结果，**用户需自行承担因使用本工具产生的全部后果**，包括但不限于：

- 学术诚信问题及相应处分
- 课程内容理解不足导致的学业影响
- 生成内容错误或格式不符导致的评分影响

**实验报告的核心价值在于记录真实实验过程和思考**，建议优先独立完成实验，本工具仅可作为格式排版辅助参考。

---

## 📄 License

MIT
