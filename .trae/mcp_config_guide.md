# Trae MCP Server 配置指南

## 在Trae中使用报告.skill MCP Server

### 方式一：在.trae/mcp.json中配置

在项目根目录的 `.trae/mcp.json` 文件中添加：

```json
{
  "mcpServers": {
    "report-skill-generator": {
      "command": "c:\\Users\\20598\\Desktop\\project\\glm\\.venv\\Scripts\\python.exe",
      "args": ["c:\\Users\\20598\\Desktop\\project\\glm\\src\\mcp_server\\server.py"],
      "cwd": "c:\\Users\\20598\\Desktop\\project\\glm"
    }
  }
}
```

### 方式二：在Claude Desktop中使用

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "report-skill-generator": {
      "command": "c:\\Users\\20598\\Desktop\\project\\glm\\.venv\\Scripts\\python.exe",
      "args": ["c:\\Users\\20598\\Desktop\\project\\glm\\src\\mcp_server\\server.py"],
      "cwd": "c:\\Users\\20598\\Desktop\\project\\glm"
    }
  }
}
```

### 不需要单独起服务

MCP Server通过stdio协议通信，**不需要单独启动服务**。Agent会自动启动和管理MCP Server进程。

当Agent需要使用工具时：
1. Agent启动MCP Server进程
2. 通过stdin/stdout通信
3. 调用完毕后进程自动结束

### 可用的6个工具

| 工具 | 用途 |
|------|------|
| `analyze_template` | 分析Word模板，返回compact数据+TS接口定义 |
| `save_profile` | 保存Profile JSON，自动Pydantic校验+补全fields |
| `generate_report` | 生成报告Word文档 |
| `generate_skill` | 生成特化Skill描述文件 |
| `parse_course_material` | 解析课件（pptx/ppt/docx/doc） |
| `verify_format` | 验证格式一致性 |

### 使用流程

1. **首次使用（模板分析+特化）**：
   - 告诉Agent你的模板文件路径
   - Agent调用`analyze_template`分析模板，获得compact数据和TS接口定义
   - Agent根据数据生成TemplateProfile JSON
   - Agent调用`save_profile`保存Profile（自动校验+补全）
   - Agent调用`generate_skill`生成特化Skill
   - 你提供约束规则（如代码风格）

2. **每次生成报告**：
   - 提供课件文件路径
   - Agent调用`parse_course_material`解析课件
   - Agent准备各章节内容
   - Agent调用`generate_report`生成Word文档
   - Agent调用`verify_format`验证格式

### 数据结构定义如何告知AI

AI不需要读代码。定义通过以下机制自动告知：
1. `analyze_template`返回中包含完整的TS接口定义（从Pydantic自动生成）
2. `save_profile`校验失败时返回错误+TS接口定义，帮助AI修正
3. 工具schema描述中包含关键字段说明
