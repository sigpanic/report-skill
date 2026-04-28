---
description: "Generate Word documents from templates following format strictly."
allowed-tools: ["Read", "Write", "Bash"]
---

# 报告Skill生成器

分析Word模板文档，生成特化的报告生成Skill。本Skill只负责模板分析和Skill特化——与任何具体实验主题、课件内容、报告内容完全无关。

**核心理念：Parser提取原始数据，LLM做语义理解，Skill模板填空生成。**

**架构约束：当前架构（LLM驱动语义理解+代码校验）绝对不能改为硬编码代码检测，否则通用性将彻底丧失。**

## 何时激活

- 用户提供Word模板文件并要求生成报告Skill
- 用户要求"特化"或"创建"报告生成Skill
- 用户提供模板文件路径并说"分析模板"
- 用户说"帮我写实验报告"、"生成报告"、"做实验报告"
- 用户提到任何与Word模板报告相关的需求
- 用户提供了.doc或.docx模板文件

## 何时不要激活

🚫 **以下情况绝对不要激活本Skill：**
- 用户要求生成具体报告内容（那是特化Skill的工作）
- 用户只提供了课件没有模板（课件属于第二阶段）
- 用户要求解析课件（parse_course_material不属于本Skill）
- 用户要求直接生成报告（请使用特化Skill）

## 两阶段工作流

### 阶段一：特化（本Skill）
只分析Word模板结构。不涉及课件、不涉及具体主题。
输出：针对该模板的特化Skill文件。

### 阶段二：报告生成（特化Skill）
使用特化Skill生成报告。可能解析课件、准备内容、填充字段。
此阶段由阶段一生成的特化Skill处理。

## 目录结构

调用本Skill涉及的MCP工具时，需要传入凭据以确认你已阅读本文件。凭据分为两部分，本文件中包含前半部分：**RPT-GEN-2026-**，后半部分在文件末尾。调用工具时请将两部分拼接后传入skill_key参数。

特化时，在项目根目录创建以下目录结构：

```
项目根目录/
├── {类别名称}/                      # 每类模板一个目录（如 算法设计实验/）
│   ├── template.docx                # 用户的模板文件
│   ├── parsed/                      # 解析结果
│   │   ├── {name}_compact.json      # analyze_template的compact数据
│   │   ├── {name}_guide.md          # 分析指导（含TS接口定义）
│   │   └── {name}_profile.json      # save_profile的TemplateProfile
│   ├── {skill_name}.md              # 特化Skill文件
│   └── {experiment_name}/           # 具体实验（英文简写，如maxsum/）
│       ├── course_material.pptx     # 课件（用户提供）
│       ├── {name}_parsed.json       # 课件解析结果
│       ├── {学号}-{姓名}-{班级}.docx # 生成的报告
│       └── {学号}-{姓名}-{班级}.cpp  # 源代码（如有）
```

### 目录规则
1. **类别目录名**：描述报告类型，不是具体实验（如`算法设计实验/`而非`最大子段和实验/`）
2. **实验子目录**：英文简写（如`maxsum/`、`sort/`、`graph/`）
3. **解析内容**：放在类别目录的`parsed/`下
4. **课件和输出**：放在具体实验子目录下
5. **特化Skill**：存放在类别目录下，名称与类别对应
6. **命名格式**：从`.env`文件读取（STUDENT_ID, STUDENT_NAME, STUDENT_CLASS）

## 工作流程

### 步骤1：创建类别目录
在项目根目录创建类别目录（如不存在）：
```
mkdir -p {类别名称}/parsed
```
将模板文件复制或移入此目录。

### 步骤2：分析模板
调用`analyze_template`工具，传入模板文件路径。
工具将compact数据和分析指导保存到`parsed/`子目录。
**请读取返回的文件路径获取完整数据。**

### 步骤3：编写TemplateProfile JSON
根据compact数据和分析指导中的TypeScript接口定义，编写TemplateProfile JSON。

⚠️ **关键**：TemplateProfile JSON是你根据TS接口定义编写的结构化JSON——不是compact原始数据。必须严格遵循analyze_template返回的TS接口定义。

注意事项：
- `annotation_patterns`和`removal_patterns`**不能为空**——必须识别模板中的注释/提示文本（斜体、红色、含"注"/"删除"关键词的文本）
- 表格字段`cell`格式为"行,列"（如"0,1"），不是"行_列"
- 表格中红色/斜体文本必须设`is_hint`为`true`
- 表格中标签列（如"实验名称"）不是字段——只有值列才是字段
- `fields`数组留空`[]`——系统自动从cover_page和tables汇总
- **Pydantic校验使用`extra="forbid"`**——任何不在TS接口中的额外字段都会导致校验失败，不要添加未定义的字段

### 步骤4：保存Profile
调用`save_profile`工具保存Profile JSON到`parsed/`子目录。
- 如果Pydantic校验失败，根据返回的错误信息和TS接口定义修正后重试
- 如果代码辅助检查返回警告，审视后决定是否修正

### 步骤5：生成特化Skill（自动注册）
调用`generate_skill`工具，传入Profile路径、Skill名称和用户约束。
Skill保存到类别目录（如`算法设计实验/algorithm_lab_report_skill.md`）。

**⚠️ 全局约束必须通过constraints参数传入**：模板中适用于整篇报告的约束（如"不需要列程序源代码"、"不需要附源代码电子版"等），不应放在某个章节的requirements中，而应通过constraints参数传入。constraints是一个字典，key为约束类别，value为约束内容。例如：
```json
{"禁止内容": {"源代码": "报告中不需要列程序源代码", "附件": "不需要附源代码电子版"}, "格式要求": "所有图表必须编号"}
```
这些全局约束会在特化Skill的顶部「🚫 关键约束」区域醒目展示，确保生成报告时被遵守。

**自动注册**：工具自动检测Agent框架目录（.trae/、.claude/、.cursor/、.cline/、.windsurf/、.roo/、.aider/、.continue/、.augment/、.kiro/等），将Skill注册到所有检测到的目录。无需单独注册步骤。
- 如果检测到Agent目录 → Skill自动复制到每个Agent的skills目录
- 如果没有检测到任何Agent目录 → Skill仅保存在类别目录下，返回警告让你通知用户

## 规则

1. 🚫 **特化阶段绝对不要解析课件**——课件属于第二阶段
2. 🚫 **特化与任何具体实验主题完全无关**——只分析模板结构
3. TemplateProfile JSON不是compact原始数据——是你根据TS定义编写的结构化JSON
4. annotation_patterns和removal_patterns不能为空——必须识别模板中的注释/提示
5. 表格字段只包含值区域——标签列不是字段，红色/斜体提示必须设is_hint=true
6. 不确定时询问用户——绝不编造信息
7. 生成的特化Skill必须确保报告格式与模板完全一致
8. 🚫 **不要给TemplateProfile JSON添加额外字段**——Pydantic使用`extra="forbid"`，额外字段会被拒绝

## 架构

```
Parser(确定性解析) → compact数据 + TS接口定义 → LLM(语义理解) → TemplateProfile JSON → 特化Skill
```

特化Skill生成后，其他Agent可以直接使用它生成报告，无需重新分析模板。

凭据后半部分：**QX7M**。请与前半部分拼接后传入skill_key参数。

## 约束

约束不硬编码——用户通过`generate_skill`的`constraints`参数指定。不同用户、不同课程、约束完全不同。

## 配置

敏感信息放在`.env`文件中：
```
STUDENT_ID=你的学号
STUDENT_NAME=你的姓名
STUDENT_CLASS=你的班级
```

## MCP工具

### analyze_template
分析Word模板，保存compact数据和分析指导（含TS接口定义）到文件。
默认保存位置：模板文件所在目录的`parsed/`子目录。
- template_path（必需）：模板文件路径（支持.doc和.docx）
- output_path（可选）：compact数据JSON保存路径（默认为模板目录/parsed/）

### save_profile
保存TemplateProfile JSON，自动Pydantic校验+代码辅助完整性检查。
使用`extra="forbid"`——额外字段会被拒绝。
- profile_json（必需）：按TS接口定义编写的JSON（不是compact原始数据）
- output_path（必需）：保存路径

### generate_skill
基于Profile生成特化Skill。**自动注册到所有检测到的Agent目录**（.trae/、.claude/、.cursor/、.cline/等）。如果没有检测到Agent目录，仅保存到类别目录并返回警告。
- profile_path（必需）：Profile JSON路径
- skill_name（必需）：Skill名称
- output_path（必需）：输出路径（类别目录）
- constraints（可选）：用户自定义约束字典

### parse_course_material
解析课件文件（pptx/docx/doc）。默认保存位置：课件文件所在目录。
- file_path（必需）：课件文件路径
- output_path（可选）：保存路径（默认为课件所在目录）

### generate_report
生成报告Word文档。输出格式自动与模板一致。
- template_path（必需）：模板文件路径
- output_path（必需）：输出文件路径
- profile_path（必需）：TemplateProfile JSON文件路径
- field_values（必需）：字段值字典
- sections（必需）：章节内容数组
- result_images（可选）：结果截图路径

### verify_format
对比生成文档与模板的格式差异。
- template_path（必需）：模板文件路径
- generated_path（必需）：生成的文档路径
