"""
通用对话 API — 让 AI 助手既能像普通 AI 一样回答任何问题，
又能在徒步/户外话题上提供专业建议，并引导用户生成完整方案。
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/chat", tags=["对话"])
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    reply: str


def _route_kb_context() -> str:
    """从路线知识库生成紧凑的路线列表，供 AI 推荐路线时参考"""
    from app.agents.route_analyst import KNOWN_ROUTES
    lines = []
    for name, r in KNOWN_ROUTES.items():
        lines.append(
            f"- {name}：{r.get('distance_km', '?')}km/{r.get('duration_days', '?')}天，"
            f"{r.get('difficulty', '?')}，最高{r.get('max_elevation_m', '?')}m，"
            f"最佳{r.get('best_season', '?')}，起点{r.get('trailhead', '?')}"
        )
    return "\n".join(lines)


SYSTEM_PROMPT = """你是「徒步助手」的智能 AI 助手——一个专业、友好、亲切的户外徒步顾问。用简体中文回答，使用 Markdown 格式。

# 核心能力
你能像普通 AI 助手（如 ChatGPT）一样回答任何问题：闲聊、知识问答、生活建议、编程、学习辅导等都可以正常、自然地回答。

# 徒步 / 户外专业能力
当话题涉及徒步、登山、露营、户外运动时，你会切换为专业顾问：
- 推荐路线时，优先参考下面【知识库路线】里的真实路线，也可补充你了解的知名路线
- 装备、安全、天气、路餐、体能、高原反应、导航等话题给出专业、实用、可操作的建议
- 回答组织清晰：用标题 / 列表 / 加粗，控制篇幅，别啰嗦

# 引导用户生成完整方案（重要）
当用户表达想要「徒步方案 / 攻略 / 完整规划」时：
1. 如果用户已给出路线 + 天数，直接告诉用户：回复「帮我规划」或「生成方案」，AI 会为你生成包含路线/装备/安全/天气/路餐/日程的完整徒步方案
2. 如果信息不足，用一句话问清楚关键信息：路线？天数？出发日期？人数？经验水平？——不要一次问太多
3. 不要假装已经生成了完整方案，要明确引导到规划功能

# 知识库路线（推荐时优先参考）
{route_context}

# 回答风格
- 适当用 emoji 增加亲切感，但别太多
- 列表/要点比大段文字更易读
- 回答自然结束，不必每次追问"""


def _build_user_message(message: str, history: list[ChatMessage] | None) -> str:
    """把对话历史并入当前问题（LLM 服务只支持单条 user message）"""
    if not history:
        return message
    turns = []
    for m in history[-6:]:
        who = "用户" if m.role == "user" else "助手"
        turns.append(f"{who}: {m.content}")
    turns.append(f"用户: {message}")
    return (
        "以下是对话历史：\n" + "\n".join(turns) +
        "\n\n请基于以上对话历史，直接回答「用户」的最新问题。"
    )


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通用对话 — 回答任意问题，并在徒步话题上提供专业建议"""
    if not data.message.strip():
        raise HTTPException(400, "消息不能为空")

    system = SYSTEM_PROMPT.format(route_context=_route_kb_context())
    llm = get_llm_service()

    result = await llm.think(
        system_prompt=system,
        user_message=_build_user_message(data.message.strip(), data.history),
        max_tokens=2048,
        temperature=0.7,
    )

    if not result.get("success"):
        # LLM 不可用或出错时，给出兜底回复而不是让用户看到报错
        logger.warning(f"通用对话失败: {result.get('error')}")
        return ChatResponse(
            reply="抱歉，我暂时无法回复。请检查后端 LLM API Key 配置，或稍后再试。"
        )

    return ChatResponse(reply=result["content"].strip())
