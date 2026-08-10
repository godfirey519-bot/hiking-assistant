import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Map, ArrowLeft, Mountain, Clock, ArrowUp, Navigation, Loader2, PlusCircle } from 'lucide-react'
import { MapContainer, TileLayer, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import api from '../services/api'

const DIFFICULTY_MAP: Record<string, string> = {
  easy: '较易', moderate: '中等', hard: '较难', expert: '困难',
}
const DIFF_COLORS: Record<string, string> = {
  较易: 'bg-green-100 text-green-700',
  中等: 'bg-yellow-100 text-yellow-700',
  较难: 'bg-orange-100 text-orange-700',
  困难: 'bg-red-100 text-red-700',
}

export default function RouteDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [route, setRoute] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(`/routes/${id}`)
      .then(res => setRoute(res.data))
      .catch(() => setError('路线不存在或加载失败'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24 text-gray-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> 加载路线...
      </div>
    )
  }

  if (error || !route) {
    return (
      <div className="max-w-3xl mx-auto">
        <Link to="/routes" className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mb-6">
          <ArrowLeft className="w-4 h-4" /> 返回路线管理
        </Link>
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
          {error || '路线不存在'}
        </div>
      </div>
    )
  }

  const diffLabel = DIFFICULTY_MAP[route.difficulty] || '未知'
  const waypoints = (route.waypoints || []).filter((w: any) => typeof w.lat === 'number' && typeof w.lng === 'number')
  const start = waypoints[0]
  const end = waypoints[waypoints.length - 1]
  const center = start || { lat: 35.0, lng: 105.0 }

  const stats = [
    { icon: <Navigation className="w-4 h-4" />, label: '距离', value: `${(route.distance / 1000).toFixed(1)}km` },
    { icon: <ArrowUp className="w-4 h-4" />, label: '累计爬升', value: `${Math.round(route.elevation_gain || 0)}m` },
    { icon: <Mountain className="w-4 h-4" />, label: '最高海拔', value: `${Math.round(route.max_elevation || 0)}m` },
    { icon: <Clock className="w-4 h-4" />, label: '预计', value: `${route.duration_days || 1}天` },
  ]

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <Link to="/routes" className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
          <ArrowLeft className="w-4 h-4" /> 路线管理
        </Link>
        <button
          onClick={() => navigate(`/plans/new?route=${encodeURIComponent(route.name)}`)}
          className="flex items-center gap-1.5 px-4 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
        >
          <PlusCircle className="w-4 h-4" /> 用此路线规划
        </button>
      </div>

      {/* 标题 + 统计 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-2xl font-bold text-gray-900">{route.name}</h2>
          <span className={`text-xs px-2.5 py-1 rounded-full ${DIFF_COLORS[diffLabel] || 'bg-gray-100 text-gray-600'}`}>
            {diffLabel}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {stats.map((s, i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center gap-1 text-gray-500 mb-0.5">{s.icon}<span className="text-[10px]">{s.label}</span></div>
              <p className="text-base font-bold text-gray-900">{s.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 轨迹地图 */}
      {waypoints.length > 1 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-2 mb-4">
          <div className="h-72 rounded-lg overflow-hidden">
            <MapContainer
              center={[center.lat, center.lng]}
              zoom={11}
              scrollWheelZoom={false}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <Polyline
                positions={waypoints.map((w: any) => [w.lat, w.lng])}
                pathOptions={{ color: '#16a34a', weight: 3.5, opacity: 0.85 }}
              />
            </MapContainer>
          </div>
          <p className="text-xs text-gray-400 px-3 py-2">
            📍 起点 ({start.lat.toFixed(4)}, {start.lng.toFixed(4)}) → 终点 ({end.lat.toFixed(4)}, {end.lng.toFixed(4)}) · {waypoints.length} 个轨迹点
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-400 text-sm mb-4">
          <Map className="w-8 h-8 mx-auto mb-2 text-gray-300" />
          该路线没有轨迹点数据
        </div>
      )}

      {/* 路线元信息 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-3">路线信息</h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-4"><dt className="text-gray-400">累计下降</dt><dd className="text-gray-700">{Math.round(route.elevation_loss || 0)}m</dd></div>
          <div className="flex justify-between gap-4"><dt className="text-gray-400">最低海拔</dt><dd className="text-gray-700">{Math.round(route.min_elevation || 0)}m</dd></div>
          <div className="flex justify-between gap-4"><dt className="text-gray-400">GPX 文件</dt><dd className="text-gray-700 break-all">{route.gpx_file_path || '—'}</dd></div>
          <div className="flex justify-between gap-4"><dt className="text-gray-400">创建时间</dt><dd className="text-gray-700">{new Date(route.created_at).toLocaleString('zh-CN')}</dd></div>
        </dl>
      </div>
    </div>
  )
}
