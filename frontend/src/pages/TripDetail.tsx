import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Calendar, Navigation, ArrowUp, Star, Loader2, Route as RouteIcon, ImagePlus } from 'lucide-react'
import api from '../services/api'

export default function TripDetail() {
  const { id } = useParams()
  const [trip, setTrip] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadTrip = useCallback(() => {
    api.get(`/trips/${id}`)
      .then(res => setTrip(res.data))
      .catch(() => setError('记录不存在或加载失败'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    loadTrip()
  }, [loadTrip])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      // 必须显式指定 multipart：axios 实例默认头是 application/json，
      // 否则 FastAPI 无法解析 file 字段（422 Field required）
      await api.post(`/trips/${id}/upload-media`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await loadTrip()
    } catch (err: any) {
      alert(err?.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24 text-gray-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> 加载记录...
      </div>
    )
  }

  if (error || !trip) {
    return (
      <div className="max-w-3xl mx-auto">
        <Link to="/trips" className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mb-6">
          <ArrowLeft className="w-4 h-4" /> 返回徒步记录
        </Link>
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
          {error || '记录不存在'}
        </div>
      </div>
    )
  }

  const fmtDate = (s: string | null) => s ? new Date(s).toLocaleDateString('zh-CN') : '—'

  const stats = [
    { icon: <Navigation className="w-4 h-4" />, label: '实际距离', value: trip.actual_distance != null ? `${trip.actual_distance}km` : '—' },
    { icon: <ArrowUp className="w-4 h-4" />, label: '累计爬升', value: trip.actual_elevation_gain != null ? `${trip.actual_elevation_gain}m` : '—' },
    { icon: <Star className="w-4 h-4" />, label: '评分', value: trip.rating ? `${trip.rating} / 5` : '—' },
    { icon: <RouteIcon className="w-4 h-4" />, label: '天气', value: trip.weather || '—' },
  ]

  return (
    <div className="max-w-3xl mx-auto">
      <Link to="/trips" className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mb-4">
        <ArrowLeft className="w-4 h-4" /> 徒步记录
      </Link>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h2 className="text-2xl font-bold text-gray-900 mb-1">{trip.title}</h2>
        <div className="flex flex-wrap gap-3 text-sm text-gray-500 mb-4">
          <span className="flex items-center gap-1.5"><Calendar className="w-4 h-4" /> {fmtDate(trip.start_date)} ~ {fmtDate(trip.end_date)}</span>
          <span className="text-xs text-gray-400">创建于 {new Date(trip.created_at).toLocaleString('zh-CN')}</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {stats.map((s, i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center gap-1 text-gray-500 mb-0.5">{s.icon}<span className="text-[10px]">{s.label}</span></div>
              <p className="text-base font-bold text-gray-900 truncate">{s.value}</p>
            </div>
          ))}
        </div>
      </div>

      {trip.description && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <h3 className="font-semibold text-gray-900 mb-2">行程描述</h3>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{trip.description}</p>
        </div>
      )}

      {trip.notes && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <h3 className="font-semibold text-gray-900 mb-2">回顾笔记</h3>
          <p className="text-sm text-gray-600 italic whitespace-pre-wrap">"{trip.notes}"</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">照片 / 视频{trip.media?.length ? `（${trip.media.length}）` : ''}</h3>
          <label
            className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg cursor-pointer transition-colors ${
              uploading ? 'bg-gray-100 text-gray-400' : 'bg-primary/10 text-primary hover:bg-primary/20'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
            {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ImagePlus className="w-3.5 h-3.5" />}
            {uploading ? '上传中…' : '添加照片/视频'}
          </label>
        </div>

        {trip.media?.length > 0 ? (
          <div className="grid grid-cols-3 gap-2">
            {trip.media.map((m: any) => {
              const src = `/media/${m.file_path}`
              return m.file_type === 'video' ? (
                <div key={m.id} className="relative">
                  <video
                    controls
                    playsInline
                    preload="metadata"
                    src={src}
                    className="w-full aspect-square object-cover rounded-lg bg-gray-100"
                  />
                </div>
              ) : (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => window.open(src, '_blank', 'noopener')}
                  className="aspect-square overflow-hidden rounded-lg group relative"
                  aria-label="查看大图"
                >
                  <img
                    src={src}
                    alt={m.description || '徒步照片'}
                    loading="lazy"
                    className="w-full h-full object-cover group-hover:opacity-90 transition-opacity"
                  />
                </button>
              )
            })}
          </div>
        ) : (
          <p className="text-xs text-gray-400">还没有照片或视频，上传后在这里展示</p>
        )}
      </div>
    </div>
  )
}
