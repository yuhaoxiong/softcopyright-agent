"""Command line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import SoftCopyrightAgent
from .models import RunConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成软件著作权设计说明书和源代码素材")
    parser.add_argument("title", help="软著标题，例如：基于深度学习的智能问答系统 V1.0")
    parser.add_argument("--output", default="outputs/generated", help="输出目录")
    parser.add_argument("--doc-words", type=int, default=9000, help="说明书目标字数")
    parser.add_argument("--code-lines", type=int, default=3000, help="源代码目标行数")
    parser.add_argument("--confirm-outline", action="store_true", help="目录生成后暂停确认")
    parser.add_argument("--no-docx", action="store_true", help="跳过 DOCX 输出")
    parser.add_argument("--llm-provider", default="auto", choices=["auto", "openai-compatible", "grok", "fallback"], help="大模型提供方")
    parser.add_argument("--llm-api-key", default=None, help="大模型 API Key；不传则读取环境变量")
    parser.add_argument("--llm-model", default=None, help="大模型名称，默认读取 SOFTCOPYRIGHT_LLM_MODEL 或 OPENAI_MODEL")
    parser.add_argument("--llm-base-url", default=None, help="OpenAI-compatible Chat Completions URL")
    parser.add_argument("--llm-required", action="store_true", help="未配置或调用失败时直接报错，不回退到本地生成")
    parser.add_argument("--aigc-rounds", type=int, default=1, help="AIGC 降重轮次（仅 LLM 模式有效），默认 1 轮")
    parser.add_argument("--interactive-review", action="store_true", help="在目录、说明书、代码阶段暂停，允许人工修改草稿")
    parser.add_argument("--review-dir", default=None, help="人工审查草稿目录")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = SoftCopyrightAgent().run(
        args.title,
        RunConfig(
            output_dir=Path(args.output),
            target_doc_words=args.doc_words,
            target_code_lines=args.code_lines,
            create_docx=not args.no_docx,
            confirm_outline=args.confirm_outline,
            llm_provider=args.llm_provider,
            llm_api_key=args.llm_api_key,
            llm_model=args.llm_model,
            llm_base_url=args.llm_base_url,
            llm_required=args.llm_required,
            aigc_rounds=args.aigc_rounds,
            interactive_review=args.interactive_review,
            review_dir=Path(args.review_dir) if args.review_dir else None,
        ),
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0
