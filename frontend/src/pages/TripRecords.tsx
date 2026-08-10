import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Footprints, Calendar, Star, Camera, Plus, ChevronRight, Loader2 } from 'lucide-react'
import api from '../services/api'
import TripFormModal from '../components/trips/TripFormModal'

interface Trip {
  id: number
  title: string
  start_date: string | null
  end_date: string | null
  actual_distance: number | null
  actual_elevation_gain: number | null
  rating: number
  weather: string
  notes: string
  description: string
  created_at: string
}

export default function TripRecords() {
  const navigate = useNavigate()
  const [trips, setTrips] = useState<Trip[]>([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'grid' | 'list'>('list')
  const [showForm, setShowForm] = useState(false)

  const loadTrips = () => {
    setLoading(true)
    api.get('/trips/')
      .then(res => setTrips(res.data || []))
      .catch(() => setTrips([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTrips()
  }, [])

  const totalDist = trips.reduce((s, t) => s + (t.actual_distance || 0), 0)
  const totalElev = trips.reduce((s, t) => s + (t.actual_elevation_gain || 0), 0)
  const totalCount = trips.length

  const fmtDate = (s: string | null) => s ? new Date(s).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) : '—'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">徒步记录</h2>
          <p className="text-sm text-gray-500 mt-1">记录你的每一次山野之旅</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView('list')}
            className={`px-3 py-2 text-sm rounded-lg transition-colors ${view === 'list' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            列表
          </button>
          <button
            onClick={() => setView('grid')}
            className={`px-3 py-2 text-sm rounded-lg transition-colors ${view === 'grid' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            网格
          </button>
          <button
            onClick={() => setShowForm(true)}
            className="px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors flex items-center gap-1"
          >
            <Plus className="w-4 h-4" /> 记录
          </button>
        </div>
      </div>

      {/* 统计仪表盘 */}
      <div className="grid grid-cols-3 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-xs text-gray-500">徒步次数</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{totalCount}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-xs text-gray-500">累计距离</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{totalDist.toFixed(1)}<span className="text-sm text-gray-400">km</span></p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-xs text-gray-500">累计爬升</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{Math.round(totalElev)}<span className="text-sm text-gray-400">m</span></p>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center items-center py-20 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin mr-2" /> 加载中...
        </div>
      )}

      {!loading && trips.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Footprints className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 mb-2">还没有徒步记录</p>
          <p className="text-sm text-gray-400">完成一次徒步后，在这里记录你的足迹</p>
        </div>
      )}

      {/* 记录卡片 */}
      <div className={view === 'grid'
        ? 'grid grid-cols-1 md:grid-cols-2 gap-4'
        : 'space-y-4'
      }>
        {trips.map(trip => (
          <button
            key={trip.id}
            onClick={() => navigate(`/trips/${trip.id}`)}
            className="bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all overflow-hidden text-left w-full"
          >
            <div className="h-24 bg-gradient-to-r from-blue-400 to-emerald-400 flex items-center justify-center">
              <Camera className="w-7 h-7 text-white/60" />
            </div>

            <div className="p-5">
              <div className="flex items-start justify-between mb-2">
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{trip.title}</h3>
                  <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                    <Calendar className="w-3 h-3" /> {fmtDate(trip.start_date)} ~ {fmtDate(trip.end_date)}
                  </p>
                </div>
                <div className="flex items-center gap-0.5 flex-shrink-0 ml-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className={`w-4 h-4 ${i < (trip.rating || 0) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} />
                  ))}
                </div>
              </div>

              <div className="flex gap-3 flex-wrap text-sm text-gray-600 mb-3">
                <span>{trip.actual_distance != null ? `${trip.actual_distance}km` : '—'}</span>
                <span>{trip.actual_elevation_gain != null ? `↑${trip.actual_elevation_gain}m` : ''}</span>
                {trip.weather && <span className="text-gray-400">{trip.weather}</span>}
              </div>

              {trip.notes && (
                <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 italic">"{trip.notes.slice(0, 80)}..."</p>
              )}

              <span className="mt-1 flex items-center gap-1 text-sm text-primary hover:text-primary-dark transition-colors py-2 px-1 -mx-1">
                查看详情 <ChevronRight className="w-4 h-4" />
              </span>
            </div>
          </button>
        ))}
      </div>

      <TripFormModal
        open={showForm}
        onClose={() => setShowForm(false)}
        onSaved={loadTrips}
      />
    </div>
  )
}
