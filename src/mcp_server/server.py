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
    PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA
)
from src.template_parser.analyzer import analyze_template, save_profile
from src.template_parser.course_parser import parse_course_material
from src.doc_generator.generator import generate_report
from src.doc_generator.verifier import verify_format
from src.skill_generator.generator import generate_skill

server = Server("report-skill-generator")


@server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    for schema in [ANALYZE_TEMPLATE_SCHEMA, GENERATE_REPORT_SCHEMA, GENERATE_SKILL_SCHEMA,
                   PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA]:
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
            profile = analyze_template(arguments["template_path"])

            output_path = arguments.get("output_path")
            if output_path:
                save_profile(profile, output_path)
                return [TextContent(type="text", text=f"模板分析完成，Profile已保存至: {output_path}\n\n字段列表: {json.dumps([f['key'] for f in profile.get('fields', [])], ensure_ascii=False)}\n章节列表: {json.dumps([s['title'] for s in profile.get('sections', [])], ensure_ascii=False)}")]

            profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
            return [TextContent(type="text", text=f"模板分析完成:\n{profile_json[:3000]}")]
        except Exception as e:
            return [TextContent(type="text", text=f"分析失败: {str(e)}")]

    elif name == "generate_report":
        try:
            profile_path = arguments["profile_path"]
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

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
            profile_path = arguments["profile_path"]
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            output = generate_skill(
                profile=profile,
                skill_name=arguments["skill_name"],
                output_path=arguments["output_path"],
                constraints=arguments.get("constraints")
            )
            return [TextContent(type="text", text=f"Skill已生成: {output}")]
        except Exception as e:
            return [TextContent(type="text", text=f"生成失败: {str(e)}")]

    elif name == "parse_course_material":
        try:
            result = parse_course_material(arguments["file_path"])
            if "error" in result and result.get("error"):
                return [TextContent(type="text", text=f"解析失败: {result['error']}")]

            output_path = arguments.get("output_path")
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

            summary = f"课件解析完成\n格式: {result.get('format', 'unknown')}\n"
            if "total_slides" in result:
                summary += f"幻灯片数: {result['total_slides']}\n"
            if "total_paragraphs" in result:
                summary += f"段落数: {result['total_paragraphs']}\n"
            if result.get("has_images"):
                summary += f"包含图片: 是\n"
            if result.get("image_note"):
                summary += f"\n⚠️ {result['image_note']}\n"
            summary += f"\n内容预览:\n{result.get('full_text', '')[:2000]}"

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

    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
