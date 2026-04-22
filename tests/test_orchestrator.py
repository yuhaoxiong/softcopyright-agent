"""Tests for the ReAct orchestrator, memory, and tool registry."""

import json
import unittest

from softcopyright_agent.memory import AgentMemory, MemoryEntry
from softcopyright_agent.orchestrator import AgentState, ParsedAction, parse_action
from softcopyright_agent.tools.base import ToolResult
from softcopyright_agent.tools.registry import ToolRegistry, ToolSpec


# ── Memory Tests ─────────────────────────────────────────────────


class TestAgentMemory(unittest.TestCase):
    """Verify the working memory system."""

    def test_add_and_retrieve(self):
        mem = AgentMemory()
        mem.add("user", "生成软著材料")
        mem.add("thought", "先分析标题")
        self.assertEqual(len(mem.entries), 2)

    def test_get_context_includes_roles(self):
        mem = AgentMemory()
        mem.add("user", "测试目标")
        mem.add("action", "调用分析", tool_name="analyze_title")
        mem.add("observation", "分析完成")
        ctx = mem.get_context()
        self.assertIn("[用户目标]", ctx)
        self.assertIn("[动作: analyze_title]", ctx)
        self.assertIn("[观察结果]", ctx)

    def test_context_truncation(self):
        mem = AgentMemory(max_context_chars=100)
        mem.add("user", "A" * 200)
        ctx = mem.get_context()
        self.assertIn("省略", ctx)
        self.assertLessEqual(len(ctx), 200)  # truncated + prefix

    def test_get_tools_called(self):
        mem = AgentMemory()
        mem.add("action", "{}", tool_name="analyze_title")
        mem.add("observation", "done")
        mem.add("action", "{}", tool_name="generate_outline")
        self.assertEqual(mem.get_tools_called(), ["analyze_title", "generate_outline"])

    def test_execution_summary(self):
        mem = AgentMemory()
        mem.add("action", "{}", tool_name="analyze_title")
        mem.add("observation", "分析完成，发现6个模块")
        summary = mem.get_execution_summary()
        self.assertIn("1.", summary)
        self.assertIn("analyze_title", summary)

    def test_clear(self):
        mem = AgentMemory()
        mem.add("user", "test")
        mem.clear()
        self.assertEqual(len(mem.entries), 0)


# ── Tool Registry Tests ─────────────────────────────────────────


class TestToolRegistry(unittest.TestCase):
    """Verify tool registration, listing, and execution."""

    def _make_registry(self):
        reg = ToolRegistry()
        reg.register(ToolSpec(
            name="test_tool",
            description="A test tool",
            parameters={"param": "test parameter"},
            handler=lambda param="": ToolResult(
                success=True, data={"param": param}, observation=f"got {param}"
            ),
        ))
        return reg

    def test_register_and_get(self):
        reg = self._make_registry()
        self.assertIsNotNone(reg.get("test_tool"))
        self.assertIsNone(reg.get("nonexistent"))

    def test_list_names(self):
        reg = self._make_registry()
        self.assertEqual(reg.list_names(), ["test_tool"])

    def test_format_for_prompt(self):
        reg = self._make_registry()
        prompt = reg.format_for_prompt()
        self.assertIn("test_tool", prompt)
        self.assertIn("A test tool", prompt)

    def test_execute_success(self):
        reg = self._make_registry()
        result = reg.execute("test_tool", param="hello")
        self.assertTrue(result.success)
        self.assertEqual(result.data["param"], "hello")

    def test_execute_unknown_tool(self):
        reg = self._make_registry()
        result = reg.execute("unknown_tool")
        self.assertFalse(result.success)
        self.assertIn("不存在", result.observation)

    def test_execute_handles_exception(self):
        reg = ToolRegistry()
        reg.register(ToolSpec(
            name="bad_tool",
            description="Raises",
            parameters={},
            handler=lambda **_: 1 / 0,
        ))
        result = reg.execute("bad_tool")
        self.assertFalse(result.success)
        self.assertIn("失败", result.observation)


# ── Action Parsing Tests ─────────────────────────────────────────


class TestActionParsing(unittest.TestCase):
    """Verify robust parsing of LLM ReAct output."""

    def test_standard_format(self):
        response = """Thought: 我需要先分析标题
Action: analyze_title
Action Input: {"title": "智能系统V1.0"}"""
        action = parse_action(response)
        self.assertEqual(action.thought, "我需要先分析标题")
        self.assertEqual(action.tool_name, "analyze_title")
        self.assertEqual(action.tool_input["title"], "智能系统V1.0")

    def test_multiline_thought(self):
        response = """Thought: 第一行
第二行分析
Action: generate_outline
Action Input: {"target_words": 6000}"""
        action = parse_action(response)
        self.assertIn("第一行", action.thought)
        self.assertEqual(action.tool_name, "generate_outline")
        self.assertEqual(action.tool_input["target_words"], 6000)

    def test_missing_input(self):
        response = """Thought: 完成
Action: finish"""
        action = parse_action(response)
        self.assertEqual(action.tool_name, "finish")
        self.assertEqual(action.tool_input, {})

    def test_empty_response(self):
        action = parse_action("")
        self.assertEqual(action.tool_name, "")
        self.assertEqual(action.tool_input, {})

    def test_malformed_json(self):
        response = """Thought: test
Action: write_chapter
Action Input: {invalid json}"""
        action = parse_action(response)
        self.assertEqual(action.tool_name, "write_chapter")
        self.assertEqual(action.tool_input, {})

    def test_finish_action(self):
        response = """Thought: 所有材料已生成完毕
Action: finish
Action Input: {}"""
        action = parse_action(response)
        self.assertEqual(action.tool_name, "finish")


# ── AgentState Tests ─────────────────────────────────────────────


class TestAgentState(unittest.TestCase):
    """Verify shared state initialization."""

    def test_default_state(self):
        state = AgentState()
        self.assertIsNone(state.analysis)
        self.assertIsNone(state.outline)
        self.assertEqual(state.chapters, {})
        self.assertEqual(state.code_files, [])

    def test_state_mutation(self):
        state = AgentState(title="测试系统")
        state.chapters["chapter_1"] = "内容"
        self.assertEqual(state.chapters["chapter_1"], "内容")


# ── Integration: Orchestrator Tool Registration ──────────────────


class TestOrchestratorToolRegistration(unittest.TestCase):
    """Verify that all expected tools get registered."""

    def test_all_tools_registered(self):
        """Check that the orchestrator registers all 7 expected tools."""
        from softcopyright_agent.analyzer import TitleAnalyzer
        from softcopyright_agent.outline_generator import OutlineGenerator
        from softcopyright_agent.doc_writer import DocumentWriter
        from softcopyright_agent.code_generator import CodeGenerator
        from softcopyright_agent.aigc_reducer import AIGCReducer
        from softcopyright_agent.output_formatter import OutputFormatter
        from softcopyright_agent.prompt_engine import PromptEngine
        from softcopyright_agent.tools.quality_tool import ChapterQualityChecker
        from softcopyright_agent.models import RunConfig
        from softcopyright_agent.orchestrator import ReActOrchestrator

        # Use a stub LLM client
        class StubLLM:
            provider_name = "stub"
            def generate(self, **_): return ""

        orch = ReActOrchestrator(
            StubLLM(),
            analyzer=TitleAnalyzer(),
            outline_generator=OutlineGenerator(),
            doc_writer=DocumentWriter(),
            quality_checker=ChapterQualityChecker(),
            aigc_reducer=AIGCReducer(),
            code_generator=CodeGenerator(),
            output_formatter=OutputFormatter(),
            prompt_engine=PromptEngine(),
            config=RunConfig(),
        )
        expected = {
            "analyze_title", "generate_outline", "write_chapter",
            "check_quality", "reduce_chapter", "generate_all_code", "finish",
        }
        self.assertEqual(set(orch.registry.list_names()), expected)


if __name__ == "__main__":
    unittest.main()
