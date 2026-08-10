// 判断用户消息应触发「完整规划工作流」还是「通用对话」
//
// 规则：用户必须表达了明确的规划意图（规划/方案/生成/制定等动词）
// 且带有具体上下文（天数 或 徒步/路线/装备/攻略等关键词），才走完整规划。
// 其余情况（闲聊、提问、"推荐路线"、装备咨询等）走通用对话 —— AI 直接回答，
// 并在徒步话题上引导用户生成方案。

const PLAN_VERBS = ['规划', '方案', '生成', '制定', '做一份', '安排', '做一份', '出个']
const HIKE_CONTEXT = ['徒步', '路线', '爬山', '登山', '露营', '穿越', '装备', '攻略', '行程', '旅行', '出游']

export function shouldPlan(message: string): boolean {
  const hasVerb = PLAN_VERBS.some(k => message.includes(k))
  const hasDays = /\d+\s*天/.test(message)
  const hasHike = HIKE_CONTEXT.some(k => message.includes(k))
  return hasVerb && (hasDays || hasHike)
}
