import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.protocol.schema import (
    ANALYZE_TEMPLATE_SCHEMA, GENERATE_REPORT_SCHEMA, GENERATE_SKILL_SCHEMA,
    PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA, SAVE_PROFILE_SCHEMA
)
from src.template_parser.analyzer import analyze_template_compact, save_profile, save_compact, get_analysis_guide, check_profile_completeness
from src.template_parser.course_parser import parse_course_material
from src.doc_generator.generator import generate_report
from src.doc_generator.verifier import verify_format
from src.skill_generator.generator import generate_skill
from src.protocol.profile_schema import validate_profile_pydantic, fix_profile_pydantic
from src.protocol.ts_generator import generate_all_ts_interfaces

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_default_output_dir(template_path: str) -> str:
    base_name = os.path.splitext(os.path.basename(template_path))[0]
    parent_dir = os.path.dirname(os.path.abspath(template_path))
    parsed_dir = os.path.join(parent_dir, "parsed")
    os.makedirs(parsed_dir, exist_ok=True)
    return parsed_dir


def _get_course_output_dir(course_path: str) -> str:
    return os.path.dirname(os.path.abspath(course_path))


server = Server("report-skill-generator")


@server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    for schema in [ANALYZE_TEMPLATE_SCHEMA, GENERATE_REPORT_SCHEMA, GENERATE_SKILL_SCHEMA,
                   PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA, SAVE_PROFILE_SCHEMA]:
        tool = Tool(
            name=schema["name"],
            description=schema["description"],
            inputSchema=schema["inputSchema"]
        )
        tools.append(tool)
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "analyze_template":
        try:
            compact = analyze_template_compact(arguments["template_path"])

            output_path = arguments.get("output_path")
            if not output_path:
                output_dir = _get_default_output_dir(arguments["template_path"])
                base_name = os.path.splitext(os.path.basename(arguments["template_path"]))[0]
                output_path = os.path.join(output_dir, f"{base_name}_compact.json")

            save_compact(compact, output_path)

            guide = get_analysis_guide()
            guide_path = output_path.replace(".json", "_guide.md")
            with open(guide_path, 'w', encoding='utf-8') as f:
                f.write(guide)

            result_text = f"""模板分析完成，数据已保存到文件。

## 文件路径
- compact原始数据: {output_path}
- 分析指导(含TS接口定义): {guide_path}

## ⚠️ 重要提示
1. 请读取上述两个文件获取完整数据
2. compact数据是原始解析结果，不是TemplateProfile JSON
3. 你必须根据compact数据和TS接口定义，自己编写TemplateProfile JSON
4. 编写完成后调用save_profile保存（自动Pydantic校验+代码辅助检查+补全fields）
5. 如果save_profile返回警告，请检查是否需要修正"""

            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"分析失败: {str(e)}")]

    elif name == "generate_report":
        try:
            profile_path = arguments["profile_path"]
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            validation = validate_profile_pydantic(profile)
            if not validation["valid"]:
                errors_str = "\n".join(f"  - {e}" for e in validation["errors"])
                return [TextContent(type="text", text=f"Profile格式验证失败，请修正以下错误后再试：\n{errors_str}")]

            profile = fix_profile_pydantic(profile)

            output = generate_report(
                template_path=arguments["template_path"],
                output_path=arguments["output_path"],
                profile=profile,
                field_values=arguments["field_values"],
                sections=arguments["sections"],
                result_images=arguments.get("result_images")
            )
            return [TextContent(type="text", text=f"报告已生成: {output}")]
        except Exception as e:
            return [TextContent(type="text", text=f"生成失败: {str(e)}")]

    elif name == "generate_skill":
        try:
            import shutil as shutil_mod

            profile_path = arguments["profile_path"]
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            validation = validate_profile_pydantic(profile)
            if not validation["valid"]:
                errors_str = "\n".join(f"  - {e}" for e in validation["errors"])
                return [TextContent(type="text", text=f"Profile格式验证失败，请先修正：\n{errors_str}")]

            profile = fix_profile_pydantic(profile)

            skill_name = arguments["skill_name"]
            output_path = arguments["output_path"]

            output = generate_skill(
                profile=profile,
                skill_name=skill_name,
                output_path=output_path,
                constraints=arguments.get("constraints")
            )

            agent_dirs = [
                (".trae", "skills"),
                (".claude", "skills"),
            ]
            search_roots = [PROJECT_ROOT, os.path.expanduser("~")]

            registered = []
            for root in search_roots:
                for agent_dir, skills_subdir in agent_dirs:
                    agent_root = os.path.join(root, agent_dir)
                    if os.path.exists(agent_root):
                        target_dir = os.path.join(agent_root, skills_subdir, skill_name)
                        os.makedirs(target_dir, exist_ok=True)
                        target_path = os.path.join(target_dir, "SKILL.md")
                        shutil_mod.copy2(output, target_path)
                        registered.append(target_path)

            result = f"Skill已生成: {output}\n"

            if registered:
                result += "\nSkill已自动注册到以下Agent目录：\n"
                for path in registered:
                    result += f"  - {path}\n"
            else:
                result += "\n⚠️ 未检测到任何Agent框架目录（.trae/、.claude/等）。"
                result += "Skill仅保存在类别目录下，请通知用户手动注册，或确保至少安装了一个支持Skill的Agent框架。\n"

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"生成失败: {str(e)}")]

    elif name == "parse_course_material":
        try:
            result = parse_course_material(arguments["file_path"])
            if "error" in result and result.get("error"):
                return [TextContent(type="text", text=f"解析失败: {result['error']}")]

            output_path = arguments.get("output_path")
            if not output_path:
                course_dir = _get_course_output_dir(arguments["file_path"])
                base_name = os.path.splitext(os.path.basename(arguments["file_path"]))[0]
                output_path = os.path.join(course_dir, f"{base_name}_parsed.json")

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            summary = f"课件解析完成，数据已保存到: {output_path}\n"
            summary += f"格式: {result.get('format', 'unknown')}\n"
            if "total_slides" in result:
                summary += f"幻灯片数: {result['total_slides']}\n"
            if "total_paragraphs" in result:
                summary += f"段落数: {result['total_paragraphs']}\n"
            if result.get("has_images"):
                summary += f"包含图片: 是\n"
            if result.get("image_note"):
                summary += f"\n⚠️ {result['image_note']}\n"
            summary += f"\n请读取文件获取完整内容: {output_path}"

            return [TextContent(type="text", text=summary)]
        except Exception as e:
            return [TextContent(type="text", text=f"解析失败: {str(e)}")]

    elif name == "verify_format":
        try:
            result = verify_format(
                template_path=arguments["template_path"],
                generated_path=arguments["generated_path"],
                output_path=arguments.get("output_path")
            )

            if result["passed"]:
                return [TextContent(type="text", text=f"格式验证通过! 所有格式与模板一致。")]
            else:
                issues = "\n".join(f"- {issue}" for issue in result["issues"])
                return [TextContent(type="text", text=f"格式验证未通过，以下格式不一致:\n{issues}")]
        except Exception as e:
            return [TextContent(type="text", text=f"验证失败: {str(e)}")]

    elif name == "save_profile":
        try:
            profile_data = arguments["profile_json"]
            output_path = arguments["output_path"]

            validation = validate_profile_pydantic(profile_data)
            if not validation["valid"]:
                errors_str = "\n".join(f"  - {e}" for e in validation["errors"])
                ts_ref = generate_all_ts_interfaces()
                return [TextContent(type="text", text=f"Profile格式验证失败，请修正以下错误：\n{errors_str}\n\n参考TypeScript接口定义：\n```typescript\n{ts_ref}\n```")]

            profile = fix_profile_pydantic(profile_data)

            template_path = profile.get("template_path", "")
            compact = None
            if template_path and os.path.exists(template_path):
                try:
                    compact = analyze_template_compact(template_path)
                except Exception:
                    pass

            warnings = []
            if compact:
                warnings = check_profile_completeness(profile, compact)

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)

            field_keys = [f.get("key", "") for f in profile.get("fields", [])]
            section_titles = [s.get("title", "") for s in profile.get("sections", [])]

            result = f"Profile已保存至: {output_path}\n字段: {json.dumps(field_keys, ensure_ascii=False)}\n章节: {json.dumps(section_titles, ensure_ascii=False)}"

            if warnings:
                result += "\n\n📋 代码辅助检查发现以下可能疏漏（仅供参考，由你决定是否修正）：\n"
                for w in warnings:
                    result += f"  {w}\n"

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"保存失败: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
