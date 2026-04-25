# Tasks

- [x] Task 1: 项目初始化与虚拟环境搭建
  - [x] SubTask 1.1: 创建Python虚拟环境（venv）
  - [x] SubTask 1.2: 创建项目工程目录结构（src/template_parser, src/doc_generator, src/protocol, src/constraints, src/mcp_server, skills, dev_test）
  - [x] SubTask 1.3: 创建config.yaml配置文件（学号、姓名、班级、命名格式等占位）
  - [x] SubTask 1.4: 安装依赖（python-docx, mcp, pyyaml等），生成requirements.txt

- [ ] Task 2: 模板解析器实现（模板层）
  - [ ] SubTask 2.1: 实现docx格式模板解析（提取段落、表格、样式、页面设置）
  - [ ] SubTask 2.2: 实现doc格式兼容处理（doc转docx后解析，或使用替代方案）
  - [ ] SubTask 2.3: 输出结构化模板描述JSON，包含完整的文档结构和样式信息
  - [ ] SubTask 2.4: 用实际模板文件测试解析结果，确认结构正确

- [ ] Task 3: Word文档生成器实现（工作层）
  - [ ] SubTask 3.1: 实现基于模板描述的文档框架生成（页面设置、基础结构）
  - [ ] SubTask 3.2: 实现段落填充（保持字体、字号、对齐、加粗等样式）
  - [ ] SubTask 3.3: 实现表格填充（保持表格结构、单元格样式、合并信息）
  - [ ] SubTask 3.4: 实现图片插入功能
  - [ ] SubTask 3.5: 用模板解析结果+模拟参数生成测试文档，与原模板格式对比验证

- [ ] Task 4: 协议层与MCP Server实现
  - [ ] SubTask 4.1: 定义generate_report工具的参数schema（template_path, output_path, experiment_name, sections, code_sections等）
  - [ ] SubTask 4.2: 实现MCP Server，注册generate_report工具
  - [ ] SubTask 4.3: 工具内部调用模板解析器+文档生成器，完成端到端流程
  - [ ] SubTask 4.4: 测试MCP Server可通过stdio协议调用

- [ ] Task 5: 约束层实现
  - [ ] SubTask 5.1: 定义代码风格规则（拼音命名、简单变量、硬编码数据、简洁输出）
  - [ ] SubTask 5.2: 规则可被MCP工具或Skill查询返回

- [ ] Task 6: Skill描述文件创建
  - [ ] SubTask 6.1: 编写experiment_report skill描述，包含工作流程、命名规则、MCP工具使用方法、代码风格要求
  - [ ] SubTask 6.2: Skill描述中明确Agent的工作步骤：读取课件→生成代码文件→调用MCP生成报告

- [ ] Task 7: 端到端验证（sy2最大字段和问题）
  - [ ] SubTask 7.1: 解析实际模板Word文档，确认模板结构
  - [ ] SubTask 7.2: 模拟LLM参数输入（实验名称、实验目的、三个算法section等）
  - [ ] SubTask 7.3: 调用MCP generate_report工具生成Word文档
  - [ ] SubTask 7.4: 输出到dev_test/目录，验证格式与模板一致
  - [ ] SubTask 7.5: 验证文件命名符合学号-姓名-班级格式

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2, Task 3]
- [Task 5] depends on [Task 1]
- [Task 6] depends on [Task 4, Task 5]
- [Task 7] depends on [Task 4, Task 6]
- [Task 1] 无依赖，可立即开始
- [Task 5] 与 [Task 2, Task 3] 可并行
