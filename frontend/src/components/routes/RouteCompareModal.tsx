import { X } from 'lucide-react'

interface CompareRoute {
  name: string
  distance: number
  elevation: number
  maxEle: number
  difficulty: string
  days: number
  terrain: string
  bestSeason: string
  region: string
  trailhead: string
  isUserUpload?: boolean
}

type CompareField = 'distance' | 'elevation' | 'maxEle' | 'difficulty' | 'days' | 'terrain' | 'bestSeason' | 'region' | 'trailhead'

const ROWS: { key: CompareField; label: string; kind: 'num' | 'text' }[] = [
  { key: 'distance', label: '距离', kind: 'num' },
  { key: 'elevation', label: '累计爬升', kind: 'num' },
  { key: 'maxEle', label: '最高海拔', kind: 'num' },
  { key: 'difficulty', label: '难度', kind: 'text' },
  { key: 'days', label: '天数', kind: 'num' },
  { key: 'terrain', label: '地形', kind: 'text' },
  { key: 'bestSeason', label: '最佳季节', kind: 'text' },
  { key: 'region', label: '地区', kind: 'text' },
  { key: 'trailhead', label: '起点', kind: 'text' },
]

function formatValue(key: CompareField, v: string | number): string {
  if (key === 'distance') return `${v}km`
  if (key === 'elevation' || key === 'maxEle') return `${v}m`
  if (key === 'days') return `${v}天`
  return String(v ?? '—')
}

export default function RouteCompareModal({
  routes,
  onClose,
}: {
  routes: CompareRoute[]
  onClose: () => void
}) {
  // 数值行计算最小/最大值，用于高亮
  const extremes = ROWS.reduce<Record<string, { min: number | null; max: number | null }>>((acc, row) => {
    if (row.kind === 'num') {
      const vals = routes.map(r => Number(r[row.key])).filter(v => !Number.isNaN(v))
      acc[row.key] = {
        min: vals.length ? Math.min(...vals) : null,
        max: vals.length ? Math.max(...vals) : null,
      }
    }
    return acc
  }, {})

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4"
      onClick={onClose}
    >
      <div
        className="bg-white w-full sm:max-w-2xl rounded-t-2xl sm:rounded-2xl shadow-xl max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-3 flex items-center justify-between z-10">
          <div>
            <h3 className="font-bold text-gray-900">路线对比</h3>
            <p className="text-xs text-gray-500">{routes.length} 条路线 · 绿色=数值最低，红色=最高</p>
          </div>
          <button onClick={onClose} className="p-2 -m-2 text-gray-400 hover:text-gray-700 rounded-lg" title="关闭">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 对比表格（移动端横向滑动） */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="sticky left-0 bg-white text-left px-5 py-3 text-xs font-medium text-gray-500 border-b border-gray-100 whitespace-nowrap z-10">
                  属性
                </th>
                {routes.map(r => (
                  <th
                    key={r.name}
                    className="text-left px-3 py-3 font-semibold text-gray-900 border-b border-gray-100 whitespace-nowrap max-w-[150px] truncate"
                  >
                    {r.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map(row => (
                <tr key={row.key} className="border-b border-gray-50 last:border-0">
                  <td className="sticky left-0 bg-white px-5 py-2.5 text-xs text-gray-500 whitespace-nowrap z-10">
                    {row.label}
                  </td>
                  {routes.map(r => {
                    const v = r[row.key]
                    let cls = 'text-gray-700'
                    if (row.kind === 'num') {
                      const num = Number(v)
                      const ext = extremes[row.key]
                      if (!Number.isNaN(num) && ext) {
                        if (num === ext.min && ext.min !== ext.max) cls = 'text-green-600 font-semibold'
                        else if (num === ext.max) cls = 'text-red-500 font-medium'
                      }
                    }
                    return (
                      <td key={r.name} className={`px-3 py-2.5 whitespace-nowrap ${cls}`}>
                        {formatValue(row.key, v)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* footer 说明 */}
        <div className="px-5 py-3 bg-gray-50/50 text-xs text-gray-500">
          💡 绿/红仅表示该项数值的高低（距离短、天数少、爬升低等），不代表好坏，请结合难度、地形与自身经验综合判断。
        </div>
      </div>
    </div>
  )
}
