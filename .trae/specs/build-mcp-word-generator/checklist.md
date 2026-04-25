# Checklist

- [ ] Python虚拟环境创建成功，依赖安装完成，requirements.txt存在
- [ ] 项目目录结构完整（src/template_parser, src/doc_generator, src/protocol, src/constraints, src/mcp_server, skills, dev_test）
- [ ] config.yaml配置文件存在，包含学号、姓名、班级、命名格式等字段
- [ ] 模板解析器能正确解析.doc/.docx模板，输出结构化JSON描述
- [ ] 模板解析结果包含：段落结构、表格结构、样式信息、页面设置
- [ ] Word文档生成器能基于模板描述生成格式一致的文档
- [ ] 生成的Word文档页面设置与模板一致（页边距、纸张大小）
- [ ] 生成的Word文档段落样式与模板一致（字体、字号、对齐、加粗）
- [ ] 生成的Word文档表格结构与模板一致
- [ ] 图片插入功能可用
- [ ] MCP Server可通过stdio协议启动
- [ ] MCP generate_report工具参数schema定义完整
- [ ] 调用generate_report工具能成功生成Word文档
- [ ] 代码风格约束规则已定义并可查询
- [ ] Skill描述文件存在，包含完整工作流程说明
- [ ] dev_test/目录下存在sy2验证生成的Word文档
- [ ] 生成的Word文档文件名符合学号-姓名-班级命名格式
- [ ] 生成的Word文档内容包含最大字段和问题的算法部分
