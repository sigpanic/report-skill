# 实验报告Skill生成器（通用版）

## 概述
本Skill是一个**通用的实验报告Skill生成器**。它不针对任何特定模板或专业，而是通过分析用户提供的Word模板文档，自动生成针对该模板的特化Skill。任何Agent安装特化Skill后，即可轻松生成完全符合模板格式的报告。

**核心理念：你提供模板，我生成Skill。**

## 适用范围
- 任何专业的实验报告（计算机、物理、化学、生物、电子等）
- 课程报告、实训报告、课程设计报告
- 任何有Word模板的结构化文档

## 重要原则

### 原则1：不确定就问用户
如果有任何不确定的信息（如学号、姓名、班级、实验日期、指导老师等），**直接询问用户**，不要自己编造。这是最高优先级原则。

### 原则2：服从模板规则
模板中的注释和说明（如"写实验报告时删除此注释"、"不需要列源代码"等）**必须严格遵守**。系统会自动删除这些注释段落，但其指导意义必须被遵循。

### 原则3：服从用户约束
用户指定的约束（如代码风格、命名规则、内容风格等）**必须遵守**。约束由用户指定，不是硬编码的。

### 原则4：格式完全对齐
生成的Word文档格式必须与模板**完全一致**。字体、字号、行距、缩进、对齐方式等都必须严格保持。这是格式方面的最高优先级。

## 工作流程

### 阶段一：特化（每个模板只需做一次）

#### 步骤1：用户提供模板
- 用户提供Word模板文件（.doc或.docx）
- 模板可以是任何类型的实验报告、课程报告、实训报告等
- 用户可能同时提供课件文件（.pptx, .ppt, .docx, .doc）

#### 步骤2：分析模板
- 调用 `analyze_template` MCP工具分析模板
- 工具会自动提取：
  - 封面页字段（如学生姓名、学号、课程名等）
  - 表格字段（如实验名称、日期、地点等）
  - 章节结构（如实验目的、实验内容、算法描述等）
  - 格式规则（字体、字号、行距、缩进等）
  - 模板中的注释和说明（如"删除此注释"、"不需要列源代码"等）
- 将TemplateProfile保存为JSON文件
- **注意**：分析结果中的字段key和章节title必须原样使用，不要修改

#### 步骤3：解析课件（如有）
- 调用 `parse_course_material` MCP工具解析课件
- 提取实验要求、算法描述、关键知识点等
- 课件内容用于指导报告内容的撰写

#### 步骤4：生成特化Skill
- 调用 `generate_skill` MCP工具
- 传入：
  - profile_path: 步骤2生成的Profile JSON路径
  - skill_name: Skill名称（如"算法设计实验报告"、"物理实验报告"等）
  - output_path: Skill文件输出路径
  - constraints: 用户指定的约束规则（**可选，由用户指定，不硬编码**）
- 生成的Skill包含该模板的所有字段定义、章节结构、格式规则和用户约束
- **约束由用户指定**，不是硬编码的。如果用户没有指定约束，则不添加约束
- 将生成的特化Skill安装到Agent的skill目录中

### 阶段二：生成报告（每次实验/报告时执行）

#### 步骤5：理解任务
- 读取用户提供的课件/资料，理解实验/报告要求
- 提取关键信息：实验名称、目的、方法等
- 如果有任何不确定的信息，直接询问用户

#### 步骤6：准备内容
- 根据课件内容和特化Skill中的章节定义，准备各章节的文字内容
- 每个章节的内容必须遵守模板中的说明
- 内容风格应自然，避免AI感

#### 步骤7：准备字段值
- 收集所有需要填写的字段值
- 不确定的字段值必须询问用户
- 字段key必须与Profile中的key完全匹配

#### 步骤8：调用MCP工具生成文档
- 调用 `generate_report` MCP工具
- 传入：
  - template_path: 模板文件路径
  - output_path: 输出路径
  - profile_path: TemplateProfile JSON路径
  - field_values: 字段值字典
  - sections: 章节内容数组（每项的title必须与Profile中的section title完全匹配）

#### 步骤9：验证输出
- 调用 `verify_format` MCP工具验证格式一致性
- 检查所有字段是否正确填充
- 如果格式不一致，分析原因并修正

## MCP工具

### analyze_template
分析Word模板，生成TemplateProfile。

参数：
- template_path (必需): 模板文件路径（支持.doc和.docx）
- output_path (可选): Profile JSON保存路径

返回：TemplateProfile，包含字段列表、章节列表、格式规则、模板说明等

### generate_report
基于模板和Profile生成报告Word文档。

参数：
- template_path (必需): 模板文件路径
- output_path (必需): 输出文件路径
- profile_path (必需): TemplateProfile JSON文件路径
- field_values (必需): 字段值字典，key对应Profile中的field key
- sections (必需): 章节内容数组，每项含title和content
- result_images (可选): 结果截图路径列表

### generate_skill
基于Profile生成特化Skill描述文件。

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

约束示例（仅作参考，实际由用户指定）：

```json
{
  "代码风格": {
    "函数命名": "使用拼音，如erfen(二分)、chuantong(传统)",
    "变量命名": "简单命名，如int a, int n, vector<int> v",
    "数据输入": "硬编码数据，不使用cin输入",
    "输出风格": "简洁说明即可",
    "整体风格": "像学生手写，避免AI感"
  },
  "命名规则": {
    "报告文件": "学号-姓名-班级",
    "源代码文件": "学号-姓名-班级.cpp"
  }
}
```

不同用户、不同课程、不同专业的约束完全不同，本Skill不预设任何约束。

## 格式对齐规则

为确保生成的Word文档与模板格式完全一致，系统遵循以下规则：

1. **复制模板策略**：生成器复制模板文件后修改，而非从零创建，确保格式最大程度保持
2. **Run级别格式保持**：封面页字段替换时，保持原始run结构，标签run不变，值run替换文本
3. **Profile驱动**：所有操作基于TemplateProfile，不硬编码模板特定逻辑
4. **自动删除注释**：模板中的注释段落（斜体、含特定关键词）会被自动删除
5. **章节内容格式**：新增的章节内容严格按照Profile中的format_rules排版

## 跨Agent可用性

基于MCP（Model Context Protocol）标准协议，通过stdio传输，任何支持MCP的Agent都可以使用：

| Agent | 配置方式 |
|-------|----------|
| Trae | 在.trae配置中添加MCP Server |
| Claude Code | 在claude_desktop_config.json中添加MCP Server |
| 其他MCP客户端 | 配置stdio连接即可 |

MCP Server启动命令：
```
.venv\Scripts\python.exe src\mcp_server\server.py
```

## 配置

项目根目录的 `config.yaml` 包含用户个人信息：
```yaml
student_id: "学号"
student_name: "姓名"
student_class: "班级"
naming_format: "{student_id}-{student_name}-{student_class}"
template_path: "模板文件名"
output_base_dir: "."
```

敏感信息建议放在 `.env` 文件中：
```
STUDENT_ID=你的学号
STUDENT_NAME=你的姓名
STUDENT_CLASS=你的班级
```

## 注意事项
- 模板格式必须严格保持一致，这是最高优先级
- TemplateProfile是通用生成器和特化Skill之间的桥梁
- 约束规则完全由用户指定，本Skill不预设任何约束
- 支持.doc和.docx格式的模板
- 课件支持.pptx, .ppt, .docx, .doc格式
- 如果有任何不确定的信息，直接询问用户，不要自己编造
