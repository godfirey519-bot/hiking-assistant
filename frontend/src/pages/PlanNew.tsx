import { useSearchParams } from 'react-router-dom'
import AgentChat from '../components/agent/AgentChat'

export default function PlanNew() {
  const [searchParams] = useSearchParams()
  const routeName = searchParams.get('route') || ''
  const quickInput = searchParams.get('q') || ''

  const initialInput = quickInput || (routeName ? `走${routeName}，帮我规划装备和安全` : '')

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">新建徒步规划</h2>
      <p className="text-sm text-gray-500 mb-4">
        🤖 描述你的徒步计划，AI Agent 团队将协作分析路线、推荐装备、评估安全并生成完整方案
      </p>
      <div className="flex-1 min-h-0">
        <AgentChat initialInput={initialInput} />
      </div>
    </div>
  )
}
