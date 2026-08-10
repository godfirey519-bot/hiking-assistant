import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Calendar, Users, Map, Trash2, Loader2, PlusCircle } from 'lucide-react'
import api from '../services/api'

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  processing: { label: '生成中', cls: 'bg-blue-100 text-blue-700' },
  completed: { label: '已完成', cls: 'bg-green-100 text-green-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
}

export default function PlanHistory() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    api.get('/plans/')
      .then(res => setPlans(res.data || []))
      .catch(() => setPlans([]))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('确定删除该规划方案？')) return
    try {
      await api.delete(`/plans/${id}`)
      load()
    } catch { /* ignore */ }
  }

  const fmtDate = (s: string | null) => s ? new Date(s).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) : '—'

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">历史规划</h2>
          <p className="text-sm text-gray-500 mt-1">查看和管理你的全部徒步方案</p>
        </div>
        <button
          onClick={() => navigate('/plans/new')}
          className="flex items-center gap-1.5 px-4 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
        >
          <PlusCircle className="w-4 h-4" /> 新建规划
        </button>
      </div>

      {loading && (
        <div className="flex justify-center items-center py-20 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin mr-2" /> 加载中...
        </div>
      )}

      {!loading && plans.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
          <Map className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 mb-2">还没有徒步规划方案</p>
          <p className="text-sm text-gray-400 mb-6">在 AI 对话中描述你的徒步计划，即可生成完整方案</p>
          <button
            onClick={() => navigate('/plans/new')}
            className="px-4 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
          >
            开始规划
          </button>
        </div>
      )}

      <div className="space-y-3">
        {plans.map(p => {
          const st = STATUS_MAP[p.status] || { label: p.status, cls: 'bg-gray-100 text-gray-600' }
          return (
            <Link
              key={p.id}
              to={`/plans/${p.id}`}
              className="group bg-white rounded-xl border border-gray-200 hover:border-primary/40 hover:shadow-sm transition-all p-5 flex items-start justify-between gap-3"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                  <h3 className="font-semibold text-gray-900 truncate">{p.title}</h3>
                  <span className={`flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
                </div>
                <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {fmtDate(p.start_date)} ~ {fmtDate(p.end_date)}</span>
                  <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {p.participants || 1}人</span>
                  <span>{new Date(p.created_at).toLocaleDateString('zh-CN')}</span>
                </div>
              </div>
              <button
                onClick={(e) => handleDelete(e, p.id)}
                className="p-2 -m-2 text-gray-300 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 hover:text-red-500 rounded-lg transition-colors flex-shrink-0"
                title="删除方案"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
