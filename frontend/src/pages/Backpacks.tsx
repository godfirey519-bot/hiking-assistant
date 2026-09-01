import { useState, useEffect } from 'react'
import {
  Backpack, Trash2, Plus, Weight, ChevronDown, ChevronRight,
  Sparkles, Loader2, X,
} from 'lucide-react'
import api from '../services/api'

interface BackpackItem {
  id: number
  name: string
  category: string | null
  weight: number
  quantity: number
}

interface Backpack {
  id: number
  user_id: number
  name: string
  description: string
  base_weight: number
  item_count: number
  total_weight: number
  items: BackpackItem[]
}

interface GearItem {
  id: number
  name: string
  weight: number
  quantity: number
}

const PRESETS = ['轻装单日', '标准周末', '重装长线', '冬季雪山']

const PRESET_DESC: Record<string, string> = {
  '轻装单日': '当日往返，只带必需品',
  '标准周末': '2-3 天标准露营',
  '重装长线': '5 天以上长线重装',
  '冬季雪山': '冬季/雪山保暖防滑',
}

export default function Backpacks() {
  const [backpacks, setBackpacks] = useState<Backpack[]>([])
  const [unassigned, setUnassigned] = useState<GearItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newWeight, setNewWeight] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const load = async () => {
    try {
      const [bpRes, gearRes] = await Promise.all([
        api.get('/backpacks/'),
        api.get('/equipment/items'),
      ])
      setBackpacks(bpRes.data || [])
      const free = (gearRes.data || []).filter((g: any) => !g.backpack_id)
      setUnassigned(free)
    } catch {
      setMsg({ type: 'error', text: '加载失败，请重试' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const flash = (text: string, type: 'success' | 'error' = 'success') => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 3000)
  }

  const createFromPreset = async (name: string) => {
    setBusy(true)
    try {
      await api.post(`/backpacks/preset/${encodeURIComponent(name)}`)
      flash(`已创建「${name}」方案`)
      await load()
    } catch (err: any) {
      flash(err.response?.data?.detail || '创建失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  const createManual = async () => {
    if (!newName.trim()) { flash('请填写方案名称', 'error'); return }
    setBusy(true)
    try {
      await api.post('/backpacks/', {
        name: newName.trim(),
        description: newDesc.trim(),
        base_weight: parseInt(newWeight) || 0,
      })
      flash('背包方案已创建')
      setNewName(''); setNewWeight(''); setNewDesc(''); setShowCreate(false)
      await load()
    } catch (err: any) {
      flash(err.response?.data?.detail || '创建失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  const deleteBp = async (bp: Backpack) => {
    if (!confirm(`确定删除「${bp.name}」？装备本身会保留在装备库`)) return
    try {
      await api.delete(`/backpacks/${bp.id}`)
      flash('已删除')
      await load()
    } catch (err: any) {
      flash(err.response?.data?.detail || '删除失败', 'error')
    }
  }

  const assignItem = async (bpId: number, gearId: number) => {
    try {
      await api.post(`/backpacks/${bpId}/items/${gearId}`)
      await load()
    } catch (err: any) {
      flash(err.response?.data?.detail || '挂载失败', 'error')
    }
  }

  const unassignItem = async (bpId: number, gearId: number) => {
    try {
      await api.delete(`/backpacks/${bpId}/items/${gearId}`)
      await load()
    } catch (err: any) {
      flash(err.response?.data?.detail || '移除失败', 'error')
    }
  }

  const toggle = (id: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const totalItems = backpacks.reduce((s, b) => s + b.item_count, 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">背包方案</h2>
          <p className="text-sm text-gray-500 mt-1">
            把装备组织成可复用的出行配置 · {backpacks.length} 个方案 · {totalItems} 件装备
          </p>
        </div>
        <button
          onClick={() => setShowCreate(v => !v)}
          className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
        >
          <Plus className="w-4 h-4" /> 新建方案
        </button>
      </div>

      {msg && (
        <div className={`mb-4 text-sm px-4 py-3 rounded-lg ${msg.type === 'success' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
          {msg.text}
        </div>
      )}

      {/* Preset quick create */}
      <div className="bg-gradient-to-r from-primary/5 to-purple-500/5 border border-primary/20 rounded-xl p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-gray-900 text-sm">一键创建预设方案</h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {PRESETS.map(name => (
            <button
              key={name}
              onClick={() => createFromPreset(name)}
              disabled={busy}
              className="bg-white border border-gray-200 rounded-xl p-3 text-left hover:border-primary/50 hover:shadow-sm transition-all disabled:opacity-50"
            >
              <div className="flex items-center gap-2 mb-1">
                <Backpack className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-gray-900">{name}</span>
              </div>
              <p className="text-[11px] text-gray-400 leading-snug">{PRESET_DESC[name]}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Manual create */}
      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">自定义方案</h3>
            <button onClick={() => setShowCreate(false)} className="p-1 text-gray-400 hover:text-gray-600"><X className="w-4 h-4" /></button>
          </div>
          <div className="space-y-3">
            <input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="方案名称（如：三天两夜重装）"
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                type="number"
                value={newWeight}
                onChange={e => setNewWeight(e.target.value)}
                placeholder="背包本体重量(g)"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <input
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                placeholder="备注（可选）"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <button
              onClick={createManual}
              disabled={busy}
              className="px-4 py-2.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin inline" /> : '创建'}
            </button>
          </div>
        </div>
      )}

      {/* Backpack list */}
      {backpacks.length === 0 && !showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Backpack className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 mb-2">还没有背包方案</p>
          <p className="text-sm text-gray-400 mb-6">点击上方预设方案，一键生成完整装备配置</p>
        </div>
      )}

      <div className="space-y-3">
        {backpacks.map(bp => {
          const isOpen = expanded.has(bp.id)
          const gearWeight = bp.items.reduce((s, i) => s + (i.weight || 0) * (i.quantity || 1), 0)
          return (
            <div key={bp.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <button onClick={() => toggle(bp.id)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50/50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Backpack className="w-5 h-5 text-primary" />
                  </div>
                  <div className="text-left">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{bp.name}</h3>
                      <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{bp.item_count} 件</span>
                    </div>
                    <p className="text-xs text-gray-500">
                      {bp.description || '—'} · 本体 {bp.base_weight}g
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-xs text-gray-400">总重</p>
                    <p className="text-sm font-bold text-primary">
                      {(bp.total_weight / 1000).toFixed(1)}<span className="text-xs font-normal">kg</span>
                    </p>
                  </div>
                  {isOpen ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
                </div>
              </button>

              {isOpen && (
                <div className="border-t border-gray-100">
                  {/* Assign gear */}
                  <div className="px-5 py-3 bg-gray-50 flex items-center gap-2 flex-wrap">
                    <select
                      value=""
                      onChange={e => { if (e.target.value) assignItem(bp.id, Number(e.target.value)) }}
                      className="text-xs px-2 py-1.5 border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/30 max-w-[200px]"
                    >
                      <option value="">+ 从装备库添加…</option>
                      {unassigned.map(g => (
                        <option key={g.id} value={g.id}>{g.name} ({((g.weight || 0) / 1000).toFixed(1)}kg×{g.quantity})</option>
                      ))}
                    </select>
                    {unassigned.length === 0 && <span className="text-[11px] text-gray-400">装备库暂无未分配装备，可先到装备管理添加</span>}
                  </div>

                  {/* Items */}
                  {bp.items.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[480px]">
                        <thead>
                          <tr className="text-xs text-gray-400 bg-gray-50">
                            <th className="text-left px-5 py-2 font-medium">装备</th>
                            <th className="text-left px-2 py-2 font-medium">分类</th>
                            <th className="text-center px-2 py-2 font-medium w-14">数量</th>
                            <th className="text-right px-2 py-2 font-medium w-20">重量(g)</th>
                            <th className="px-2 py-2 w-10"></th>
                          </tr>
                        </thead>
                        <tbody>
                          {bp.items.map(item => (
                            <tr key={item.id} className="border-t border-gray-50">
                              <td className="px-5 py-2 text-sm text-gray-700">{item.name}</td>
                              <td className="px-2 py-2 text-xs text-gray-400">{item.category || '—'}</td>
                              <td className="px-2 py-2 text-center text-sm text-gray-600">{item.quantity}</td>
                              <td className="px-2 py-2 text-right text-sm text-gray-600">{(item.weight || 0) * (item.quantity || 1)}</td>
                              <td className="px-2 py-2">
                                <button
                                  onClick={() => unassignItem(bp.id, item.id)}
                                  className="p-1.5 text-gray-300 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                                  title="移出背包"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="px-5 py-8 text-center text-sm text-gray-400">
                      方案为空，从上方添加装备
                    </div>
                  )}

                  {/* Footer stats */}
                  <div className="flex items-center justify-between px-5 py-3 bg-gray-50/50 text-xs text-gray-500 border-t border-gray-100">
                    <span className="flex items-center gap-1"><Weight className="w-3.5 h-3.5" /> 装备 {gearWeight}g + 本体 {bp.base_weight}g</span>
                    <button
                      onClick={() => deleteBp(bp)}
                      className="flex items-center gap-1 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> 删除方案
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
