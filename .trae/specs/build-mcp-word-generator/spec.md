# MCP Word 实验报告生成器 Spec

## Why
需要一个自动化的工作流，能够读取Word模板文档，严格按模板格式生成实验报告Word文档。核心产出是一个MCP工具+Skill，让LLM Agent能够通过调用MCP工具生成完全符合模板格式的Word文档，而不是硬编码题目代码。

## What Changes
- 创建Python虚拟环境及项目工程结构
- 实现模板解析器：读取.doc/.docx模板，提取文档结构（标题、表格、段落样式、字体、字号等）
- 实现Word文档生成器：基于模板结构，接受参数填充内容，输出格式完全一致的Word文档
- 实现MCP Server：提供`generate_report`工具，接受模板路径、输出路径、内容参数，生成Word文档
- 创建Skill描述文件：让Agent知道如何使用此MCP工具
- 创建可配置的命名规则（学号-姓名-班级）
- 在dev_test/目录下用sy2（最大字段和问题）进行端到端验证

## Impact
- Affected specs: 无既有spec
- Affected code: 新建整个工程，不影响现有代码

## ADDED Requirements

### Requirement: 项目工程结构
系统 SHALL 采用工程化目录结构，包含以下分层：
```
glm/
├── .trae/
│   └── specs/
├── config.yaml              # 可配置变量（学号、姓名、班级、命名格式等）
├── dev_test/                # 测试输出目录
├── src/
│   ├── __init__.py
│   ├── template_parser/     # 模板层：解析Word模板结构
│   │   ├── __init__.py
│   │   └── parser.py
│   ├── doc_generator/       # 工作层：生成Word文档
│   │   ├── __init__.py
│   │   └── generator.py
│   ├── protocol/            # 协议层：MCP工具接口定义与参数schema
│   │   ├── __init__.py
│   │   └── schema.py
│   ├── constraints/         # 约束层：代码风格约束（拼音命名、学生风格等）
│   │   ├── __init__.py
│   │   └── style_rules.py
│   └── mcp_server/          # MCP Server入口
│       ├── __init__.py
│       └── server.py
├── skills/
│   └── experiment_report.md # Skill描述文件
├── sy2/                     # 实验2课件
└── 算法设计与分析实验报告模板-最新(1).doc  # 模板文件
```

#### Scenario: 项目结构创建成功
- **WHEN** 执行项目初始化
- **THEN** 上述目录结构全部创建，虚拟环境可用，依赖安装完成

### Requirement: 配置系统
系统 SHALL 提供config.yaml配置文件，包含：
- `student_id`: 学号
- `student_name`: 姓名
- `student_class`: 班级
- `naming_format`: 命名格式模板，如"{student_id}-{student_name}-{student_class}"
- `template_path`: 模板文件路径
- `output_base_dir`: 输出根目录

#### Scenario: 读取配置生成文件名
- **WHEN** 需要生成实验报告文件名
- **THEN** 按照naming_format拼接学号-姓名-班级，如"2021001-张三-计算机1班"

### Requirement: 模板解析器（模板层）
系统 SHALL 能解析.doc和.docx格式的Word模板文档，提取：
- 文档整体结构（段落顺序、表格位置）
- 每个段落的样式信息（字体、字号、加粗、居中等）
- 表格结构（行列数、单元格样式、合并信息）
- 页面设置（页边距、纸张大小）
- 占位内容（用于后续替换的文本区域）

#### Scenario: 解析.doc模板
- **WHEN** 传入.doc格式模板文件
- **THEN** 成功提取文档结构和样式信息，输出结构化JSON描述

#### Scenario: 解析.docx模板
- **WHEN** 传入.docx格式模板文件
- **THEN** 成功提取文档结构和样式信息，输出结构化JSON描述

### Requirement: Word文档生成器（工作层）
系统 SHALL 基于模板解析结果和内容参数，生成与模板格式完全一致的Word文档：
- 保持模板的页面设置（页边距、纸张大小）
- 保持模板的段落样式（字体、字号、对齐方式）
- 保持模板的表格结构和样式
- 将参数内容填充到对应位置
- 支持图片插入（如运行结果截图）

#### Scenario: 生成格式一致的Word文档
- **WHEN** 提供模板解析结果和内容参数
- **THEN** 生成的Word文档与模板格式完全一致，内容正确填充

### Requirement: MCP Server（协议层）
系统 SHALL 提供MCP Server，暴露`generate_report`工具：
- 输入参数：
  - `template_path`: 模板文件路径
  - `output_path`: 输出文件路径
  - `experiment_name`: 实验名称
  - `experiment_purpose`: 实验目的
  - `sections`: 内容段落列表，每个section包含title和content
  - `code_sections`: 代码段列表，每个包含title和code
  - `result_images`: 结果截图路径列表（可选）
- 输出：生成的Word文档路径

#### Scenario: LLM调用MCP生成报告
- **WHEN** LLM通过MCP协议调用generate_report工具，传入必要参数
- **THEN** 系统生成符合模板格式的Word文档，返回文件路径

### Requirement: 代码风格约束（约束层）
系统 SHALL 提供代码风格规则，供LLM生成实验代码时参考：
- 函数命名使用拼音（如erfen而非binary_search）
- 变量命名简单（如int a, vector<int> v）
- 数据硬编码或随机生成，不使用cin输入
- 输出简洁，说明清楚即可
- 整体风格像学生手写，避免AI感

#### Scenario: 约束规则可被查询
- **WHEN** LLM查询代码风格约束
- **THEN** 返回上述规则，LLM据此生成学生风格的代码

### Requirement: Skill描述
系统 SHALL 提供Skill描述文件，让Agent了解：
- 如何使用MCP工具生成实验报告
- 实验文件夹的创建规则（sy1, sy2...）
- 命名规则（学号-姓名-班级）
- 代码风格要求
- 工作流程步骤

#### Scenario: Agent读取Skill描述
- **WHEN** Agent加载experiment_report skill
- **THEN** Agent了解完整工作流程，能正确调用MCP工具

### Requirement: 端到端验证
系统 SHALL 使用sy2（最大字段和问题）进行端到端验证：
- 解析模板Word文档
- 基于sy2课件内容，模拟LLM传入参数
- 生成实验报告Word文档
- 验证输出文档格式与模板一致
- 所有测试输出到dev_test/目录

#### Scenario: sy2验证通过
- **WHEN** 执行端到端验证流程
- **THEN** dev_test/目录下生成格式正确的Word文档，内容包含最大字段和问题的三个算法部分

## 设计原则

### 分层架构
1. **模板层（template_parser）**：负责解析Word模板，提取结构化描述。不同模板只需替换此层。
2. **协议层（protocol）**：定义MCP工具接口、参数schema。是LLM与系统的契约。
3. **工作层（doc_generator）**：基于模板描述和参数，生成Word文档。核心逻辑。
4. **约束层（constraints）**：代码风格、命名规则等约束，供LLM参考。

### 扩展性考虑
- 模板层可替换：未来支持任意模板，只需实现对应的parser
- 协议层参数可扩展：section结构支持任意数量的内容段
- 约束层可配置：不同课程可能有不同代码风格要求
- MCP工具可组合：generate_report是核心工具，未来可加parse_template等辅助工具
