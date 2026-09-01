import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Calendar, Users, Loader2, Link2 } from 'lucide-react'
import api from '../services/api'
import PlanResult from '../components/agent/PlanResult'
import { mapPlanToResult } from '../utils/planMapper'

/** 公开分享页：免登录只读查看他人分享的徒步方案 */
export default function SharePage() {
  const { token } = useParams()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(`/share/plans/${token}`)
      .then(res => setData(res.data.plan))
      .catch(() => setError('分享链接不存在或已撤销'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24 text-gray-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> 加载分享方案...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Link2 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    )
  }
  if (!data) return null

  const plan = mapPlanToResult(data)
  const fmtDate = (s: string | null) => s ? new Date(s).toLocaleDateString('zh-CN') : '—'

  return (
    <div className="max-w-3xl mx-auto">
      {/* 分享横幅 */}
      <div className="bg-gradient-to-r from-primary/5 to-purple-500/5 border border-primary/20 rounded-xl px-5 py-3 mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link2 className="w-4 h-4 text-primary flex-shrink-0" />
        <span>来自徒步助手的分享方案（只读）</span>
      </div>

      {/* 标题 + 元信息 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h2 className="text-2xl font-bold text-gray-900 leading-snug">{data.title}</h2>
        <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-500">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4" /> {fmtDate(data.start_date)} ~ {fmtDate(data.end_date)}
          </span>
          <span className="flex items-center gap-1.5">
            <Users className="w-4 h-4" /> {data.participants || 1} 人
          </span>
          <span className="text-xs text-gray-400">
            创建于 {new Date(data.created_at).toLocaleString('zh-CN')}
          </span>
        </div>
      </div>

      {/* 方案 7 大区块 */}
      <PlanResult plan={plan} />

      <div className="mt-6 text-center text-xs text-gray-400 pb-8">
        —— 由 徒步助手 · AI Agent 徒步规划 生成 ——
      </div>
    </div>
  )
}
