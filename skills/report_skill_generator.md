# 报告Skill生成器（通用版）

## 概述

本Skill的唯一职责是：**分析Word模板 → 生成特化Skill**。

用户提供的Word模板文档，通过LLM理解模板结构后，生成针对该模板的特化Skill。特化Skill包含了该模板的所有字段、章节、格式规则和约束，其他Agent安装特化Skill后即可生成报告。

**核心理念：Parser提取原始数据，LLM做语义理解，Skill模板填空生成。**

## 工作流程

### 步骤1：用户提供模板

- 用户提供Word模板文件（.doc或.docx）
- **此阶段不需要课件**，课件在后续使用特化Skill生成报告时才需要

### 步骤2：提取模板原始数据

- 调用 `analyze_template` MCP工具
- 工具返回：compact原始数据 + TypeScript接口定义 + 分析指导

### 步骤3：LLM分析模板结构，编写TemplateProfile JSON

- **这一步由LLM（你）完成**，不是硬编码规则
- 根据compact数据和TypeScript接口定义，编写TemplateProfile JSON
- **⚠️ TemplateProfile JSON不是compact原始数据！** 它是你根据TS接口定义(上一步操作返回的TS定义)分析编写的结构化JSON，定义了封面字段、表格字段、章节结构、格式规则等,必须严格遵守TS定义，分析模板word解析的内容，生成符合ts定义的json
- 你必须按照analyze\_template返回的TypeScript接口定义来编写
- 调用 `save_profile` 保存Profile（自动Pydantic校验+补全fields）
- 如果校验失败，根据返回的错误信息和TS接口定义修正后重试

### 步骤4：生成特化Skill

- 调用 `generate_skill` MCP工具
- 传入Profile、Skill名称、用户约束
- 约束由用户指定，不硬编码
- 生成的特化Skill会包含该模板的完整工作流程（包括读取课件、准备内容、生成报告等）

### 步骤5（可选）：顺带生成报告

- 如果用户同时要求生成一份具体报告，根据生成的特化Skill工作即可
- 特化Skill中包含了完整的报告生成工作流程

## MCP工具

### analyze\_template

分析Word模板，返回compact原始数据 + TypeScript接口定义。

- template\_path (必需): 模板文件路径（支持.doc和.docx）
- output\_path (可选): 原始数据JSON保存路径

### save\_profile

保存TemplateProfile JSON到文件，自动Pydantic校验+补全fields。

- profile\_json (必需): TemplateProfile JSON对象（按analyze\_template返回的TS接口定义编写，不是compact原始数据）
- output\_path (必需): Profile JSON保存路径

### generate\_skill

基于Profile生成特化Skill描述文件。

- profile\_path (必需): TemplateProfile JSON文件路径
- skill\_name (必需): Skill名称
- output\_path (必需): Skill文件输出路径
- constraints (可选): 用户指定的约束规则字典

## 重要原则

### 原则0：🚫 特化阶段严禁解析课件
本Skill（通用版）的工作流程**只涉及模板分析**，与任何具体的实验主题、课件、报告内容完全无关。
**绝对不要**在特化阶段调用parse_course_material或读取任何课件文件。
课件解析属于第二阶段（使用特化Skill生成报告时），不在本阶段范围内。

### 原则1：TemplateProfile JSON不是compact原始数据

compact数据是模板的原始解析结果（格式目录+引用模式），TemplateProfile JSON是你根据TS接口定义**分析编写**的结构化描述。两者完全不同。

### 原则2：annotation\_patterns和removal\_patterns需要特别注意

模板中通常包含注释/提示文本（如红色斜体文字、"删除此注释"等），必须识别并填入annotation\_patterns和removal\_patterns，否则注释不会被删除。

### 原则3：表格字段只包含值区域

表格中标签列（如"实验名称"）不是字段，只有值区域才是字段。红色/斜体的提示文本is\_hint必须设为true。

### 原则4：不确定就问用户

如果有任何不确定的信息，直接询问用户，不要自己编造。

### 原则5：格式完全对齐

生成的特化Skill必须确保报告格式与模板完全一致。

## 约束规则说明

约束规则**不是硬编码的**，由用户在调用 `generate_skill` 时通过 `constraints` 参数传入。不同用户、不同课程的约束完全不同。

## 架构设计

```
Parser(确定性) → compact数据 + TS接口定义 → LLM(语义理解) → TemplateProfile JSON → 特化Skill
```

特化Skill生成后，其他Agent即可使用它来生成报告，无需再分析模板。

## 配置

敏感信息放在 `.env` 文件中：

```
STUDENT_ID=你的学号
STUDENT_NAME=你的姓名
STUDENT_CLASS=你的班级
```

