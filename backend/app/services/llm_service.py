"""
LLM 服务层 — 支持 Anthropic Claude 和 DeepSeek (OpenAI 兼容)

为 Agent 提供统一的 LLM 调用接口：
- 文本响应：用于生成思考过程（thinking）
- JSON 响应：用于生成结构化输出（output）
- 自动重试 + 超时处理
- 多 Provider 支持（deepseek / anthropic）
"""
import json
import logging
import asyncio
import re
from typing import Any

import anthropic
from openai import AsyncOpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """多 Provider LLM 调用封装"""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.llm_provider  # "deepseek" or "anthropic"

        # Anthropic
        self.anthropic_api_key = settings.anthropic_api_key
        self.anthropic_model = settings.anthropic_model
        self.anthropic_base_url = settings.anthropic_base_url
        self._anthropic_client: anthropic.AsyncAnthropic | None = None

        # DeepSeek (OpenAI 兼容)
        self.deepseek_api_key = settings.deepseek_api_key
        self.deepseek_model = settings.deepseek_model
        self.deepseek_base_url = settings.deepseek_base_url
        self._openai_client: AsyncOpenAI | None = None

    @property
    def available(self) -> bool:
        """检查当前 Provider 的 LLM 是否可用"""
        if self.provider == "deepseek":
            return bool(self.deepseek_api_key)
        return bool(self.anthropic_api_key)

    @property
    def model(self) -> str:
        """当前使用的模型名称"""
        if self.provider == "deepseek":
            return self.deepseek_model
        return self.anthropic_model

    async def think(
        self,
        system_prompt: str,
        user_message: str,
        output_format: str = "text",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict:
        """
        调用 LLM 进行推理。

        Returns:
            {"success": True, "content": "...", "json": {...}} 或
            {"success": False, "error": "..."}
        """
        if not self.available:
            return {"success": False, "error": f"LLM Provider ({self.provider}) API key 未配置"}

        if self.provider == "deepseek":
            result = await self._call_deepseek(system_prompt, user_message, output_format, max_tokens, temperature)
        elif self.provider == "anthropic":
            result = await self._call_anthropic(system_prompt, user_message, output_format, max_tokens, temperature)
        else:
            return {"success": False, "error": f"未知 LLM Provider: {self.provider}"}

        # 尝试解析 JSON
        if result["success"] and output_format == "json":
            result["json"] = self._extract_json(result["content"])

        return result

    # === DeepSeek (OpenAI 兼容) ===

    async def _call_deepseek(
        self, system_prompt: str, user_message: str, output_format: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """调用 DeepSeek API"""
        client = self._get_openai_client()

        # 构建 messages
        messages = [{"role": "user", "content": user_message}]
        system = system_prompt

        if output_format == "json":
            system += "\n\n⚠️ 重要：你必须只输出有效的 JSON，不要包含任何 markdown 代码块标记。"

        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.deepseek_model,
                        messages=[
                            {"role": "system", "content": system},
                            *messages,
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    ),
                    timeout=120.0,
                )

                content = response.choices[0].message.content or ""
                usage = response.usage

                logger.info(
                    f"DeepSeek 调用成功: model={self.deepseek_model}, "
                    f"input_tokens={usage.prompt_tokens if usage else '?'}, "
                    f"output_tokens={usage.completion_tokens if usage else '?'}"
                )
                return {"success": True, "content": content}

            except asyncio.TimeoutError:
                logger.warning(f"DeepSeek 调用超时 (attempt {attempt + 1}/3)")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                continue
            except Exception as e:
                logger.error(f"DeepSeek API 错误: {e}")
                if attempt < 2:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "重试耗尽"}

    def _get_openai_client(self) -> AsyncOpenAI:
        """延迟初始化 OpenAI 客户端（用于 DeepSeek）"""
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_base_url,
            )
        return self._openai_client

    # === Anthropic Claude ===

    async def _call_anthropic(
        self, system_prompt: str, user_message: str, output_format: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """调用 Anthropic Claude API"""
        client = self._get_anthropic_client()
        messages = [{"role": "user", "content": user_message}]
        system = system_prompt

        if output_format == "json":
            system += "\n\n⚠️ 重要：你必须只输出有效的 JSON，不要包含任何其他文本、解释或 markdown 代码块。直接输出 JSON 对象。"

        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    client.messages.create(
                        model=self.anthropic_model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system,
                        messages=messages,
                    ),
                    timeout=120.0,
                )

                content = response.content[0].text
                logger.info(
                    f"Anthropic 调用成功: model={self.anthropic_model}, "
                    f"input_tokens={response.usage.input_tokens}, "
                    f"output_tokens={response.usage.output_tokens}"
                )
                return {"success": True, "content": content}

            except asyncio.TimeoutError:
                logger.warning(f"Anthropic 调用超时 (attempt {attempt + 1}/3)")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                continue
            except anthropic.APIError as e:
                logger.error(f"Anthropic API 错误: {e}")
                if "rate_limit" in str(e).lower() and attempt < 2:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                return {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(f"Anthropic 调用异常: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "重试耗尽"}

    def _get_anthropic_client(self) -> anthropic.AsyncAnthropic:
        """延迟初始化 Anthropic 客户端"""
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=self.anthropic_api_key,
                base_url=self.anthropic_base_url,
            )
        return self._anthropic_client

    # === 通用工具方法 ===

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 响应中提取 JSON 对象（增强容错）"""
        if not text:
            return None

        # 1. 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 从 markdown 代码块提取 ```json ... ``` 或 ``` ... ```
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. 提取第一个 { 到最后一个 } 之间的内容
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 4. 尝试修复被截断的 JSON（补齐缺失的括号）
                repaired = self._repair_truncated_json(json_str)
                if repaired:
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass

        # 5. 尝试找到 JSON 数组
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(f"无法从 LLM 响应中提取 JSON: {text[:200]}...")
        return None

    def _repair_truncated_json(self, text: str) -> str | None:
        """尝试修复被截断的 JSON"""
        # 统计未闭合的括号
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')

        if open_braces > 0 or open_brackets > 0:
            # 检查是否在字符串中间截断
            in_string = False
            for ch in text:
                if ch == '"' and (not text or text[-1] != '\\'):
                    in_string = not in_string
            if in_string:
                text += '"'

            # 补齐缺失的括号
            text += ']' * open_brackets
            text += '}' * open_braces
            return text

        return None


# 全局单例
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
