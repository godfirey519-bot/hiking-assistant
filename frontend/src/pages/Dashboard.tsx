import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Sparkles, Send, Map, Backpack, Footprints, ClipboardList, ChevronRight,
  Mountain, ArrowRight,
} from 'lucide-react'
import api from '../services/api'

interface RecentPlan {
  id: number
  title: string
  status: string
  created_at: string | null
}

interface Stats {
  kb_routes: number
  user_routes: number
  gear_items: number
  trips: number
  plans: number
  recent_plans: RecentPlan[]
}

const QUICK_HINTS = [
  '国庆走武功山穿越线，2天1夜，新手',
  '雨崩3天徒步需要什么装备？',
  '虎跳峡高路周末两天怎么走',
  '10月适合去哪里徒步？推荐几条',
]

const PLAN_STATUS: Record<string, { label: string; cls: string }> = {
  completed: { label: '已完成', cls: 'bg-green-100 text-green-700' },
  running: { label: '进行中', cls: 'bg-blue-100 text-blue-700' },
  processing: { label: '进行中', cls: 'bg-blue-100 text-blue-700' },
  pending: { label: '待开始', cls: 'bg-amber-100 text-amber-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const sameYear = d.getFullYear() === now.getFullYear()
  return d.toLocaleDateString('zh-CN', {
    month: 'numeric', day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
  }) + ' ' + d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get('/stats/')
      setStats(res.data)
    } catch {
      // 未登录或接口异常：保留空状态，登录后自动刷新
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchStats() }, [fetchStats])

  const startPlanning = (text: string) => {
    const q = text.trim()
    if (!q) return
    navigate(`/plans/new?q=${encodeURIComponent(q)}`)
  }

  const cards = stats ? [
    { label: '知识库路线', value: stats.kb_routes, icon: Mountain, tint: 'bg-emerald-50 text-emerald-600', note: '全国热门路线' },
    { label: '我的路线', value: stats.user_routes, icon: Map, tint: 'bg-blue-50 text-blue-600', note: '含 GPX 上传' },
    { label: '装备数量', value: stats.gear_items, icon: Backpack, tint: 'bg-amber-50 text-amber-600', note: '13 类装备' },
    { label: '徒步记录', value: stats.trips, icon: Footprints, tint: 'bg-purple-50 text-purple-600', note: '行程回忆' },
    { label: '规划方案', value: stats.plans, icon: ClipboardList, tint: 'bg-sky-50 text-sky-600', note: 'Agent 生成' },
  ] : []

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* ===== Hero：一句话开始规划 ===== */}
      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-600 via-emerald-500 to-teal-500 rounded-2xl p-6 md:p-10 shadow-lg">
        {/* 装饰圆点 */}
        <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full bg-white/10" aria-hidden />
        <div className="absolute -bottom-24 -left-10 w-72 h-72 rounded-full bg-white/5" aria-hidden />
        <div className="absolute top-10 right-24 w-3 h-3 rounded-full bg-white/40" aria-hidden />
        <div className="absolute bottom-16 right-40 w-2 h-2 rounded-full bg-white/30" aria-hidden />

        <div className="relative">
          <div className="flex items-center gap-2 text-emerald-50/90 text-sm font-medium">
            <Sparkles className="w-4 h-4" />
            6 个 AI Agent 协作 · 路线 / 装备 / 天气 / 路餐 / 安全 / 日程
          </div>
          <h1 className="text-2xl md:text-4xl font-bold text-white mt-3 leading-snug">
            一句话，生成你的完整徒步方案
          </h1>
          <p className="text-emerald-50/90 text-sm md:text-base mt-2">
            描述目的地、天数、经验，Agent 团队自动分工，几分钟出完整规划
          </p>

          {/* 输入框 */}
          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault()
                    startPlanning(input)
                  }
                }}
                placeholder="例如：十一去武功山徒步 2 天 1 夜，新手，求路线和装备"
                rows={2}
                className="w-full px-4 py-3 bg-white/95 backdrop-blur rounded-xl text-gray-800 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-white/60 resize-none"
              />
            </div>
            <button
              onClick={() => startPlanning(input)}
              disabled={!input.trim()}
              className="shrink-0 px-6 py-3 bg-white text-emerald-700 font-semibold rounded-xl hover:bg-emerald-50 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              开始规划 <Send className="w-4 h-4" />
            </button>
          </div>

          {/* 快捷提示 */}
          <div className="mt-4 flex flex-wrap gap-2">
            {QUICK_HINTS.map((hint) => (
              <button
                key={hint}
                onClick={() => startPlanning(hint)}
                className="px-3 py-1.5 text-xs bg-white/15 hover:bg-white/25 text-white rounded-full transition-colors"
              >
                {hint}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ===== 统计卡片 ===== */}
      <section>
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
                <div className="h-4 w-16 bg-gray-200 rounded" />
                <div className="h-8 w-10 bg-gray-200 rounded mt-3" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {cards.map((c) => (
              <div
                key={c.label}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all"
              >
                <div className={`w-10 h-10 rounded-lg ${c.tint} flex items-center justify-center`}>
                  <c.icon className="w-5 h-5" />
                </div>
                <p className="text-3xl font-bold text-gray-900 mt-3">{c.value}</p>
                <p className="text-sm text-gray-500 mt-0.5">{c.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{c.note}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ===== 最近的规划 ===== */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">最近的规划</h2>
          <Link to="/plans" className="flex items-center gap-1 text-sm text-primary hover:text-primary-dark transition-colors">
            查看全部 <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="p-6 space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : stats && stats.recent_plans.length > 0 ? (
            <ul className="divide-y divide-gray-100">
              {stats.recent_plans.map((p) => {
                const st = PLAN_STATUS[p.status] || { label: p.status, cls: 'bg-gray-100 text-gray-600' }
                return (
                  <li key={p.id}>
                    <Link
                      to={`/plans/${p.id}`}
                      className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{p.title}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{formatDate(p.created_at)}</p>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${st.cls}`}>
                        {st.label}
                      </span>
                      <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
                    </Link>
                  </li>
                )
              })}
            </ul>
          ) : (
            <div className="text-center py-12">
              <Sparkles className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500">还没有徒步规划</p>
              <p className="text-sm text-gray-400 mt-1 mb-4">从上面输入一句话，看看 AI Agent 能生成什么</p>
              <button
                onClick={() => navigate('/plans/new')}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
              >
                去新建规划 <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
