# 实验报告Skill生成器（通用版）

## 概述
本Skill是一个**通用的实验报告Skill生成器**。它不针对任何特定模板或专业，而是通过分析用户提供的Word模板文档，让LLM理解模板结构后生成针对该模板的特化Skill。任何Agent安装特化Skill后，即可轻松生成完全符合模板格式的报告。

**核心理念：Parser提取原始数据，LLM做语义理解，Skill模板填空生成。**

## 适用范围
- 任何专业的实验报告（计算机、物理、化学、生物、电子等）
- 课程报告、实训报告、课程设计报告
- 任何有Word模板的结构化文档

## 重要原则

### 原则1：不确定就问用户
如果有任何不确定的信息（如学号、姓名、班级、实验日期、指导老师等），**直接询问用户**，不要自己编造。这是最高优先级原则。

### 原则2：服从模板规则
模板中的注释和说明（如"写实验报告时删除此注释"、"不需要列源代码"等）**必须严格遵守**。

### 原则3：服从用户约束
用户指定的约束（如代码风格、命名规则、内容风格等）**必须遵守**。约束由用户指定，不是硬编码的。

### 原则4：格式完全对齐
生成的Word文档格式必须与模板**完全一致**。字体、字号、行距、缩进、对齐方式等都必须严格保持。

### 原则5：输出格式与模板一致
模板是.doc则输出.doc，模板是.docx则输出.docx。

## 工作流程

### 阶段一：特化（每个模板只需做一次）

#### 步骤1：用户提供模板
- 用户提供Word模板文件（.doc或.docx）
- 用户可能同时提供课件文件（.pptx, .ppt, .docx, .doc）

#### 步骤2：提取模板原始数据
- 调用 `analyze_template` MCP工具
- 工具会提取原始结构数据：
  - 所有段落的文本、格式（字体、字号、加粗、斜体、下划线、颜色）
  - 所有表格的单元格内容、位置、格式
  - 页面设置（纸张大小、页边距）
- 工具同时返回分析指导，告诉你如何解读这些数据

#### 步骤3：LLM分析模板结构
- **这一步由LLM（你）完成**，不是硬编码规则
- 根据原始数据，判断：
  - 哪些段落是封面标题？哪些是学院名称？
  - 哪些是带标签的填充字段（如"学生姓名："后跟下划线）？
  - 表格中哪些单元格是标签，哪些是值区域？
  - 哪些是章节标题？哪些是注释/说明？
  - 格式要求是什么（字体、字号、行距等）？
- 生成TemplateProfile JSON并保存

#### 步骤4：解析课件（如有）
- 调用 `parse_course_material` MCP工具解析课件
- 提取实验要求、关键知识点等

#### 步骤5：生成特化Skill
- 调用 `generate_skill` MCP工具
- 传入Profile、Skill名称、用户约束
- 工具使用填空式模板生成Skill，确保格式统一
- 约束由用户指定，不硬编码

### 阶段二：生成报告（每次实验/报告时执行）

#### 步骤6-10：同之前的流程
- 理解任务 → 准备内容 → 准备字段值 → 调用generate_report → 验证输出

## MCP工具

### analyze_template
提取Word模板的原始结构数据，返回给LLM分析。

参数：
- template_path (必需): 模板文件路径（支持.doc和.docx）
- output_path (可选): 原始数据JSON保存路径

返回：原始结构数据 + 分析指导

### generate_report
基于模板和Profile生成报告Word文档。

参数：
- template_path (必需): 模板文件路径
- output_path (必需): 输出文件路径（后缀与模板一致）
- profile_path (必需): TemplateProfile JSON文件路径
- field_values (必需): 字段值字典
- sections (必需): 章节内容数组
- result_images (可选): 结果截图路径列表

### generate_skill
基于Profile生成特化Skill描述文件（填空式模板）。

参数：
- profile_path (必需): TemplateProfile JSON文件路径
- skill_name (必需): Skill名称
- output_path (必需): Skill文件输出路径
- constraints (可选): 用户指定的约束规则字典

### parse_course_material
解析课件文件，提取文本内容。

参数：
- file_path (必需): 课件文件路径（支持.pptx, .ppt, .docx, .doc）
- output_path (可选): 解析结果JSON保存路径

### verify_format
对比生成的Word文档与模板的格式差异。

参数：
- template_path (必需): 模板文件路径
- generated_path (必需): 生成的文档路径
- output_path (可选): 验证结果JSON保存路径

## 约束规则说明

约束规则**不是硬编码的**，由用户在调用 `generate_skill` 时通过 `constraints` 参数传入。

不同用户、不同课程、不同专业的约束完全不同，本Skill不预设任何约束。

## 架构设计

```
Parser(确定性) → 原始数据 → LLM(语义理解) → Profile → Skill模板(填空式) → 特化Skill
                                    ↓
                              generate_report → Word文档
```

- **Parser**: 确定性地提取文本、格式、位置等原始数据，不做语义判断
- **LLM**: 根据原始数据理解模板结构，生成Profile
- **Skill模板**: 填空式模板，LLM的Profile数据填入指定位置
- **generate_report**: 根据Profile和用户内容生成Word文档

## 跨Agent可用性

基于MCP（Model Context Protocol）标准协议，通过stdio传输，任何支持MCP的Agent都可以使用。

MCP Server启动命令：
```
.venv\Scripts\python.exe src\mcp_server\server.py
```

## 配置

敏感信息放在 `.env` 文件中：
```
STUDENT_ID=你的学号
STUDENT_NAME=你的姓名
STUDENT_CLASS=你的班级
```

## 注意事项
- 模板格式必须严格保持一致，这是最高优先级
- Profile是通用生成器和特化Skill之间的桥梁
- 约束规则完全由用户指定
- 输出文件后缀必须与模板一致
- 如果有任何不确定的信息，直接询问用户，不要自己编造
