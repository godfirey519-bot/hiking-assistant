import { useState, useRef, useEffect, useCallback } from 'react'
import { Upload, Map, Mountain, Clock, ArrowUp, Search, Loader2, CheckCircle2, AlertCircle, Circle, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import RouteCompareModal from '../components/routes/RouteCompareModal'

// 知识库路线
const KNOWN_ROUTES = [
  { name: '武功山穿越', distance: 22, elevation: 1800, maxEle: 1918, difficulty: '中等', days: 2, terrain: '高山草甸、碎石坡、木栈道', bestSeason: '5-10月', trailhead: '萍乡沈子村/龙山村', region: '江西' },
  { name: '雨崩', distance: 18, elevation: 1500, maxEle: 3800, difficulty: '较难', days: 3, terrain: '高原山路、原始森林', bestSeason: '5-6月、9-10月', trailhead: '德钦飞来寺→西当村', region: '云南' },
  { name: '虎跳峡高路', distance: 25, elevation: 1200, maxEle: 2670, difficulty: '中等', days: 2, terrain: '悬崖栈道、碎石路', bestSeason: '3-6月、9-11月', trailhead: '香格里拉虎跳峡镇', region: '云南' },
  { name: '四姑娘山二峰', distance: 32, elevation: 2200, maxEle: 5276, difficulty: '困难', days: 3, terrain: '高山草甸、碎石坡、雪线', bestSeason: '6-10月', trailhead: '日隆镇', region: '四川' },
  { name: '太白山南北穿越', distance: 45, elevation: 3000, maxEle: 3767, difficulty: '困难', days: 3, terrain: '石海、高山草甸、森林', bestSeason: '6-10月', trailhead: '眉县汤峪/周至厚畛子', region: '陕西' },
  { name: '徽杭古道', distance: 20, elevation: 800, maxEle: 1050, difficulty: '较易', days: 1, terrain: '石板路、古道', bestSeason: '全年', trailhead: '绩溪伏岭镇', region: '安徽' },
  { name: '稻城亚丁', distance: 14, elevation: 1000, maxEle: 4700, difficulty: '较难', days: 2, terrain: '高原湖泊、雪山', bestSeason: '9-10月', trailhead: '稻城香格里拉镇', region: '四川' },
  { name: '长城箭扣段', distance: 10, elevation: 600, maxEle: 1000, difficulty: '中等', days: 1, terrain: '野长城、陡坡', bestSeason: '4-5月、9-10月', trailhead: '怀柔西栅子村', region: '北京' },
]

interface DisplayRoute {
  id?: number        // API routes have id, known routes don't
  name: string
  distance: number   // km
  elevation: number  // m
  maxEle: number
  difficulty: string
  days: number
  terrain: string
  bestSeason: string
  trailhead: string
  region: string
  isUserUpload?: boolean
  routeId?: number   // for navigation
}

const DIFFICULTY_MAP: Record<string, string> = {
  easy: '较易', moderate: '中等', hard: '较难', expert: '困难',
}
const DIFFICULTY_COLORS: Record<string, string> = {
  '轻松': 'bg-green-100 text-green-700',
  '较易': 'bg-green-100 text-green-700',
  '中等': 'bg-yellow-100 text-yellow-700',
  '较难': 'bg-orange-100 text-orange-700',
  '困难': 'bg-red-100 text-red-700',
  '专业级': 'bg-red-200 text-red-800',
}

export default function RoutesPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [uploadMessage, setUploadMessage] = useState('')
  const [userRoutes, setUserRoutes] = useState<DisplayRoute[]>([])
  const [compareList, setCompareList] = useState<string[]>([])
  const [showCompare, setShowCompare] = useState(false)

  // 加载用户已上传的路线
  const fetchUserRoutes = useCallback(async () => {
    try {
      const res = await api.get('/routes/')
      const routes: DisplayRoute[] = (res.data || []).map((r: any) => ({
        id: r.id,
        routeId: r.id,
        name: r.name,
        distance: Math.round((r.distance || 0) / 100) / 10,  // m → km，保留1位小数
        elevation: Math.round(r.elevation_gain || 0),
        maxEle: Math.round(r.max_elevation || 0),
        difficulty: DIFFICULTY_MAP[r.difficulty] || '中等',
        days: r.duration_days || 1,
        terrain: 'GPX 轨迹',
        bestSeason: '—',
        trailhead: r.start_point
          ? `${r.start_point.split(',')[0].slice(0, 7)}...`
          : '—',
        region: '自定义',
        isUserUpload: true,
      }))
      setUserRoutes(routes)
    } catch {
      // Not logged in or API error — just show known routes
    }
  }, [])

  useEffect(() => {
    fetchUserRoutes()
  }, [fetchUserRoutes])

  // GPX 上传
  const uploadGPX = async (file: File) => {
    if (!file.name.endsWith('.gpx')) {
      setUploadStatus('error')
      setUploadMessage('请上传 .gpx 格式的文件')
      setTimeout(() => setUploadStatus('idle'), 3000)
      return
    }

    setUploading(true)
    setUploadStatus('idle')
    setUploadMessage('')

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post('/routes/upload-gpx', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      })

      if (res.data.success) {
        setUploadStatus('success')
        setUploadMessage(`✅ "${res.data.route.name}" 导入成功！${res.data.waypoint_count} 个轨迹点`)
        // 刷新用户路线列表
        await fetchUserRoutes()
        // 3秒后清除成功提示
        setTimeout(() => setUploadStatus('idle'), 4000)
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || '上传失败，请重试'
      setUploadStatus('error')
      setUploadMessage(typeof detail === 'string' ? detail : JSON.stringify(detail))
      setTimeout(() => setUploadStatus('idle'), 5000)
    } finally {
      setUploading(false)
    }
  }

  // 文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadGPX(file)
    // 重置 input 以允许重复上传同一文件
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // 拖拽上传
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) uploadGPX(file)
  }

  const allRoutes: DisplayRoute[] = [...userRoutes, ...KNOWN_ROUTES]

  const toggleCompare = (key: string) => {
    setCompareList(prev => {
      if (prev.includes(key)) return prev.filter(k => k !== key)
      if (prev.length >= 4) return prev
      return [...prev, key]
    })
  }

  const clearCompare = () => setCompareList([])

  const compareRoutes = compareList
    .map(key => allRoutes.find(r => (r.isUserUpload ? `user-${r.id}` : r.name) === key))
    .filter((r): r is DisplayRoute => Boolean(r))

  const filtered = allRoutes.filter(r => {
    if (search && !r.name.includes(search) && !r.region.includes(search)) return false
    if (difficultyFilter && r.difficulty !== difficultyFilter) return false
    return true
  })

  return (
    <div className={`max-w-4xl mx-auto ${compareList.length > 0 ? 'pb-20' : ''}`}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">路线管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            {KNOWN_ROUTES.length} 条经典路线{userRoutes.length > 0 && ` + ${userRoutes.length} 条自定义`} · 或上传 GPX
          </p>
        </div>
      </div>

      {/* 隐藏的文件选择器 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".gpx"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* GPX Upload */}
      <div
        className={`mb-6 border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          dragOver ? 'border-primary bg-primary/5' : uploadStatus === 'success'
            ? 'border-green-400 bg-green-50'
            : uploadStatus === 'error'
              ? 'border-red-400 bg-red-50'
              : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        {uploading ? (
          <>
            <Loader2 className="w-10 h-10 mx-auto mb-3 text-primary animate-spin" />
            <p className="text-gray-600 font-medium">正在解析 GPX 文件...</p>
            <p className="text-xs text-gray-400 mt-1">分析距离、爬升、轨迹点</p>
          </>
        ) : uploadStatus === 'success' ? (
          <>
            <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-green-500" />
            <p className="text-green-700 font-medium">{uploadMessage}</p>
          </>
        ) : uploadStatus === 'error' ? (
          <>
            <AlertCircle className="w-10 h-10 mx-auto mb-3 text-red-500" />
            <p className="text-red-700 font-medium">{uploadMessage}</p>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="text-gray-600 font-medium">拖拽 GPX 文件到此处上传</p>
            <p className="text-xs text-gray-400 mt-1">支持 .gpx 格式 · 自动解析距离/爬升/难度</p>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 px-4 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
            >
              选择文件
            </button>
          </>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索路线或地区..."
            className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <select
          value={difficultyFilter}
          onChange={(e) => setDifficultyFilter(e.target.value)}
          className="px-3 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          <option value="">全部难度</option>
          <option value="较易">较易</option>
          <option value="中等">中等</option>
          <option value="较难">较难</option>
          <option value="困难">困难</option>
        </select>
      </div>

      {/* Route cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map(route => {
          const key = route.isUserUpload ? `user-${route.id}` : route.name
          const selected = selectedRoute === key
          return (
            <div
              key={key}
              onClick={() => setSelectedRoute(selected ? null : key)}
              className={`bg-white rounded-xl border transition-all cursor-pointer ${
                selected ? 'border-primary ring-2 ring-primary/20' : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              {/* Card header */}
              <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900 truncate">{route.name}</h3>
                      {route.isUserUpload && (
                        <span className="px-1.5 py-0.5 text-[10px] bg-blue-100 text-blue-600 rounded font-medium flex-shrink-0">
                          GPX
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{route.region} · {route.trailhead}</p>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleCompare(key) }}
                      title={compareList.includes(key) ? '取消对比' : '加入对比'}
                      className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
                        compareList.includes(key) ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }`}
                    >
                      {compareList.includes(key) ? <CheckCircle2 className="w-4 h-4" /> : <Circle className="w-4 h-4" />}
                    </button>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${DIFFICULTY_COLORS[route.difficulty] || 'bg-gray-100 text-gray-600'}`}>
                      {route.difficulty}
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex gap-4 text-sm">
                  <span className="flex items-center gap-1 text-gray-600">
                    <Map className="w-3.5 h-3.5" /> {route.distance}km
                  </span>
                  <span className="flex items-center gap-1 text-gray-600">
                    <ArrowUp className="w-3.5 h-3.5" /> {route.elevation}m
                  </span>
                  <span className="flex items-center gap-1 text-gray-600">
                    <Clock className="w-3.5 h-3.5" /> {route.days}天
                  </span>
                  <span className="flex items-center gap-1 text-gray-600">
                    <Mountain className="w-3.5 h-3.5" /> {route.maxEle}m
                  </span>
                </div>
              </div>

              {/* Expanded details */}
              {selected && (
                <div className="border-t border-gray-100 px-5 py-4 bg-gray-50/50 rounded-b-xl">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-gray-500">地形</p>
                      <p className="text-gray-700">{route.terrain}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">最佳季节</p>
                      <p className="text-gray-700">{route.bestSeason}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    {route.isUserUpload && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/routes/${route.id}`)
                        }}
                        className="flex-1 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        查看轨迹地图
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        // 跳转到新建规划页，携带路线名
                        navigate(`/plans/new?route=${encodeURIComponent(route.name)}`)
                      }}
                      className={`${route.isUserUpload ? 'flex-1' : 'w-full'} py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors`}
                    >
                      用此路线创建规划
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <Map className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">没有找到匹配的路线</p>
        </div>
      )}

      {/* 对比操作条 */}
      {compareList.length > 0 && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 bg-gray-900/95 text-white rounded-full pl-5 pr-2 py-2 shadow-lg backdrop-blur">
          <span className="text-sm font-medium whitespace-nowrap">已选 {compareList.length}/4</span>
          <button
            onClick={() => setShowCompare(true)}
            disabled={compareList.length < 2}
            className={`px-4 py-1.5 text-sm rounded-full transition-colors ${
              compareList.length < 2
                ? 'bg-white/10 text-white/40 cursor-not-allowed'
                : 'bg-primary text-white hover:bg-primary-dark'
            }`}
          >
            开始对比
          </button>
          <button
            onClick={clearCompare}
            className="w-7 h-7 rounded-full flex items-center justify-center text-white/70 hover:bg-white/10"
            title="清空选择"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 对比弹窗 */}
      {showCompare && (
        <RouteCompareModal routes={compareRoutes} onClose={() => setShowCompare(false)} />
      )}
    </div>
  )
}
