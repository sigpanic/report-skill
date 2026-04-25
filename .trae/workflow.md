# 报告.skill 技术工作流程说明

## 核心设计原则

### 单一真相源：Pydantic → TypeScript
数据结构定义以Pydantic模型为唯一标准源（`src/protocol/profile_schema.py`），TypeScript接口由Pydantic模型自动生成（`src/protocol/ts_generator.py`），从构造上消除TS与Pydantic不一致的可能。

### LLM如何获知数据结构定义
LLM不需要读代码来发现数据结构。定义通过以下机制自动告知AI：
1. **analyze_template工具返回**：调用`analyze_template`时，返回的compact数据后附完整的TS接口定义（自动从Pydantic生成）
2. **save_profile验证反馈**：当LLM调用`save_profile`保存Profile JSON时，如果Pydantic验证失败，错误信息中会附带完整的TS接口定义，帮助LLM修正
3. **save_profile工具描述**：工具schema的description中包含关键字段说明

### 验证闭环
```
LLM生成JSON → Pydantic校验 → 通过则保存/失败则返回错误+TS定义 → LLM修正 → 再次校验
```

## 跨Agent可用性

本系统基于MCP（Model Context Protocol）协议，通过stdio传输，任何支持MCP的Agent都可以使用：
- **Trae**: 在.trae/mcp.json中配置MCP Server
- **Claude Code**: 在claude_desktop_config.json中添加MCP Server
- **其他MCP客户端**: 配置stdio连接即可

MCP Server启动命令：
```
.venv\Scripts\python.exe src\mcp_server\server.py
```

## 系统架构

```
用户模板 → [模板层] → Compact数据(JSON)
                              ↓
                    [LLM+TS接口定义] → TemplateProfile(JSON)
                              ↓                    ↓
用户约束 → [Skill生成器] ← Profile    [Pydantic校验] → 验证反馈
                 ↓
           特化Skill(.md)
                 ↓
用户课件 → [课件解析器] → 课件内容
                 ↓
    [文档生成器] → Word文档
                 ↓
    [格式验证器] → 验证结果
```

## 完整工作流程

### 阶段1：模板分析（LLM驱动）

1. 用户提供Word模板文件路径
2. Agent调用`analyze_template`工具
3. 工具内部流程：
   - `parser.py`解析Word文档，提取段落/表格/样式原始数据
   - `analyzer.py`将原始数据压缩为compact格式（格式目录+引用模式，减少60% token）
   - 返回compact数据 + 自动生成的TS接口定义 + 分析步骤指导
4. LLM根据compact数据和TS接口定义，分析模板结构，生成TemplateProfile JSON
5. LLM调用`save_profile`工具保存Profile JSON
6. `save_profile`内部用Pydantic校验JSON：
   - 通过 → 自动补全fields（从cover_page和tables汇总）→ 保存
   - 失败 → 返回具体错误 + TS接口定义 → LLM修正后重试

### 阶段2：Skill特化（必须）

1. 用户提供约束规则（如代码风格、命名规则等）
2. Agent调用`generate_skill`工具
3. 工具基于Profile生成特化Skill .md文件
4. Skill包含：字段定义、章节结构、格式规则、约束规则、工作流程
5. **特化Skill是生成报告的前提**——只有根据特化Skill才能正确生成报告

### 阶段3：报告生成

1. Agent调用`get_env_config`获取.env中的个人信息
2. 用户提供课件/资料
3. Agent调用`parse_course_material`解析课件
4. Agent根据Profile中的章节结构和课件内容，准备各章节文字
5. Agent准备字段值（封面+表格，.env中的信息自动填充）
6. Agent调用`generate_report`工具
7. 工具内部流程：
   - 复制模板文件（保持格式基础）
   - 填充封面字段（run级别替换，保持下划线等格式）
   - 填充表格字段（保持单元格样式）
   - 插入章节内容（按format_rules排版）
   - 删除注释段落（按annotation_patterns/removal_patterns）
   - 输出格式与模板一致（.doc→.doc, .docx→.docx）
8. Agent调用`verify_format`验证格式一致性

## 分层说明

### 模板层 (src/template_parser/)
- `parser.py`: Word文档基础解析，提取段落/表格/样式原始数据，支持.doc→.docx转换
- `analyzer.py`: compact数据生成 + analysis guide（含自动生成的TS接口定义）
- `course_parser.py`: 课件解析，支持pptx/ppt/docx/doc

### 协议层 (src/protocol/)
- `profile_schema.py`: **Pydantic模型定义（单一真相源）**，包含14个模型类
- `ts_generator.py`: **从Pydantic模型自动生成TypeScript接口**，确保TS与Pydantic一致
- `schema.py`: MCP工具参数Schema定义（6个工具）

### 工作层 (src/doc_generator/)
- `generator.py`: Word文档生成，run级别格式保持，输出格式与模板一致
- `verifier.py`: 格式验证，对比页面设置/段落样式/表格结构

### Skill生成器 (src/skill_generator/)
- `generator.py`: 基于TemplateProfile生成特化Skill描述文件

### 约束层 (src/constraints/)
- `style_rules.py`: 约束规则管理（通用，不硬编码特定约束）

### MCP Server (src/mcp_server/)
- `server.py`: MCP工具注册和实现，6个工具

## MCP工具详细说明

### analyze_template
分析Word模板 → compact数据 + TS接口定义
- 输入: template_path, output_path(可选)
- 输出: compact格式数据 + 自动生成的TS接口定义 + 分析步骤指导
- compact数据使用格式目录+引用模式，大幅减少token消耗

### save_profile
保存LLM生成的TemplateProfile JSON，自动Pydantic校验
- 输入: profile_json, output_path
- 校验通过: 自动补全fields（从cover_page和tables汇总）→ 保存
- 校验失败: 返回具体错误 + 完整TS接口定义 → LLM可修正后重试

### generate_report
生成报告Word文档
- 输入: template_path, output_path, profile_path, field_values, sections, result_images(可选)
- field_values: 字典，key=Profile中的field key, value=要填入的值
- sections: 数组，每项含title(必须与Profile section title完全匹配)和content
- 输出格式与模板一致(.doc→.doc, .docx→.docx)

### generate_skill
生成特化Skill
- 输入: profile_path, skill_name, output_path, constraints(可选)
- constraints: 用户自定义约束，如代码风格、命名规则等
- 输出: Skill .md文件

### parse_course_material
解析课件
- 输入: file_path, output_path(可选)
- 支持格式: .pptx, .ppt, .docx, .doc
- 输出: 课件内容JSON，含full_text和image_note

### verify_format
验证格式一致性
- 输入: template_path, generated_path, output_path(可选)
- 检查: 页面设置、段落样式、字体、字号、加粗、斜体、下划线、表格结构

## TemplateProfile数据结构

### 核心模型关系
```
TemplateProfile
├── template_path: string
├── page_setup: PageSetup (6个浮点数字段)
├── cover_page: CoverPage
│   ├── title: CoverTitle | null
│   ├── fields: CoverField[] (key, label, type, default, style)
│   └── college: CoverCollege | null
├── tables: TableInfo[]
│   └── fields: TableField[] (key, cell, label, type, is_hint, style)
├── sections: SectionInfo[]
│   ├── title, style: SectionStyle, note
├── format_rules: FormatRules
│   ├── body_text: BodyTextStyle
│   ├── section_header: SectionHeaderStyle
│   └── line_spacing_pt, first_line_indent_chars, space_before, space_after
├── annotation_patterns: string[]
├── removal_patterns: string[]
└── fields: FieldEntry[] (系统自动从cover_page和tables汇总)
```

### 字段类型说明
- **CoverField.type**: `"text_with_underline"` | `"text"` — 有下划线用text_with_underline
- **TableField.type**: `"table_cell"` — 表格单元格
- **TableField.is_hint**: 是否为提示性内容（红色/斜体文本）
- **FieldEntry**: 统一字段模型，系统自动从cover_page和tables汇总生成，含source字段标识来源

## 关键设计决策

1. **Pydantic为单一真相源**: TS接口从Pydantic自动生成，不可能不一致
2. **复制模板策略**: 生成器复制模板文件后修改，而非从零创建，确保格式最大程度保持
3. **Run级别格式保持**: 封面页字段替换时，保持原始run结构，标签run不变，值run替换文本
4. **Profile驱动**: 所有操作基于TemplateProfile，不硬编码模板特定逻辑
5. **约束用户指定**: 约束规则不是硬编码的，由用户在generate_skill时传入
6. **不确定就问用户**: 系统不编造信息，缺少信息时提示用户
7. **验证反馈闭环**: save_profile校验失败时返回错误+TS定义，LLM可自动修正

## 已知限制

1. OCR依赖Tesseract引擎，需用户自行安装
2. 复杂的Word格式（如文本框、艺术字）可能无法完美保持
3. 合并单元格的检测依赖python-docx的实现，可能有边界情况
4. .doc格式需要Windows COM接口（Word应用），非Windows平台不可用
5. LLM生成的Profile JSON可能需要多次校验-修正循环才能通过Pydantic验证
6. 格式验证器(verifier)目前按段落索引对比，插入/删除内容后段落偏移会导致对比不准确（需改进为按语义身份对比）
7. 章节标题匹配要求精确字符串匹配，模板中的空格/Unicode差异可能导致匹配失败
8. Skill生成器的工作流描述目前偏向实验报告场景，非实验报告模板需要进一步泛化

## Code Review修复记录

### 已修复
- 清理所有未使用的import（profile_schema.py, analyzer.py, generator.py, verifier.py, parser.py）
- fix_profile_pydantic增加异常处理：当fallback构造TemplateProfile失败时使用安全默认值
- generate_skill增加Pydantic校验：生成Skill前先验证Profile格式
- generate_report不再覆盖原始Profile文件（移除副作用）
- pyright扫描：0 errors, 0 warnings
- Skill生成器工作流描述模板无关化：移除"实验报告"硬编码，改为通用"报告/文档"
- 格式规则提取支持多种编号格式：中文(一、)、阿拉伯(1.)、英文(Chapter/Section)
- verifier.py和parser.py的bare except改为except Exception
- generator.py临时文件清理：try/finally中清理tempfile目录
- Skill模板增加save_profile工具说明

### 待改进
- verifier应改为基于format_rules的语义对比，而非段落索引对比
- 章节标题匹配应增加模糊匹配（类似封面的fuzzy_match_label）
- 临时文件清理（generator.py中的tempfile目录）
