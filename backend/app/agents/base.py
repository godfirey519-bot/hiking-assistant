"""Agent 基类 — 所有专业 Agent 的父类

集成 Claude LLM：Agent 通过 system_prompt 引导 LLM 进行领域推理，
LLM 返回 JSON（含 thinking 和 output），自动解析为 AgentResult。
LLM 不可用时自动降级到规则逻辑。
"""
from dataclasses import dataclass, field
from typing import Any, Callable
from pydantic import BaseModel
import json
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Agent 执行结果"""
    agent_name: str
    success: bool
    output: dict | str
    thinking: str = ""
    error: str = ""
    duration_ms: float = 0


class Tool(BaseModel):
    """Agent 可用的工具定义"""
    name: str
    description: str
    parameters: dict = {}  # JSON Schema for parameters
    func: Callable | None = None  # 实际执行的函数

    class Config:
        arbitrary_types_allowed = True


class BaseAgent:
    """Agent 基类

    每个专业 Agent 继承此类，实现自己的 system_prompt 和业务方法。
    支持 LLM 驱动的思考链 (Chain of Thought) 和结构化输出。
    LLM 不可用时自动降级为规则逻辑。
    """

    name: str = "base"
    role: str = "planner"  # planner / reviewer / orchestrator / synthesizer
    description: str = "Base agent"
    tools: list[Tool] = []

    # LLM 配置 —— 子类可覆盖以控制速度和成本
    llm_max_tokens: int = 2048   # 输出 token 上限
    llm_temperature: float = 0.3  # 创造性（越低越快越确定）

    def __init__(self):
        self._tools_map = {t.name: t for t in self.tools}

    @property
    def system_prompt(self) -> str:
        """子类必须覆盖此属性，定义 Agent 的系统提示词"""
        raise NotImplementedError

    @property
    def output_schema_hint(self) -> str:
        """子类可覆盖，描述期望的输出 JSON 结构（嵌入 system_prompt 末尾）"""
        return ""

    def build_user_message(self, user_input: str, context: dict | None = None) -> str:
        """构建发送给 LLM 的用户消息"""
        parts = [f"## 用户需求\n{user_input}"]

        if context:
            # 只传递关键信息，避免 context 过大
            safe_context = {}
            for key, value in (context or {}).items():
                if isinstance(value, (dict, list, str, int, float, bool)):
                    safe_context[key] = value
            if safe_context:
                parts.append(
                    f"\n## 上下文信息\n```json\n{json.dumps(safe_context, ensure_ascii=False, indent=2)}\n```"
                )

        return "\n\n".join(parts)

    async def think(self, user_input: str, context: dict | None = None) -> AgentResult:
        """
        Agent 的思考/执行入口。

        优先使用 LLM 进行推理，LLM 不可用时降级为规则逻辑。
        子类可覆盖此方法实现自定义逻辑（如 RouteAnalyst 的 GPX 分析）。
        """
        start = time.time()
        logger.info(f"[{self.name}] 开始执行，输入: {user_input[:100]}...")

        try:
            # 尝试 LLM 推理
            llm_result = await self._try_llm_think(user_input, context)

            duration = (time.time() - start) * 1000
            logger.info(f"[{self.name}] {'LLM' if llm_result else '规则'}执行完成，耗时 {duration:.0f}ms")

            if llm_result:
                llm_result.duration_ms = duration
                return llm_result

            # LLM 不可用，降级为规则逻辑
            return await self._fallback_think(user_input, context, start)

        except Exception as e:
            logger.error(f"[{self.name}] 执行失败: {e}", exc_info=True)
            # 降级
            try:
                return await self._fallback_think(user_input, context, start)
            except Exception as fallback_error:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    output={},
                    thinking="",
                    error=str(fallback_error),
                    duration_ms=(time.time() - start) * 1000,
                )

    async def _try_llm_think(self, user_input: str, context: dict | None = None) -> AgentResult | None:
        """尝试使用 LLM 进行推理，失败返回 None"""
        from app.services.llm_service import get_llm_service

        llm = get_llm_service()
        if not llm.available:
            logger.info(f"[{self.name}] LLM 不可用，使用规则逻辑")
            return None

        # 构建完整 system_prompt（含输出格式要求）
        system = self._build_llm_system_prompt()

        # 构建用户消息
        user_message = self.build_user_message(user_input, context)

        # 调用 LLM（要求 JSON 输出）
        result = await llm.think(
            system_prompt=system,
            user_message=user_message,
            output_format="json",
            max_tokens=self.llm_max_tokens,
            temperature=self.llm_temperature,
        )

        if not result["success"] or result.get("json") is None:
            logger.warning(f"[{self.name}] LLM 调用失败: {result.get('error', 'JSON 解析失败')}")
            return None

        # 解析 LLM 返回的 JSON
        data = result["json"]
        thinking = data.get("thinking", result.get("content", ""))
        output = data.get("output", data)

        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            thinking=thinking,
        )

    async def _fallback_think(self, user_input: str, context: dict | None, start_time: float) -> AgentResult:
        """降级为规则逻辑"""
        thinking = self._generate_thinking(user_input, context)
        output = await self._execute_with_tools(user_input, context)
        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            thinking=thinking,
            duration_ms=(time.time() - start_time) * 1000,
        )

    def _build_llm_system_prompt(self) -> str:
        """构建完整的 LLM system prompt（含输出格式指令）"""
        parts = [self.system_prompt]

        # 通用 JSON 输出格式
        parts.append("""
## 输出格式要求

你必须以 JSON 格式输出，包含以下两个字段：

```json
{
  "thinking": "你的推理过程（详细说明你的分析步骤、考虑因素、决策依据）",
  "output": { ... 你的结构化输出结果 ... }
}
```

- `thinking`: 字符串，详细记录你的分析推理过程
- `output`: 对象，包含你的最终结构化结果
""")

        # 子类可添加特定的 output schema 提示
        if self.output_schema_hint:
            parts.append(f"\n### 期望的 output 结构\n{self.output_schema_hint}")

        return "\n".join(parts)

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        """生成思考过程文本（LLM 不可用时的降级逻辑）

        子类需覆盖此方法提供专业领域的推理逻辑。
        """
        return f"[{self.name}] 正在分析需求..."

    async def _execute_with_tools(self, user_input: str, context: dict | None = None) -> dict:
        """使用工具执行任务（LLM 不可用时的降级逻辑）

        子类需覆盖此方法提供结构化的规则输出。
        """
        return {"message": f"[{self.name}] 执行完成", "agent": self.name}

    def log(self, message: str):
        """记录 Agent 日志"""
        logger.info(f"[{self.name}] {message}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "tools": [t.name for t in self.tools],
        }
