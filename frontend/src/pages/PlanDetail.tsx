import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Trash2, ChevronDown, ChevronRight, Calendar, Users, Loader2, Share2, Check } from 'lucide-react'
import api from '../services/api'
import PlanResult from '../components/agent/PlanResult'
import { mapPlanToResult } from '../utils/planMapper'

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  processing: { label: '生成中', cls: 'bg-blue-100 text-blue-700' },
  completed: { label: '已完成', cls: 'bg-green-100 text-green-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
}

export default function PlanDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showLogs, setShowLogs] = useState(false)
  const [shareUrl, setShareUrl] = useState('')
  const [shareLoading, setShareLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = () => {
    setLoading(true)
    api.get(`/plans/${id}`)
      .then(res => setData(res.data))
      .catch(() => setError('方案不存在或加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [id])

  const handleDelete = async () => {
    if (!confirm('确定删除该规划方案？')) return
    try {
      await api.delete(`/plans/${id}`)
      navigate('/plans')
    } catch { /* ignore */ }
  }

  const handleShare = async () => {
    setShareLoading(true)
    try {
      const res = await api.post(`/share/plans/${id}`)
      setShareUrl(`${window.location.origin}${res.data.url}`)
    } catch (err: any) {
      alert(err.response?.data?.detail || '生成分享链接失败')
    } finally {
      setShareLoading(false)
    }
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard unavailable */ }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24 text-gray-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> 加载方案...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <Link to="/plans" className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mb-6">
          <ArrowLeft className="w-4 h-4" /> 返回历史规划
        </Link>
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">{error}</div>
      </div>
    )
  }
  if (!data) return null

  const plan = mapPlanToResult(data)
  const status = STATUS_MAP[data.status] || { label: data.status, cls: 'bg-gray-100 text-gray-600' }
  const fmtDate = (s: string | null) => s ? new Date(s).toLocaleDateString('zh-CN') : '—'

  return (
    <div className="max-w-3xl mx-auto">
      {/* 返回 + 操作 */}
      <div className="flex items-center justify-between mb-4">
        <Link to="/plans" className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
          <ArrowLeft className="w-4 h-4" /> 历史规划
        </Link>
        <div className="flex items-center gap-1">
          <button
            onClick={handleShare}
            disabled={shareLoading || data.status !== 'completed'}
            className="flex items-center gap-1.5 text-sm text-primary hover:bg-primary/5 px-2.5 py-2 rounded-lg transition-colors disabled:opacity-50"
            title={data.status !== 'completed' ? '方案完成后才能分享' : '生成分享链接'}
          >
            <Share2 className="w-4 h-4" /> {shareLoading ? '生成中...' : '分享'}
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-red-500 px-2 py-2 transition-colors"
          >
            <Trash2 className="w-4 h-4" /> 删除
          </button>
        </div>
      </div>

      {/* 分享链接 */}
      {shareUrl && (
        <div className="bg-gradient-to-r from-primary/5 to-purple-500/5 border border-primary/20 rounded-xl p-4 mb-4">
          <p className="text-sm font-medium text-gray-700 mb-2">🔗 分享链接（他人无需登录即可查看）</p>
          <div className="flex gap-2">
            <input
              readOnly
              value={shareUrl}
              onFocus={e => e.target.select()}
              className="flex-1 min-w-0 px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none"
            />
            <button
              onClick={copyLink}
              className="flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors flex-shrink-0"
            >
              {copied ? <Check className="w-4 h-4" /> : <Share2 className="w-4 h-4" />}
              {copied ? '已复制' : '复制'}
            </button>
          </div>
        </div>
      )}

      {/* 标题 + 元信息 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-2xl font-bold text-gray-900 leading-snug">{data.title}</h2>
          <span className={`flex-shrink-0 text-xs px-2.5 py-1 rounded-full ${status.cls}`}>{status.label}</span>
        </div>
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

      {/* Agent 日志 */}
      {data.agent_logs?.length > 0 && (
        <div className="mt-4 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="w-full flex items-center justify-between px-5 py-3 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <span className="font-medium">🤖 Agent 工作日志（{data.agent_logs.length} 条）</span>
            {showLogs ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          {showLogs && (
            <div className="border-t border-gray-100 divide-y divide-gray-50">
              {data.agent_logs.map((log: any, i: number) => (
                <div key={i} className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-700">{log.agent_name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      log.status === 'completed' ? 'bg-green-100 text-green-700'
                      : log.status === 'failed' ? 'bg-red-100 text-red-700'
                      : 'bg-blue-100 text-blue-700'
                    }`}>{log.status}</span>
                  </div>
                  {log.output && Object.keys(log.output).length > 0 && (
                    <pre className="mt-1.5 text-xs text-gray-500 whitespace-pre-wrap bg-gray-50 rounded-lg p-2.5 max-h-40 overflow-y-auto">
                      {JSON.stringify(log.output, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
