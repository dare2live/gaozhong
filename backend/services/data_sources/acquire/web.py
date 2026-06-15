"""通用 web 获取层 (crawl4ai, 驱动**本机 Chrome**) — lazy import, 优雅降级.

浏览器策略 (用户 2026-06-15: "本机开 chrome 效果更好, 不要装 chromium"):
- crawl4ai/playwright 默认会下载并用 bundled chromium; 本模块改用
  `channel="chrome"` → 直接驱动 **本机已装的 Google Chrome** (/Applications/Google Chrome.app),
  不依赖 bundled chromium. 见 GAOZHONG_CHROME_CHANNEL / GAOZHONG_CHROME_HEADLESS 环境变量。
- 需要导航/登陆/强反爬的官方站 (如 jyt.ln.gov.cn 辽宁教育厅) → 升级走 **Chrome MCP**
  (`mcp__Claude_in_Chrome__*`, agent 驱动真实运行的 Chrome, 已实证可达); 本模块是
  programmatic/批量切片, MCP 是 agent-interactive 切片, 二者互补 (见 docs/architecture.md 数据获取层)。

设计 (遵 CLAUDE.md §1.5 "失败先承认, 不静默吃错误"):
- crawl4ai 用 **lazy import** (import 写在函数内, 不在模块顶层).
  → 即使 crawl4ai 没装好 / 没装, 本模块仍能被 `import` 成功,
    其它代码路径不受影响; 只有真正 fetch 时才需要 crawl4ai.
- crawl4ai 不可用时, fetch_* 返回 {success: False, error: ...} 而非抛栈,
  明确 error 字段 (不静默), 但调用方不崩.

公开 API:
- is_available() -> bool
- fetch_url(url, *, timeout=30) -> dict
- fetch_official_source(url) -> dict  (附 lineage/timestamp, 供官方源取证)
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
from datetime import datetime, timezone
from typing import Any

_NOT_INSTALLED_ERROR = "crawl4ai not installed"

# 本机 Chrome channel: playwright 的 channel 名 ("chrome"=系统 Google Chrome stable).
# 可经环境变量覆盖 (如 "chrome-beta"/"msedge"); 空串 → 回退 bundled chromium (不推荐).
_CHROME_CHANNEL = os.environ.get("GAOZHONG_CHROME_CHANNEL", "chrome")
# headless 默认 True (批量无界面); 设 GAOZHONG_CHROME_HEADLESS=0 → 有头 (调试/弱反爬时更像真人).
_CHROME_HEADLESS = os.environ.get("GAOZHONG_CHROME_HEADLESS", "1") != "0"


def _now_iso() -> str:
    """UTC ISO 时间戳 (秒精度), 与 fetcher.py 对齐."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_available() -> bool:
    """crawl4ai 是否可用 (不触发实际 import, 只查 spec)."""
    try:
        return importlib.util.find_spec("crawl4ai") is not None
    except (ImportError, ValueError):
        return False


def _unavailable_result(url: str) -> dict[str, Any]:
    """统一的"crawl4ai 不可用"降级返回体."""
    return {
        "url": url,
        "success": False,
        "markdown": None,
        "html": None,
        "status_code": None,
        "error": _NOT_INSTALLED_ERROR,
    }


def _error_result(url: str, error: str) -> dict[str, Any]:
    """抓取过程出错的返回体 (明确 error, 不抛栈)."""
    return {
        "url": url,
        "success": False,
        "markdown": None,
        "html": None,
        "status_code": None,
        "error": error,
    }


def _browser_config():
    """构建本机 Chrome 的 BrowserConfig (channel='chrome'); channel 为空则回退 chromium."""
    from crawl4ai import BrowserConfig  # lazy

    kwargs: dict[str, Any] = {"headless": _CHROME_HEADLESS, "browser_type": "chromium"}
    if _CHROME_CHANNEL:
        # crawl4ai 0.8.x 启动实际读 chrome_channel (browser_manager.py:1115 → playwright launch
        # browser_args['channel']); channel 仅入 dump 不入 launch. 两个都传, 兼容新旧版本.
        kwargs["chrome_channel"] = _CHROME_CHANNEL
        kwargs["channel"] = _CHROME_CHANNEL  # → 本机 Google Chrome, 不碰 bundled chromium
    return BrowserConfig(**kwargs)


async def _arun(url: str, timeout: int) -> dict[str, Any]:
    """实际异步抓取 — crawl4ai 在此 lazy import, 驱动本机 Chrome (channel='chrome')."""
    from crawl4ai import AsyncWebCrawler  # lazy: 仅 fetch 时才需要

    async with AsyncWebCrawler(config=_browser_config()) as crawler:
        result = await crawler.arun(url=url, page_timeout=timeout * 1000)

    markdown = getattr(result, "markdown", None)
    # crawl4ai 0.8.x markdown 可能是 MarkdownGenerationResult, 取 raw 文本.
    if markdown is not None and not isinstance(markdown, str):
        markdown = getattr(markdown, "raw_markdown", None) or str(markdown)

    return {
        "url": url,
        "success": bool(getattr(result, "success", False)),
        "markdown": markdown,
        "html": getattr(result, "html", None),
        "status_code": getattr(result, "status_code", None),
        "error": getattr(result, "error_message", None) or None,
    }


def fetch_url(url: str, *, timeout: int = 30) -> dict[str, Any]:
    """用 crawl4ai 抓 url (同步接口, 内部 asyncio.run 包异步).

    返回: {url, success, markdown, html, status_code[, error]}
    crawl4ai 不可用 → {success: False, error: 'crawl4ai not installed'} (不崩).
    抓取出错 → {success: False, error: <异常文本>} (不抛栈, 明确 error).
    """
    if not is_available():
        return _unavailable_result(url)
    try:
        return asyncio.run(_arun(url, timeout))
    except Exception as exc:  # 优雅降级: 网络/解析/超时等都落到 error 字段
        return _error_result(url, f"{type(exc).__name__}: {exc}")


def fetch_official_source(url: str) -> dict[str, Any]:
    """fetch_url 封装, 附 lineage/timestamp 占位, 供官方源取证.

    用于辽宁省教育厅 (jyt.ln.gov.cn) 类官方源: 在抓取结果上挂
    source_url / fetched_at / source_tier 元数据, 便于后续 manifest 倒查
    (sha256/URL lineage 由上层 manifest 工具补全, 此处只占位 lineage).
    """
    result = fetch_url(url)
    result["lineage"] = {
        "source_url": url,
        "fetched_at": _now_iso(),
        "source_tier": "official",  # CLAUDE.md §3.2: Truth(S)/High(A) 官方源
        "fetcher": "backend.services.data_sources.acquire.web.fetch_official_source",
    }
    return result
