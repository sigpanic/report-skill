# 📝 报告 Skill 生成器

> **你给个 Word 模板，AI 自动填好内容生成格式完全一致的报告。**  
> 不需要手动排版、不需要告诉 AI 格式规则，给模板 + 课件就行。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0%2B-8A2BE2)](https://modelcontextprotocol.io/)

---

## 它能做什么

**场景：大学生写实验报告**

你有一份 Word 实验报告模板（封面有学生姓名、学号、课程名；中间有实验目的、环境、内容、结果、总结等章节；还有评分表格），每学期要做很多份。

以前：打开模板 → 手改封面字段 → 复制粘贴实验内容 → 调整格式 → 保存 → 重复  
现在：把模板交给 AI，AI 分析模板结构，生成一个专属**Skill**。以后每次给课件，AI 自动填好内容生成报告。

**场景：公司周报/月报**

你有固定的周报模板。AI 分析一次，以后每次说"生成这周的周报"就自动填好。

---

## 核心亮点

- **一份模板，无限复用** — 分析一次模板，生成专属 Skill，后续每次只需给课件
- **格式 100% 保留** — 复制模板后逐字替换，下划线、字体、表格样式全部保留
- **不需要 AI 理解排版** — 格式由代码提取 + 注释自然语言决定，AI 只做语义理解
- **基于 MCP 标准协议** — 支持 Claude Code、Trae、Cursor 等所有主流 AI Agent
- **自动校验闭环** — Profile 格式错了 Pydantic 自动报错 + 给出修正指南

---

## 快速开始

### 1. 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置 MCP

**Claude Code** — 项目根目录 `.mcp.json`：

```json
{
  "mcpServers": {
    "report-skill-generator": {
      "command": ".venv/Scripts/python.exe",
      "args": ["src/mcp_server/server.py"],
      "cwd": "."
    }
  }
}
```

**Trae** — `.trae/mcp.json`（需要在 Trae 设置中手动打开「加载项目级 MCP」）：

```json
{
  "mcpServers": {
    "report-skill-generator": {
      "command": ".venv/Scripts/python.exe",
      "args": ["src/mcp_server/server.py"],
      "cwd": "."
    }
  }
}
```

> 其他 Agent（Cursor、Cline、Windsurf 等）配置方式类似，只需将上述 JSON 放入对应 MCP 配置文件中。具体路径请参考各 Agent 的官方 MCP 配置文档。

### 3. 开始使用

重启 Agent 后就能看到 6 个 MCP 工具。按照**两阶段工作流**操作：

**阶段一：特化**（每个模板只做一次）
1. 调用 `analyze_template` 分析模板
2. AI 根据分析结果编写 Profile
3. 调用 `save_profile` 保存并校验
4. 调用 `generate_skill` 生成特化 Skill

**阶段二：生成**（每次实验重复）
1. 调用 `parse_course_material` 解析课件（可选）
2. AI 准备内容和字段值
3. 调用 `generate_report` 生成报告
4. 调用 `verify_format` 验证格式

---

## MCP 工具一览

| 工具 | 功能 |
|------|------|
| `analyze_template` | 分析 Word 模板，提取结构 + 格式草稿 |
| `save_profile` | 保存 Profile，自动校验 + 补全字段 |
| `generate_skill` | 生成特化 Skill，自动注册到 Agent 目录 |
| `generate_report` | 按模板格式生成 Word 报告 |
| `parse_course_material` | 解析课件文字（支持 OCR） |
| `verify_format` | 验证生成文档与模板格式一致 |

---

## 工作流程详解

### 第一阶段：特化

```
你给模板 → AI 分析 → 生成 Profile → 生成 Skill → 下次直接用
```

`analyze_template` 会输出一份**紧凑数据**，包含：
- 文档的纯文本内容 + 段落分类（封面、标题、正文、注释）
- 代码自动提取的格式草稿（正文用啥字体、标题用啥字号）
- 注释中检测到的格式关键词提醒

AI 根据这些信息编写 TemplateProfile JSON，`save_profile` 自动校验格式完整性，通过后生成特化 Skill 文件。

### 第二阶段：报告生成

```
你给课件 → AI 读课件写内容 → 生成报告 → 验证格式
```

个人信息（姓名、学号、班级）由系统自动从 `.env` 文件读取填充。

---

## 项目结构

```
src/
├── mcp_server/           # MCP Server 入口 + 工具实现
├── protocol/             # Pydantic 模型 + TS 接口生成
├── template_parser/      # 模板解析 + 课件解析
├── doc_generator/        # 报告生成 + 格式验证
├── skill_generator/      # 特化 Skill 生成
└── constraints/          # 约束管理
```

---

## 配置

```env
# .env — 个人信息
STUDENT_ID=你的学号
STUDENT_NAME=你的姓名
STUDENT_CLASS=你的班级
```

```yaml
# config.yaml
naming_format: "{student_id}-{student_name}-{student_class}"
template_path: "你的模板文件名.docx"
output_base_dir: "."
```

---

## 常见问题

**格式怎么确定的？**

代码先从文档正文统计出格式草稿（最常用的字体字号作为正文字体，加粗大字号作为标题字体）。如果模板注释里写了格式要求（如"宋体小四、行间距22磅"），AI 读注释后覆盖代码的值。没写注释就用代码统计值。

**报告里的代码会被怎么处理？**

模板如果有"不需要列程序源代码"的注释，AI 会在生成报告时自动遵守这条约束，只描述算法思路不贴代码。源代码可以单独打包提交。

**支持哪些文件格式？**

| 类型 | 格式 | 说明 |
|------|------|------|
| 模板 | `.docx` | 直接处理，无需额外依赖 |
| 模板 | `.doc`（老格式） | 需要 Windows 安装 Microsoft Word，通过 COM 自动转换 |
| 课件 | `.pptx` | 直接处理，无需额外依赖 |
| 课件 | `.ppt`（老格式） | 需要 Windows 安装 Microsoft PowerPoint，通过 COM 自动转换 |
| 课件 | `.docx` / `.doc` | 同模板规则 |
| 输出 | 自动匹配输入格式 | `.docx` 模板 → `.docx` 输出，`.doc` 模板 → `.doc` 输出 |

**WPS 用户：** WPS 虽然也能打开 `.doc`/`.ppt`，但它的 COM 接口与 Microsoft Office 不完全兼容，转换大概率会失败。建议用 `.docx`/`.pptx` 格式，不需要 COM 调用，不存在兼容问题。

---

## 已知限制

- OCR 需要安装 Tesseract
- `.doc` / `.ppt`（老格式）依赖 Microsoft Office COM 接口，需要安装 Office 且仅限 Windows
- WPS 的 COM 兼容性不足，老格式建议先手动另存为 `.docx` / `.pptx`
- 文本框、艺术字等复杂 Word 元素可能无法完美保持

---

## ⚖️ 声明

本项目仅供学习 MCP 协议和 AI Agent 工作流开发参考，**不得用于任何学术不端行为**。使用本工具生成的报告内容并不代表用户的真实实验过程和结果，**用户需自行承担因使用本工具产生的全部后果**，包括但不限于：

- 学术诚信问题及相应处分
- 课程内容理解不足导致的学业影响
- 生成内容错误或格式不符导致的评分影响

**实验报告的核心价值在于记录真实实验过程和思考**，建议优先独立完成实验，本工具仅可作为格式排版辅助参考。

---

## License

MIT
