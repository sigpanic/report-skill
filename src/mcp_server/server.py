import asyncio
import json
import os
import re
import sys

if __name__ == "__main__":
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.protocol.schema import (
    ANALYZE_TEMPLATE_SCHEMA, GENERATE_REPORT_SCHEMA, GENERATE_SKILL_SCHEMA,
    PARSE_COURSE_SCHEMA, VERIFY_FORMAT_SCHEMA, SAVE_PROFILE_SCHEMA
)
from src.protocol.constants import _G, AGENT_FRAMEWORKS, KEY_ERROR_GENERAL, KEY_ERROR_SPECIALIZED
from src.template_parser.analyzer import analyze_template_compact, save_compact, get_analysis_guide, check_profile_completeness
from src.template_parser.course_parser import parse_course_material
from src.doc_generator.generator import generate_report
from src.doc_generator.verifier import verify_format
from src.skill_generator.generator import generate_skill
from src.protocol.profile_schema import validate_profile_pydantic, fix_profile_pydantic
from src.protocol.ts_generator import generate_all_ts_interfaces

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ENV_WHITELIST = {
    "STUDENT_ID": "student_id",
    "STUDENT_NAME": "student_name",
    "STUDENT_CLASS": "student_class",
}

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _get_env_info() -> str:
    parts = []
    for env_key, field_key in _ENV_WHITELIST.items():
        val = os.environ.get(env_key, "")
        if val:
            parts.append(f"{field_key}={val}")
    if parts:
        return ".env 已自动加载: " + ", ".join(parts)
    return ".env 文件不存在或无有效内容 — 个人信息需要询问用户"


def _auto_fill_from_env(field_values: dict) -> dict:
    filled = dict(field_values)
    for env_key, field_key in _ENV_WHITELIST.items():
        if field_key not in filled or not filled.get(field_key):
            env_val = os.environ.get(env_key, "")
            if env_val:
                filled[field_key] = env_val
    return filled

_skill_file_cache = None
_skill_file_cache_mtime = 0


def _wrap_skill_for_framework(content: str, skill_name: str, frontmatter_type: str) -> str:
    body = content
    if body.startswith("---"):
        end = body.find("---", 3)
        if end != -1:
            body = body[end + 3:].lstrip("\n")

    if frontmatter_type == "trae":
        return f"---\nname: \"{skill_name}\"\ndescription: \"Generate '{skill_name}' Word documents following template format strictly.\"\n---\n\n{body}"
    elif frontmatter_type == "claude":
        return f"---\ndescription: \"Generate '{skill_name}' Word documents following template format strictly.\"\nallowed-tools: [\"Read\", \"Write\", \"Bash\"]\n---\n\n{body}"
    elif frontmatter_type == "cursor":
        return f"---\ndescription: \"Generate '{skill_name}' Word documents following template format strictly.\"\nglobs: []\nalwaysApply: false\n---\n\n{body}"
    else:
        return body


def _iter_skill_files():
    for fw in AGENT_FRAMEWORKS:
        agent_dir = fw["dir"]
        skills_subdir = fw["subdir"]
        if fw.get("single_file"):
            single_file = os.path.join(PROJECT_ROOT, agent_dir, fw["filename"])
            if os.path.exists(single_file):
                yield single_file
            continue
        skills_base = os.path.join(PROJECT_ROOT, agent_dir, skills_subdir)
        if not os.path.exists(skills_base):
            continue
        if fw.get("nested"):
            for skill_dir_name in os.listdir(skills_base):
                skill_file = os.path.join(skills_base, skill_dir_name, fw["filename"])
                if os.path.exists(skill_file):
                    yield skill_file
        else:
            ext = fw.get("ext", ".md")
            for f_name in os.listdir(skills_base):
                if f_name.endswith(ext):
                    yield os.path.join(skills_base, f_name)


def _build_skill_content_cache():
    global _skill_file_cache, _skill_file_cache_mtime
    cache = {}
    for skill_file in _iter_skill_files():
        try:
            mtime = os.path.getmtime(skill_file)
            with open(skill_file, 'r', encoding='utf-8') as sf:
                cache[skill_file] = {"content": sf.read().upper(), "mtime": mtime}
        except Exception:
            pass
    _skill_file_cache = cache
    _skill_file_cache_mtime = 0
    return cache


def _get_skill_cache():
    global _skill_file_cache
    if _skill_file_cache is None:
        _skill_file_cache = _build_skill_content_cache()
    return _skill_file_cache


def _normalize_key(k: str) -> str:
    return re.sub(r'[\s\-]+', '', k.strip()).upper()


def _check_specialized_key(skill_key: str, category_dir: str = "") -> bool:
    key_norm = _normalize_key(skill_key)
    if not key_norm or len(key_norm) < 8:
        return False
    if key_norm == _normalize_key(_G):
        return False

    key_parts = key_norm.split("2026")
    if len(key_parts) < 2:
        return False
    suffix = key_parts[-1]

    if category_dir and os.path.isdir(category_dir):
        for f_name in os.listdir(category_dir):
            if f_name.endswith(".md") and f_name != "README.md":
                try:
                    with open(os.path.join(category_dir, f_name), 'r', encoding='utf-8') as sf:
                        content = sf.read()
                        content_norm = _normalize_key(content)
                        if suffix in content_norm and "RPT" in content_norm:
                            return True
                except Exception:
                    pass

    cache = _get_skill_cache()
    for skill_file, entry in cache.items():
        content = entry["content"]
        content_norm = _normalize_key(content)
        if suffix in content_norm and "RPT" in content_norm:
            return True

    return False


def _has_skill_in_category(category_dir: str) -> bool:
    if not os.path.isdir(category_dir):
        return False
    for f in os.listdir(category_dir):
        if f.endswith(".md") and f != "README.md":
            return True
    return False


def _has_skill_registered(template_path_val: str) -> bool:
    if not template_path_val:
        return False

    cache = _get_skill_cache()
    template_basename = os.path.basename(template_path_val)
    for skill_file, entry in cache.items():
        content = entry["content"]
        if template_basename.upper() in content or template_path_val.upper() in content:
            return True

    return False


def _get_category_dir(profile_path: str) -> str:
    profile_dir = os.path.dirname(os.path.abspath(profile_path))
    return os.path.dirname(profile_dir) if os.path.basename(profile_dir) == "parsed" else profile_dir


def _get_default_output_dir(template_path: str) -> str:
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
            if _normalize_key(arguments.get("skill_key", "")) != _normalize_key(_G):
                return [TextContent(type="text", text=KEY_ERROR_GENERAL)]

            compact = analyze_template_compact(arguments["template_path"])

            output_path = arguments.get("output_path")
            if not output_path:
                output_dir = _get_default_output_dir(arguments["template_path"])
                base_name = os.path.splitext(os.path.basename(arguments["template_path"]))[0]
                output_path = os.path.join(output_dir, f"{base_name}_compact.json")
            else:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            save_compact(compact, output_path)

            guide = get_analysis_guide()
            guide_path = os.path.splitext(output_path)[0] + "_guide.md"
            os.makedirs(os.path.dirname(os.path.abspath(guide_path)), exist_ok=True)
            with open(guide_path, 'w', encoding='utf-8') as f:
                f.write(guide)

            env_info = _get_env_info()
            # toagent: 此处必须保持中文，严禁改成英文
            result_text = f"""模板分析完成，数据已保存到文件。

## 文件路径
- compact原始数据: {output_path}
- 分析指导(含TS接口定义): {guide_path}

## ⚠️ 强制要求
1. **你必须读取上述两个文件的完整内容**，不能跳过或只读部分
2. compact数据是原始解析结果，不是TemplateProfile JSON
3. 你必须根据compact数据和TS接口定义，自己编写TemplateProfile JSON
4. 编写完成后调用save_profile保存（自动Pydantic校验+代码辅助检查+补全fields）
5. 如果save_profile返回警告，请检查是否需要修正
6. **不读取完整文件将导致Profile编写错误，Pydantic校验会拒绝执行**

{env_info}"""

            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"分析失败: {str(e)}")]

    elif name == "generate_report":
        try:
            skill_key = arguments.get("skill_key", "")
            profile_path = arguments["profile_path"]
            template_path_arg = arguments["template_path"]

            if not os.path.exists(template_path_arg):
                return [TextContent(type="text", text=f"❌ 模板文件不存在: {template_path_arg}")]

            if not os.path.exists(profile_path):
                return [TextContent(type="text", text=f"❌ Profile文件不存在: {profile_path}\n请先完成模板分析（analyze_template）和Profile保存（save_profile）。")]

            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            category_dir = _get_category_dir(profile_path)
            if not _check_specialized_key(skill_key, category_dir):
                return [TextContent(type="text", text=KEY_ERROR_SPECIALIZED)]

            validation = validate_profile_pydantic(profile)
            if not validation["valid"]:
                errors_str = "\n".join(f"  - {e}" for e in validation["errors"])
                return [TextContent(type="text", text=f"❌ Profile格式验证失败，请修正以下错误后再试：\n{errors_str}")]

            profile = fix_profile_pydantic(profile)

            profile_template = profile.get("template_path", "")
            if profile_template and os.path.abspath(profile_template) != os.path.abspath(template_path_arg):
                return [TextContent(type="text", text=f"❌ template_path参数({template_path_arg})与Profile中的template_path({profile_template})不一致，请确认使用正确的模板和Profile。")]

            if not _has_skill_in_category(category_dir) and not _has_skill_registered(profile.get("template_path", "")):
                return [TextContent(type="text", text=f"❌ 未找到对应的特化Skill。请先完成特化（调用generate_skill生成特化Skill），然后按Skill规定的工作流程生成报告。\n不要跳过Skill直接调用本工具。")]

            field_values = _auto_fill_from_env(arguments.get("field_values", {}))
            env_info = _get_env_info()
            # toagent: 此处必须保持中文，严禁改成英文
            output = generate_report(
                template_path=template_path_arg,
                output_path=arguments["output_path"],
                profile=profile,
                field_values=field_values,
                sections=arguments["sections"],
                result_images=arguments.get("result_images")
            )
            return [TextContent(type="text", text=f"报告已生成: {output}\n\n{env_info}")]
        except Exception as e:
            return [TextContent(type="text", text=f"生成失败: {str(e)}")]

    elif name == "generate_skill":
        try:
            if _normalize_key(arguments.get("skill_key", "")) != _normalize_key(_G):
                return [TextContent(type="text", text=KEY_ERROR_GENERAL)]

            profile_path = arguments["profile_path"]
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            validation = validate_profile_pydantic(profile)
            if not validation["valid"]:
                errors_str = "\n".join(f"  - {e}" for e in validation["errors"])
                return [TextContent(type="text", text=f"Profile格式验证失败，请先修正：\n{errors_str}")]

            profile = fix_profile_pydantic(profile)

            skill_name = arguments["skill_name"]
            if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$', skill_name):
                return [TextContent(type="text", text=f"❌ skill_name包含非法字符: {skill_name}。只允许字母、数字、下划线、连字符和中文。")]
            output_path = arguments["output_path"]

            if os.path.isdir(output_path):
                output_path = os.path.join(output_path, f"{skill_name}.md")

            output = generate_skill(
                profile=profile,
                skill_name=skill_name,
                output_path=output_path,
                constraints=arguments.get("constraints")
            )

            with open(output, 'r', encoding='utf-8') as sf:
                skill_content = sf.read()

            registered = []
            for fw in AGENT_FRAMEWORKS:
                agent_dir = fw["dir"]
                agent_root = os.path.join(PROJECT_ROOT, agent_dir)
                if not os.path.exists(agent_root):
                    continue

                fw_type = fw.get("frontmatter_type", "plain")
                fw_content = _wrap_skill_for_framework(skill_content, skill_name, fw_type)

                if fw.get("single_file"):
                    target_path = os.path.join(agent_root, fw["filename"])
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(fw_content)
                    registered.append(target_path)
                elif fw.get("nested"):
                    target_dir = os.path.join(agent_root, fw["subdir"], skill_name)
                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, fw["filename"])
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(fw_content)
                    registered.append(target_path)
                else:
                    target_dir = os.path.join(agent_root, fw["subdir"])
                    os.makedirs(target_dir, exist_ok=True)
                    target_filename = f"{skill_name}{fw['ext']}"
                    target_path = os.path.join(target_dir, target_filename)
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(fw_content)
                    registered.append(target_path)

            _build_skill_content_cache()

            env_info = _get_env_info()
            # toagent: 此处必须保持中文，严禁改成英文
            result = f"✅ 特化Skill已生成: {output}\n\n{env_info}\n"

            if registered:
                result += "\nSkill已自动注册到以下Agent目录：\n"
                for path in registered:
                    result += f"  - {path}\n"
            else:
                result += "\n⚠️ 未检测到任何Agent框架目录。Skill仅保存在类别目录下，请通知用户手动注册。\n"

            result += f"\n---\n## 特化Skill内容（请按此工作流程执行报告生成）\n\n{skill_content}\n\n---\n"
            result += "⚠️ 以上是特化Skill的完整内容。如果用户要求生成报告，请严格按照上述工作流程执行，不要跳过任何步骤。"

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"生成失败: {str(e)}")]

    elif name == "parse_course_material":
        try:
            skill_key = arguments.get("skill_key", "")
            if not _check_specialized_key(skill_key):
                return [TextContent(type="text", text=KEY_ERROR_SPECIALIZED)]

            result = parse_course_material(arguments["file_path"])
            if "error" in result and result.get("error"):
                return [TextContent(type="text", text=f"解析失败: {result['error']}")]

            output_path = arguments.get("output_path")
            if not output_path:
                course_dir = _get_course_output_dir(arguments["file_path"])
                base_name = os.path.splitext(os.path.basename(arguments["file_path"]))[0]
                output_path = os.path.join(course_dir, f"{base_name}_parsed.json")
            else:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

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
            summary += f"\n⚠️ **你必须读取文件获取完整内容**: {output_path}"

            return [TextContent(type="text", text=summary)]
        except Exception as e:
            return [TextContent(type="text", text=f"解析失败: {str(e)}")]

    elif name == "verify_format":
        try:
            skill_key = arguments.get("skill_key", "")
            if not _check_specialized_key(skill_key):
                return [TextContent(type="text", text=KEY_ERROR_SPECIALIZED)]

            profile = None
            profile_path = arguments.get("profile_path")
            if profile_path and os.path.exists(profile_path):
                with open(profile_path, 'r', encoding='utf-8') as f:
                    profile = json.load(f)

            result = verify_format(
                template_path=arguments["template_path"],
                generated_path=arguments["generated_path"],
                output_path=arguments.get("output_path"),
                profile=profile
            )

            if result["passed"]:
                msg = "格式验证通过! 所有格式与模板一致。"
            else:
                issues = "\n".join(f"- {issue}" for issue in result["issues"])
                msg = f"格式验证未通过，以下格式不一致:\n{issues}"

            req_warnings = result.get("requirement_warnings", [])
            if req_warnings:
                msg += "\n\n📋 Requirements代码辅助检查（仅供参考，由你决定是否修正）：\n"
                for w in req_warnings:
                    msg += f"  {w}\n"

            return [TextContent(type="text", text=msg)]
        except Exception as e:
            return [TextContent(type="text", text=f"验证失败: {str(e)}")]

    elif name == "save_profile":
        try:
            if _normalize_key(arguments.get("skill_key", "")) != _normalize_key(_G):
                return [TextContent(type="text", text=KEY_ERROR_GENERAL)]

            profile_data = arguments["profile_json"]
            output_path = arguments["output_path"]

            template_path_val = profile_data.get("template_path", "")
            if template_path_val and not os.path.exists(template_path_val):
                return [TextContent(type="text", text=f"❌ 模板文件不存在: {template_path_val}\n请先调用analyze_template分析模板，然后根据分析结果编写Profile。")]

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
