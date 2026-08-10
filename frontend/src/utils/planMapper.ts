// 把后端的 Plan sections（type + JSON content）映射成 PlanResult 需要的扁平结构
// 在 AgentChat 实时对话 和 PlanDetail 历史方案页 两处复用

export interface PlanResultShape {
  title: string
  overview: Record<string, any>
  route_analysis: Record<string, any>
  equipment: Record<string, any>
  safety: Record<string, any>
  weather: Record<string, any>
  meal: Record<string, any>
  schedule: any[]
  checklist: string[]
  agents_involved: string[]
}

export function mapPlanToResult(data: any): PlanResultShape {
  const plan: PlanResultShape = {
    title: data.title || '徒步方案',
    overview: {},
    route_analysis: {},
    equipment: {},
    safety: {},
    weather: {},
    meal: {},
    schedule: [],
    checklist: [],
    agents_involved: ['🗺️ 路线分析', '🌤️ 天气查询', '🎒 装备规划', '🧐 装备审核', '🍽️ 路餐推荐', '🛡️ 安全评估', '📝 AI 汇总'],
  }

  for (const section of data.sections || []) {
    try {
      const content = typeof section.content === 'string' ? JSON.parse(section.content) : section.content
      switch (section.type) {
        case 'route':
          plan.route_analysis = content
          plan.overview = {
            distance_km: content.distance_km || 0,
            elevation_gain_m: content.elevation_gain_m || 0,
            difficulty: content.difficulty || '未知',
            duration_days: content.duration_days || 1,
            max_elevation_m: content.max_elevation_m || 0,
          }
          break
        case 'equipment':
          plan.equipment = content
          break
        case 'safety':
          plan.safety = content
          break
        case 'weather':
          plan.weather = content
          break
        case 'meal':
          plan.meal = content
          break
        case 'schedule':
          plan.schedule = Array.isArray(content) ? content : [content]
          break
        case 'summary':
          // Synthesizer 的完整输出，用于 checklist 和 overview 增强
          if (content.checklist?.length) plan.checklist = content.checklist
          if (content.overview) plan.overview = { ...plan.overview, ...content.overview }
          break
      }
    } catch { /* 跳过解析失败的 section */ }
  }

  // 若 summary 未提供 checklist，从安全缓解措施/路线备注构建兜底
  if (!plan.checklist.length) {
    plan.checklist = plan.safety?.mitigations?.length
      ? plan.safety.mitigations.map((m: string) => `✅ ${m}`)
      : plan.route_analysis?.notes
        ? [plan.route_analysis.notes, '✅ 离线地图', '✅ 充电宝满电', '✅ 告知家人行程']
        : ['✅ 离线地图已下载', '✅ 充电宝充满电', '✅ 告知家人行程计划', '✅ 购买户外保险', '✅ 装备逐一检查']
  }

  return plan
}
