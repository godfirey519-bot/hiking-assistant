import { useEffect, useState } from 'react'
import { X, Star, Loader2, Footprints, Calendar, Route as RouteIcon, ArrowUp, Navigation } from 'lucide-react'
import api from '../../services/api'

interface TripFormModalProps {
  open: boolean
  onClose: () => void
  onSaved: () => void
}

interface FormState {
  title: string
  start_date: string
  end_date: string
  actual_distance: string
  actual_elevation_gain: string
  rating: number
  weather: string
  description: string
  notes: string
}

const EMPTY_FORM: FormState = {
  title: '',
  start_date: '',
  end_date: '',
  actual_distance: '',
  actual_elevation_gain: '',
  rating: 0,
  weather: '',
  description: '',
  notes: '',
}

const inputCls =
  'w-full px-3 py-2.5 text-sm text-gray-900 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary placeholder:text-gray-400'

export default function TripFormModal({ open, onClose, onSaved }: TripFormModalProps) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // 打开时重置表单
  useEffect(() => {
    if (open) {
      setForm(EMPTY_FORM)
      setError('')
    }
  }, [open])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async () => {
    if (!form.title.trim()) {
      setError('请填写标题')
      return
    }
    setSaving(true)
    setError('')
    try {
      await api.post('/trips/', {
        title: form.title.trim(),
        description: form.description.trim(),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        actual_distance: form.actual_distance ? Number(form.actual_distance) : null,
        actual_elevation_gain: form.actual_elevation_gain ? Number(form.actual_elevation_gain) : null,
        rating: form.rating,
        weather: form.weather.trim(),
        notes: form.notes.trim(),
      })
      onSaved()
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-black/40" onClick={() => !saving && onClose()} />

      {/* 面板：移动端底部弹出，桌面居中 */}
      <div className="relative w-full sm:max-w-lg bg-white rounded-t-2xl sm:rounded-2xl shadow-xl max-h-[92vh] flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Footprints className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-bold text-gray-900">记录一次徒步</h3>
          </div>
          <button
            onClick={onClose}
            disabled={saving}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            aria-label="关闭"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 表单主体（可滚动） */}
        <div className="px-5 py-4 space-y-4 overflow-y-auto">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              标题 <span className="text-red-500">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="如：武功山金顶 2 日穿越"
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
              <input
                type="date"
                className={inputCls}
                value={form.start_date}
                onChange={(e) => set('start_date', e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
              <input
                type="date"
                className={inputCls}
                value={form.end_date}
                onChange={(e) => set('end_date', e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <span className="inline-flex items-center gap-1"><Navigation className="w-3.5 h-3.5" /> 实际距离 (km)</span>
              </label>
              <input
                type="number"
                inputMode="decimal"
                min="0"
                step="0.1"
                className={inputCls}
                placeholder="0.0"
                value={form.actual_distance}
                onChange={(e) => set('actual_distance', e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <span className="inline-flex items-center gap-1"><ArrowUp className="w-3.5 h-3.5" /> 累计爬升 (m)</span>
              </label>
              <input
                type="number"
                inputMode="numeric"
                min="0"
                step="1"
                className={inputCls}
                placeholder="0"
                value={form.actual_elevation_gain}
                onChange={(e) => set('actual_elevation_gain', e.target.value)}
              />
            </div>
          </div>

          {/* 评分 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">评分</label>
            <div className="flex items-center gap-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => set('rating', i + 1)}
                  className={`p-1.5 rounded-lg transition-colors ${form.rating > i ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-200'}`}
                  aria-label={`${i + 1} 星`}
                >
                  <Star className={`w-7 h-7 ${form.rating > i ? 'fill-yellow-400' : ''}`} />
                </button>
              ))}
              <span className="text-sm text-gray-400 ml-2">
                {form.rating ? `${form.rating} / 5` : '未评分'}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <span className="inline-flex items-center gap-1"><RouteIcon className="w-3.5 h-3.5" /> 天气情况</span>
            </label>
            <input
              className={inputCls}
              placeholder="如：晴，山顶有风"
              value={form.weather}
              onChange={(e) => set('weather', e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">行程描述</label>
            <textarea
              className={`${inputCls} min-h-[70px] resize-y`}
              placeholder="这次徒步走过了哪些地方，看到了什么…"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">回顾笔记</label>
            <textarea
              className={`${inputCls} min-h-[70px] resize-y`}
              placeholder="身体感受、难忘瞬间、经验教训…"
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}
        </div>

        {/* 底部操作 */}
        <div className="flex gap-3 px-5 py-4 border-t border-gray-100">
          <button
            onClick={onClose}
            disabled={saving}
            className="flex-1 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 py-2.5 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calendar className="w-4 h-4" />}
            {saving ? '保存中…' : '保存记录'}
          </button>
        </div>
      </div>
    </div>
  )
}
