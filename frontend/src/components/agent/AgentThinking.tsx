import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2, Brain } from 'lucide-react'

interface AgentLog {
  id: number
  agent_name: string
  role: string
  status: 'running' | 'completed' | 'failed'
  output: string
  thinking: string
}

const AGENT_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  Orchestrator: { icon: '🎯', color: 'border-purple-400 bg-purple-50', label: '主控协调' },
  RouteAnalyst: { icon: '🗺️', color: 'border-blue-400 bg-blue-50', label: '路线分析' },
  EquipmentPlanner: { icon: '🎒', color: 'border-green-400 bg-green-50', label: '装备规划' },
  EquipmentReviewer: { icon: '🧐', color: 'border-amber-400 bg-amber-50', label: '装备审核' },
  SafetyAssessor: { icon: '🛡️', color: 'border-red-400 bg-red-50', label: '安全评估' },
  Synthesizer: { icon: '📝', color: 'border-indigo-400 bg-indigo-50', label: '方案汇总' },
}

export default function AgentThinking({ log }: { log: AgentLog }) {
  const [expanded, setExpanded] = useState(false)
  const config = AGENT_CONFIG[log.agent_name] || { icon: '🤖', color: 'border-gray-300 bg-gray-50', label: log.agent_name }

  return (
    <div className={`border-l-4 rounded-lg p-4 mb-3 transition-all ${config.color}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">{log.agent_name}</span>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {config.label}
              </span>
            </div>
            <p className="text-xs text-gray-500">{log.role}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {log.status === 'running' && (
            <div className="flex items-center gap-1.5 text-blue-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-xs font-medium">思考中</span>
              <span className="flex gap-0.5">
                <span className="agent-thinking-dot w-1.5 h-1.5 bg-blue-500 rounded-full" />
                <span className="agent-thinking-dot w-1.5 h-1.5 bg-blue-500 rounded-full" />
                <span className="agent-thinking-dot w-1.5 h-1.5 bg-blue-500 rounded-full" />
              </span>
            </div>
          )}
          {log.status === 'completed' && (
            <div className="flex items-center gap-1 text-green-600">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-xs font-medium">完成</span>
            </div>
          )}
          {log.status === 'failed' && (
            <div className="flex items-center gap-1 text-red-600">
              <XCircle className="w-4 h-4" />
              <span className="text-xs font-medium">失败</span>
            </div>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 hover:bg-white/60 rounded transition-colors"
          >
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* 展开的思考过程 */}
      {expanded && (
        <div className="mt-3 space-y-2">
          {log.thinking && (
            <div>
              <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1">
                <Brain className="w-3.5 h-3.5" />
                思考过程
              </div>
              <pre className="text-xs text-gray-700 bg-white/70 rounded-lg p-3 whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto">
                {log.thinking}
              </pre>
            </div>
          )}

          {log.output && (
            <div>
              <div className="text-xs text-gray-500 mb-1">输出结果</div>
              <pre className="text-xs text-gray-700 bg-white/70 rounded-lg p-3 whitespace-pre-wrap font-mono max-h-64 overflow-y-auto">
                {typeof log.output === 'string' ? log.output : JSON.stringify(log.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
