import { useState, useEffect } from 'react'
import {
  Backpack, Tent, CookingPot, Shirt, Footprints, Flashlight,
  Smartphone, HeartPulse, Map, Wrench, Package, Plus, Trash2,
  Weight, ChevronDown, ChevronRight, Sparkles, ArrowRight, Check,
  Loader2,
} from 'lucide-react'
import api from '../services/api'

interface GearItem {
  id: number
  category_id: number
  name: string
  brand: string
  model: string
  weight: number
  quantity: number
  description: string
}

interface GearCategory {
  id: number
  name: string
  icon: string
  sort_order: number
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  backpack: <Backpack className="w-5 h-5" />,
  tent: <Tent className="w-5 h-5" />,
  'cooking-pot': <CookingPot className="w-5 h-5" />,
  shirt: <Shirt className="w-5 h-5" />,
  footprints: <Footprints className="w-5 h-5" />,
  'trekking-pole': <Footprints className="w-5 h-5" />,
  flashlight: <Flashlight className="w-5 h-5" />,
  smartphone: <Smartphone className="w-5 h-5" />,
  'heart-pulse': <HeartPulse className="w-5 h-5" />,
  map: <Map className="w-5 h-5" />,
  wrench: <Wrench className="w-5 h-5" />,
  package: <Package className="w-5 h-5" />,
}

const CATEGORY_GUIDE: Record<string, string> = {
  '背负系统': '登山包是你的移动之家。大背包(50-70L)装所有装备，冲顶包/腰包放随身物品，防水袋保护重要装备。',
  '睡眠系统': '好的睡眠是徒步的能量来源。帐篷挡风遮雨，睡袋和防潮垫决定你的睡眠质量。',
  '饮食系统': '山上吃好很重要！炉头+锅具做热食，水袋/水瓶保证饮水，净水器让你安全取水。',
  '服装-上衣': '三层穿衣法则：排汗底层(速干)+保暖中层(抓绒/羽绒)+防风外层(冲锋衣)，灵活穿脱应对天气。',
  '服装-下装': '徒步裤要透气耐磨。冲锋裤防风防雨，速干裤日常穿。别忘了雨衣！',
  '鞋袜': '徒步鞋是最重要的装备！高帮防水保护脚踝，羊毛袜防磨防臭，营地鞋让脚休息。',
  '登山杖/冰爪': '登山杖省力30%，双杖更好。冰爪雪套是冰雪路线的安全保障。',
  '照明': '头灯解放双手是首选。记得带备用电池！',
  '电子设备': '充电宝是生命线。手机+离线地图+GPS确保不迷路。',
  '急救/药品': '急救包必须齐全：创可贴/碘伏/绷带/止痛药，高海拔路线加抗高反药。',
  '导航通讯': '离线地图+指南针是基础，卫星电话/SOS设备是安全保障。',
  '工具': '多功能刀、打火机、修补工具…小东西解决大问题。',
  '其他': '防晒霜+墨镜+身份证+现金，容易被忽略但很重要的小物件。',
}

// 每个分类的默认装备模板（weight 为典型单件重量，单位克）
const DEFAULT_ITEMS: Record<string, { name: string; notes: string; quantity: number; weight: number }[]> = {
  '背负系统': [
    { name: '大背包 (50-70L)', notes: '轻量化优先，带防雨罩', quantity: 1, weight: 2200 },
    { name: '冲顶包/腰包 (15-25L)', notes: '放随身贵重物品', quantity: 1, weight: 500 },
    { name: '防水袋/压缩袋', notes: '保护衣物和电子设备', quantity: 3, weight: 150 },
  ],
  '睡眠系统': [
    { name: '帐篷', notes: '三季帐或四季帐，看季节', quantity: 1, weight: 2000 },
    { name: '睡袋', notes: '温标比最低温再低5°C', quantity: 1, weight: 1200 },
    { name: '防潮垫', notes: '充气垫舒适，蛋巢垫可靠', quantity: 1, weight: 550 },
    { name: '充气枕头', notes: '可选，提升睡眠质量', quantity: 1, weight: 80 },
    { name: '地布', notes: '保护帐篷底部', quantity: 1, weight: 200 },
  ],
  '饮食系统': [
    { name: '炉头', notes: '分体式更稳定，一体式更轻', quantity: 1, weight: 80 },
    { name: '气罐', notes: '高海拔用高山气罐', quantity: 2, weight: 350 },
    { name: '锅具套装', notes: '钛合金最轻，铝合金性价比高', quantity: 1, weight: 400 },
    { name: '餐具 (碗/筷/勺)', notes: '折叠或钛合金', quantity: 1, weight: 50 },
    { name: '水袋/水瓶 (2-3L)', notes: '软水袋省空间', quantity: 2, weight: 150 },
    { name: '净水器/净水片', notes: '野外取水必备', quantity: 1, weight: 60 },
    { name: '保温杯', notes: '冬季/高海拔推荐', quantity: 1, weight: 350 },
  ],
  '服装-上衣': [
    { name: '冲锋衣 (硬壳)', notes: 'Gore-Tex或类似防水透气', quantity: 1, weight: 550 },
    { name: '抓绒衣/棉服', notes: '保暖中层', quantity: 1, weight: 400 },
    { name: '速干T恤 (长袖)', notes: '美利奴羊毛或速干面料', quantity: 2, weight: 180 },
    { name: '羽绒服 (营地用)', notes: '充绒量200g+', quantity: 1, weight: 450 },
    { name: '保暖内衣', notes: '美利奴羊毛最佳', quantity: 1, weight: 250 },
  ],
  '服装-下装': [
    { name: '冲锋裤 (硬壳)', notes: '防风防水', quantity: 1, weight: 450 },
    { name: '速干裤', notes: '日常徒步穿', quantity: 1, weight: 250 },
    { name: '雨衣 (分体式)', notes: '比雨披更方便', quantity: 1, weight: 300 },
  ],
  '鞋袜': [
    { name: '徒步鞋 (高帮防水)', notes: '提前磨合2周以上！', quantity: 1, weight: 1200 },
    { name: '徒步袜 (羊毛)', notes: '美利奴羊毛，防磨防臭', quantity: 3, weight: 80 },
    { name: '营地鞋/溯溪鞋', notes: '轻便备用', quantity: 1, weight: 350 },
    { name: '雪套', notes: '雨雪泥地防护', quantity: 1, weight: 200 },
  ],
  '登山杖/冰爪': [
    { name: '登山杖 (双杖)', notes: '碳纤维最轻，铝合金耐用', quantity: 2, weight: 250 },
    { name: '冰爪', notes: '冰雪路面必备', quantity: 1, weight: 700 },
  ],
  '照明': [
    { name: '头灯', notes: '首选，解放双手', quantity: 1, weight: 60 },
    { name: '备用电池', notes: 'AA或18650，看头灯型号', quantity: 2, weight: 50 },
  ],
  '电子设备': [
    { name: '充电宝 (20000mAh+)', notes: '至少够充手机2-3次', quantity: 2, weight: 450 },
    { name: '手机 + 离线地图', notes: '提前下载离线地图', quantity: 1, weight: 200 },
    { name: 'GPS手持机', notes: '可选，长线推荐', quantity: 1, weight: 250 },
    { name: '太阳能充电板', notes: '长线可选', quantity: 1, weight: 400 },
  ],
  '急救/药品': [
    { name: '急救包', notes: '创可贴/碘伏棉签/绷带/医用胶带', quantity: 1, weight: 300 },
    { name: '常用药品', notes: '止痛药/止泻药/过敏药/感冒药', quantity: 1, weight: 200 },
    { name: '抗高反药', notes: '乙酰唑胺/红景天，高海拔必备', quantity: 1, weight: 100 },
    { name: '防晒霜 (SPF50+)', notes: '高原紫外线强', quantity: 1, weight: 60 },
    { name: '防蚊液', notes: '夏季必备', quantity: 1, weight: 50 },
  ],
  '导航通讯': [
    { name: '地图 (纸质)', notes: '电子设备没电时的后备', quantity: 1, weight: 100 },
    { name: '指南针', notes: '小巧必备', quantity: 1, weight: 50 },
    { name: '卫星电话/SOS设备', notes: '无信号区域安全保障', quantity: 1, weight: 250 },
  ],
  '工具': [
    { name: '多功能刀/瑞士军刀', notes: '实用小工具', quantity: 1, weight: 100 },
    { name: '打火机/防水火柴', notes: '生火备用', quantity: 2, weight: 20 },
    { name: '修补工具', notes: '帐篷修补/睡垫修补片', quantity: 1, weight: 50 },
    { name: '登山绳/扁带', notes: '必要时使用', quantity: 1, weight: 500 },
    { name: '垃圾袋', notes: 'LNT原则，带走所有垃圾', quantity: 3, weight: 30 },
  ],
  '其他': [
    { name: '墨镜', notes: '高原/雪地防紫外线', quantity: 1, weight: 40 },
    { name: '速干毛巾', notes: '轻便快干', quantity: 1, weight: 60 },
    { name: '身份证/现金', notes: '山区可能无信号', quantity: 1, weight: 50 },
    { name: '纸巾/湿巾', notes: '个人卫生', quantity: 1, weight: 50 },
    { name: '户外保险', notes: '含直升机救援', quantity: 1, weight: 0 },
  ],
}

export default function Equipment() {
  const [categories, setCategories] = useState<GearCategory[]>([])
  const [items, setItems] = useState<GearItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [showGuide, setShowGuide] = useState(false)
  const [guideStep, setGuideStep] = useState(0)
  const [addingItem, setAddingItem] = useState<number | null>(null) // category_id being added to

  // 初始化：加载分类和装备
  useEffect(() => {
    initData()
  }, [])

  const initData = async () => {
    setLoading(true)
    try {
      // 确保默认分类已初始化
      await api.post('/equipment/init-defaults')
      // 加载分类
      const catRes = await api.get('/equipment/categories')
      setCategories(catRes.data)
      // 加载装备
      const itemsRes = await api.get('/equipment/items')
      setItems(itemsRes.data)
      // 默认展开所有分类
      const catIds = (catRes.data as GearCategory[]).map(c => c.id)
      setExpanded(new Set(catIds))
      // 首次使用？弹出引导
      if (!itemsRes.data || itemsRes.data.length === 0) {
        setShowGuide(true)
      }
    } catch (err) {
      console.error('加载装备失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleExpand = (catId: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(catId)) next.delete(catId)
      else next.add(catId)
      return next
    })
  }

  const getItemsByCategory = (catId: number) =>
    items.filter(item => item.category_id === catId)

  const updateItemField = async (item: GearItem, field: string, value: any) => {
    // 乐观更新
    setItems(prev => prev.map(i => i.id === item.id ? { ...i, [field]: value } : i))
    try {
      await api.put(`/equipment/items/${item.id}`, {
        category_id: item.category_id,
        name: item.name,
        brand: item.brand,
        model: field === 'model' ? value : item.model,
        weight: field === 'weight' ? value : item.weight,
        quantity: field === 'quantity' ? value : item.quantity,
        description: item.description,
      })
    } catch {
      // 回滚
      setItems(prev => prev.map(i => i.id === item.id ? item : i))
    }
  }

  const addItem = async (catId: number) => {
    setAddingItem(catId)
    try {
      const res = await api.post('/equipment/items', {
        category_id: catId,
        name: '新装备',
        brand: '',
        model: '',
        weight: 0,
        quantity: 1,
        description: '',
      })
      setItems(prev => [...prev, res.data])
    } catch (err) {
      console.error('添加失败:', err)
    } finally {
      setAddingItem(null)
    }
  }

  const deleteItem = async (itemId: number) => {
    setItems(prev => prev.filter(i => i.id !== itemId))
    try {
      await api.delete(`/equipment/items/${itemId}`)
    } catch {
      // 刷新
      initData()
    }
  }

  // 一键填充默认装备
  const fillDefaults = async () => {
    for (const cat of categories) {
      const templates = DEFAULT_ITEMS[cat.name]
      if (!templates) continue
      for (const t of templates) {
        try {
          const res = await api.post('/equipment/items', {
            category_id: cat.id,
            name: t.name,
            brand: '',
            model: '',
            weight: t.weight,
            quantity: t.quantity,
            description: t.notes,
          })
          setItems(prev => [...prev, res.data])
        } catch { /* skip */ }
      }
    }
    setShowGuide(false)
  }

  // 统计
  const totalItems = items.reduce((s, i) => s + i.quantity, 0)
  const totalWeight = items.reduce((s, i) => s + (i.weight || 0) * (i.quantity || 1), 0)
  const filledCats = categories.filter(c => getItemsByCategory(c.id).length > 0).length
  const catProgress = categories.length > 0 ? Math.round((filledCats / categories.length) * 100) : 0

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
          <h2 className="text-2xl font-bold text-gray-900">装备管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理你的全部徒步装备 · {filledCats}/{categories.length} 分类已填写
          </p>
        </div>
        <div className="flex gap-3 text-center">
          <div className="bg-white rounded-lg border px-4 py-2">
            <p className="text-xs text-gray-500">总件数</p>
            <p className="text-xl font-bold text-gray-900">{totalItems}</p>
          </div>
          <div className="bg-white rounded-lg border px-4 py-2">
            <p className="text-xs text-gray-500 flex items-center gap-1"><Weight className="w-3 h-3" />总重量</p>
            <p className="text-xl font-bold text-primary">
              {(totalWeight / 1000).toFixed(1)}<span className="text-sm font-normal">kg</span>
            </p>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-4 bg-gray-200 rounded-full h-1.5">
        <div
          className="bg-primary h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${catProgress}%` }}
        />
      </div>

      {/* First-time guide */}
      {showGuide && (
        <div className="mb-6 bg-gradient-to-r from-primary/5 to-purple-500/5 border border-primary/20 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 text-lg mb-1">欢迎使用装备管理！</h3>
              <p className="text-sm text-gray-600 mb-4">
                完整的装备清单让 AI 能更精准地为你规划。请花 5 分钟填写你的装备，或者使用我们预设的模板快速开始。
              </p>
              {guideStep === 0 ? (
                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={() => setGuideStep(1)}
                    className="flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
                  >
                    开始逐个填写 <ArrowRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={fillDefaults}
                    className="flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                  >
                    <Check className="w-4 h-4" /> 使用预设模板快速填充
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-500 mb-2">
                    引导模式：点击下方每个分类展开，添加你的装备。填写更多=AI 推荐更精准。
                  </p>
                  <button onClick={() => setShowGuide(false)} className="text-sm text-primary hover:underline">
                    跳过引导，我自己来
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Category modules */}
      <div className="space-y-3">
        {categories.map(cat => {
          const catItems = getItemsByCategory(cat.id)
          const catWeight = catItems.reduce((s, i) => s + (i.weight || 0) * (i.quantity || 1), 0)
          const isExpanded = expanded.has(cat.id)
          const isEmpty = catItems.length === 0

          return (
            <div
              key={cat.id}
              className={`bg-white rounded-xl border overflow-hidden transition-colors ${
                isEmpty ? 'border-orange-200 bg-orange-50/30' : 'border-gray-200'
              }`}
            >
              {/* Header */}
              <button
                onClick={() => toggleExpand(cat.id)}
                className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={isEmpty ? 'text-orange-400' : 'text-primary'}>
                    {CATEGORY_ICONS[cat.icon] || <Package className="w-5 h-5" />}
                  </div>
                  <div className="text-left">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{cat.name}</h3>
                      {isEmpty && (
                        <span className="text-[10px] bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded">
                          待填写
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {catItems.length > 0
                        ? `${catItems.reduce((s, i) => s + i.quantity, 0)} 件 · ${catWeight}g`
                        : CATEGORY_GUIDE[cat.name]?.slice(0, 50) + '...'}
                    </p>
                  </div>
                </div>
                {isExpanded ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
              </button>

              {/* Content */}
              {isExpanded && (
                <div className="border-t border-gray-100">
                  {/* Guide tip for empty categories */}
                  {isEmpty && (
                    <div className="px-5 py-3 bg-orange-50 text-xs text-orange-700 border-b border-orange-100">
                      💡 {CATEGORY_GUIDE[cat.name]}
                    </div>
                  )}

                  {/* Items table */}
                  {catItems.length > 0 && (
                    <div className="overflow-x-auto">
                    <table className="w-full min-w-[540px]">
                      <thead>
                        <tr className="text-xs text-gray-400 bg-gray-50">
                          <th className="text-left px-5 py-2 font-medium">装备名称</th>
                          <th className="text-left px-2 py-2 font-medium w-20">品牌</th>
                          <th className="text-center px-2 py-2 font-medium w-14">数量</th>
                          <th className="text-right px-2 py-2 font-medium w-20">重量(g)</th>
                          <th className="px-2 py-2 w-10"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {catItems.map(item => (
                          <tr key={item.id} className="border-t border-gray-50 hover:bg-gray-50/50 group">
                            <td className="px-5 py-1.5">
                              <input
                                type="text"
                                defaultValue={item.name}
                                onBlur={(e) => {
                                  if (e.target.value !== item.name) updateItemField(item, 'name', e.target.value)
                                }}
                                placeholder="装备名称"
                                className="w-full text-sm bg-transparent border-none focus:outline-none focus:ring-0 placeholder-gray-300"
                              />
                            </td>
                            <td className="px-2 py-1.5">
                              <input
                                type="text"
                                defaultValue={item.brand}
                                onBlur={(e) => updateItemField(item, 'brand', e.target.value)}
                                placeholder="品牌"
                                className="w-full text-xs bg-transparent border-none focus:outline-none focus:ring-0 placeholder-gray-300 text-gray-500"
                              />
                            </td>
                            <td className="px-2 py-1.5">
                              <input
                                type="number"
                                defaultValue={item.quantity}
                                onBlur={(e) => {
                                  const v = parseInt(e.target.value) || 1
                                  if (v !== item.quantity) updateItemField(item, 'quantity', v)
                                }}
                                min={0}
                                className="w-full text-center text-sm bg-gray-50 rounded border border-gray-200 py-0.5"
                              />
                            </td>
                            <td className="px-2 py-1.5">
                              <input
                                type="number"
                                defaultValue={item.weight || ''}
                                onBlur={(e) => {
                                  const v = parseInt(e.target.value) || 0
                                  if (v !== item.weight) updateItemField(item, 'weight', v)
                                }}
                                placeholder="0"
                                className="w-full text-right text-sm bg-gray-50 rounded border border-gray-200 py-0.5"
                              />
                            </td>
                            <td className="px-2 py-1.5">
                              <button
                                onClick={() => deleteItem(item.id)}
                                className="p-1.5 -m-1 text-gray-300 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
                                title="删除装备"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    </div>
                  )}

                  {/* Add button */}
                  <button
                    onClick={() => addItem(cat.id)}
                    disabled={addingItem === cat.id}
                    className="w-full flex items-center justify-center gap-2 py-3 text-sm text-gray-400 hover:text-primary hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    {addingItem === cat.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Plus className="w-4 h-4" />
                    )}
                    添加装备
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
