import { Map, Mountain, Clock, ArrowUp, Shield, CheckCircle2, AlertTriangle, Thermometer, Cloud, Wind, Tent, Calendar, ChevronRight, CookingPot } from 'lucide-react'
import { useState } from 'react'

interface PlanResultProps {
  plan: {
    title: string
    overview: Record<string, any>
    route_analysis: Record<string, any>
    equipment: Record<string, any>
    safety: Record<string, any>
    weather: Record<string, any>
    meal: Record<string, any>
    schedule: any[]
    checklist: string[]
    agents_involved: string[]
  }
}

export default function PlanResult({ plan }: PlanResultProps) {
  const route = plan.route_analysis || {}
  const equip = plan.equipment || {}
  const safety = plan.safety || {}
  const weather = plan.weather || {}
  const meal = plan.meal || {}
  const schedule = plan.schedule || []
  const overview = plan.overview || {}

  // Safety color
  const riskLevel = safety.overall_risk || 'low'
  const riskColors: Record<string, string> = {
    low: 'bg-green-50 border-green-300 text-green-700',
    medium: 'bg-yellow-50 border-yellow-300 text-yellow-700',
    high: 'bg-orange-50 border-orange-300 text-orange-700',
    extreme: 'bg-red-50 border-red-300 text-red-700',
  }
  const riskLabels: Record<string, string> = { low: '低风险', medium: '中等风险', high: '高风险', extreme: '极高风险' }

  return (
    <div className="space-y-4 text-sm">
      {/* Title */}
      <h2 className="text-lg font-bold text-gray-900">{plan.title || '徒步方案'}</h2>

      {/* 1. Route Overview */}
      {route.name && (
        <Section icon={<Map className="w-4 h-4" />} title="路线概览" color="text-blue-600">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
            <StatBox icon={<Map className="w-3.5 h-3.5" />} label="距离" value={`${route.distance_km || overview.distance_km || 0}km`} />
            <StatBox icon={<ArrowUp className="w-3.5 h-3.5" />} label="爬升" value={`${route.elevation_gain_m || overview.elevation_gain_m || 0}m`} />
            <StatBox icon={<Mountain className="w-3.5 h-3.5" />} label="最高" value={`${route.max_elevation_m || 0}m`} />
            <StatBox icon={<Clock className="w-3.5 h-3.5" />} label="天数" value={`${route.duration_days || overview.duration_days || 1}天`} />
          </div>
          <DetailRow label="难度" value={route.difficulty || overview.difficulty || '未知'} />
          <DetailRow label="地形" value={route.terrain} />
          <DetailRow label="起点" value={route.trailhead} />
          <DetailRow label="最佳季节" value={route.best_season} />
          <DetailRow label="水源" value={route.water_sources} />
          {route.notes && <p className="mt-2 text-xs text-gray-500 italic">{route.notes}</p>}
        </Section>
      )}

      {/* 2. Equipment by Category */}
      {equip.equipment_by_category && (
        <Section icon={<Tent className="w-4 h-4" />} title="装备清单" color="text-emerald-600"
          badge={equip.review_result === 'approved' ? `✅ 审核通过 · ${equip.total_items || 0}件` : ''}
        >
          {equip.weight_analysis && (
            <div className="mb-3 text-xs text-gray-500">
              预估总重 <span className="font-semibold text-gray-700">{equip.weight_analysis.estimated_total_kg}kg</span>
              {equip.weight_analysis.target_kg && <> / 目标 {equip.weight_analysis.target_kg}kg</>}
            </div>
          )}

          {/* 个性化调整 */}
          {equip.personalized_adjustments && equip.personalized_adjustments.length > 0 && (
            <div className="mb-3 bg-blue-50 rounded-lg p-2.5">
              <p className="text-xs font-medium text-blue-700 mb-1.5">🎯 个性化装备调整</p>
              {equip.personalized_adjustments.map((adj: any, i: number) => (
                <div key={i} className="flex gap-1.5 text-xs mb-1 last:mb-0">
                  <span className="text-blue-400">•</span>
                  <span className="font-medium text-gray-700">{adj.adjustment}</span>
                  <span className="text-gray-400">— {adj.reason}</span>
                </div>
              ))}
            </div>
          )}

          {/* 个性化建议 */}
          {equip.personalized_notes && (
            <p className="mb-3 text-xs text-gray-500 italic">💡 {equip.personalized_notes}</p>
          )}

          {Object.entries(equip.equipment_by_category as Record<string, any[]>).map(([cat, items]) => (
            <EquipmentCategory key={cat} name={cat} items={items} />
          ))}
        </Section>
      )}

      {/* 3. Safety */}
      {safety.overall_risk && (
        <Section icon={<Shield className="w-4 h-4" />} title="安全评估" color="text-red-600"
          badge={<span className={`px-2 py-0.5 rounded text-xs font-medium ${riskColors[riskLevel]}`}>{riskLabels[riskLevel]}</span>}
        >
          {/* Weather */}
          {safety.weather && (
            <div className="mb-3 bg-blue-50 rounded-lg p-3 text-xs">
              <p className="font-medium text-blue-700 mb-1">🌤️ 天气参考（{safety.weather.location || '当地'}）</p>
              <div className="flex gap-3">
                <span><Thermometer className="w-3 h-3 inline" /> {safety.weather.temperature_high_c}°C / {safety.weather.temperature_low_c}°C</span>
                <span><Cloud className="w-3 h-3 inline" /> {safety.weather.condition}</span>
                <span><Wind className="w-3 h-3 inline" /> {safety.weather.wind_speed_kmh}km/h</span>
              </div>
            </div>
          )}

          {/* Risks */}
          {(safety.risks || []).map((risk: any, i: number) => (
            typeof risk === 'string' ? (
              <div key={i} className="flex gap-2 text-xs text-gray-600 py-1">
                <AlertTriangle className="w-3 h-3 text-yellow-500 mt-0.5 flex-shrink-0" />
                {risk}
              </div>
            ) : (
              <div key={i} className="flex gap-2 text-xs py-1">
                <AlertTriangle className="w-3 h-3 text-yellow-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-medium text-gray-700">{risk.category}:</span>
                  <span className="text-gray-600 ml-1">{risk.detail}</span>
                  {risk.factors?.map((f: string, j: number) => (
                    <p key={j} className="text-gray-400 ml-4">· {f}</p>
                  ))}
                </div>
              </div>
            )
          ))}

          {/* Mitigations */}
          {safety.mitigations && safety.mitigations.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-1">防范措施</p>
              {safety.mitigations.map((m: string, i: number) => (
                <p key={i} className="text-xs text-gray-600">✅ {m}</p>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* 4. Weather (real API data) */}
      {weather.daily && weather.daily.length > 0 && (
        <Section icon={<Cloud className="w-4 h-4" />} title="天气预报" color="text-sky-600"
          badge={weather.hiking_advice ? (
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              weather.hiking_advice.go_nogo === 'no_go' ? 'bg-red-100 text-red-600' :
              weather.hiking_advice.go_nogo === 'conditional_go' ? 'bg-yellow-100 text-yellow-600' :
              'bg-green-100 text-green-600'
            }`}>
              {weather.hiking_advice.go_nogo === 'no_go' ? '⚠️ 不建议' :
               weather.hiking_advice.go_nogo === 'conditional_go' ? '⚠️ 需注意' : '✅ 适宜'}
            </span>
          ) : undefined}
        >
          {/* Daily forecast chips */}
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
            {weather.daily.map((d: any, i: number) => (
              <div key={i} className={`flex-shrink-0 w-20 text-center rounded-lg p-2 ${
                d.is_severe ? 'bg-red-50 border border-red-200' :
                d.is_caution ? 'bg-yellow-50 border border-yellow-200' :
                'bg-gray-50 border border-gray-100'
              }`}>
                <p className="text-[10px] text-gray-500">{d.date?.slice(5)}</p>
                <p className="text-lg my-0.5">{getWeatherEmoji(d.weather_code)}</p>
                <p className="text-[10px] text-gray-400">{d.weather_desc}</p>
                <p className="text-xs font-semibold text-gray-700">{d.temp_min_c?.toFixed(0)}~{d.temp_max_c?.toFixed(0)}°</p>
                <div className="flex justify-center gap-1 mt-1">
                  {d.precip_prob > 30 && <span className="text-[9px] text-blue-500">💧{d.precip_prob}%</span>}
                  {d.wind_max_kmh > 20 && <span className="text-[9px] text-cyan-500">💨{d.wind_max_kmh}</span>}
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          {weather.summary && (
            <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2">{weather.summary}</p>
          )}

          {/* Hiking advice */}
          {weather.hiking_advice && (
            <div className="mt-2">
              {weather.hiking_advice.risk_factors?.length > 0 && (
                <div className="mb-2">
                  {weather.hiking_advice.risk_factors.map((r: string, i: number) => (
                    <p key={i} className="text-xs text-red-600 flex gap-1">⚠️ {r}</p>
                  ))}
                </div>
              )}
              {weather.hiking_advice.gear_notes?.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs font-medium text-gray-500 mb-0.5">🌤️ 天气相关建议</p>
                  {weather.hiking_advice.gear_notes.map((g: string, i: number) => (
                    <p key={i} className="text-xs text-gray-600">· {g}</p>
                  ))}
                </div>
              )}
              <p className="text-xs text-gray-700 font-medium">{weather.hiking_advice.overall}</p>
            </div>
          )}
        </Section>
      )}

      {/* 5. Meal plan */}
      {meal.daily && meal.daily.length > 0 && (
        <Section icon={<CookingPot className="w-4 h-4" />} title="路餐推荐" color="text-amber-600"
          badge={<span className="text-xs text-gray-500">{meal.budget_tier}预算 · {meal.estimated_cost_range}</span>}
        >
          {meal.daily.map((day: any, i: number) => (
            <div key={i} className="mb-3 last:mb-0 border border-amber-100 rounded-lg overflow-hidden">
              <div className="bg-amber-50 px-3 py-2 flex items-center justify-between">
                <p className="font-semibold text-xs text-gray-800">📅 第{day.day}天</p>
                <span className="text-[10px] text-amber-600">{day.total_calories}千卡</span>
              </div>
              <div className="px-3 py-2 space-y-2">
                {day.breakfast?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-orange-500 mb-0.5">🌅 早餐</p>
                    {day.breakfast.map((item: any, j: number) => (
                      <MealItem key={j} item={item} />
                    ))}
                  </div>
                )}
                {day.lunch?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-yellow-500 mb-0.5">☀️ 路餐</p>
                    {day.lunch.map((item: any, j: number) => (
                      <MealItem key={j} item={item} />
                    ))}
                  </div>
                )}
                {day.dinner?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-indigo-500 mb-0.5">🌙 晚餐</p>
                    {day.dinner.map((item: any, j: number) => (
                      <MealItem key={j} item={item} />
                    ))}
                  </div>
                )}
                {day.snacks?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-green-500 mb-0.5">🍪 零食</p>
                    {day.snacks.map((item: any, j: number) => (
                      <MealItem key={j} item={item} compact />
                    ))}
                  </div>
                )}
                {day.hydration && (
                  <p className="text-[10px] text-blue-600 bg-blue-50 rounded px-2 py-1">💧 {day.hydration}</p>
                )}
              </div>
            </div>
          ))}

          {/* Route notes */}
          {meal.route_notes?.length > 0 && (
            <div className="mt-3 bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-medium text-gray-500 mb-1.5">📋 路线饮食贴士</p>
              {meal.route_notes.map((note: string, i: number) => (
                <p key={i} className="text-xs text-gray-600 mb-1 last:mb-0">{note}</p>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* 6. Schedule */}
      {schedule.length > 0 && (
        <Section icon={<Calendar className="w-4 h-4" />} title="日程安排" color="text-purple-600">
          {schedule.map((day: any, i: number) => {
            const hasDetail = day.from && day.to
            return (
              <div key={i} className={`mb-3 last:mb-0 rounded-lg overflow-hidden border ${
                hasDetail ? 'border-purple-100' : 'bg-gray-50'
              }`}>
                {/* Day header */}
                <div className={`px-3 py-2 ${hasDetail ? 'bg-purple-50' : 'bg-gray-50'}`}>
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-gray-800 text-xs">
                      📅 第{day.day || i + 1}天
                      {day.distance_km ? ` · ${day.distance_km}km` : ''}
                      {day.gain_m ? ` · 爬升${day.gain_m}m` : ''}
                    </p>
                    {day.pace && (
                      <span className="text-[10px] text-gray-400">⏱️ {day.pace}</span>
                    )}
                  </div>
                  {hasDetail && (
                    <p className="text-xs text-purple-700 font-medium mt-0.5">
                      {day.from} → {day.to}
                    </p>
                  )}
                  {!hasDetail && day.description && (
                    <p className="text-xs text-gray-600 mt-0.5">{day.description}</p>
                  )}
                </div>

                {/* Detail grid for routes with segment data */}
                {hasDetail && (
                  <div className="px-3 py-2 space-y-1.5">
                    {day.terrain && <DetailTag icon="🏔️" label="地形" value={day.terrain} />}
                    {day.water && <DetailTag icon="💧" label="水源" value={day.water} />}
                    {day.highlights && <DetailTag icon="📸" label="亮点" value={day.highlights} />}
                    {day.risks && <DetailTag icon="⚠️" label="注意" value={day.risks} color="text-red-600" />}
                    {day.notes && (
                      <p className="text-xs text-orange-600 bg-orange-50 rounded px-2 py-1 mt-1">💡 {day.notes}</p>
                    )}
                  </div>
                )}

                {/* Simple time slots for generic routes */}
                {!hasDetail && (
                  <div className="px-3 pb-2 grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {day.morning && <div><span className="text-xs text-orange-500 font-medium">☀️ 上午</span><p className="text-xs text-gray-500">{day.morning}</p></div>}
                    {day.afternoon && <div><span className="text-xs text-yellow-500 font-medium">🌤️ 下午</span><p className="text-xs text-gray-500">{day.afternoon}</p></div>}
                    {day.evening && <div><span className="text-xs text-indigo-500 font-medium">🌙 晚上</span><p className="text-xs text-gray-500">{day.evening}</p></div>}
                  </div>
                )}
              </div>
            )
          })}
        </Section>
      )}

      {/* 7. Checklist */}
      {plan.checklist && plan.checklist.length > 0 && (
        <Section icon={<CheckCircle2 className="w-4 h-4" />} title="行前检查" color="text-green-600">
          <div className="grid grid-cols-2 gap-1">
            {plan.checklist.map((item: string, i: number) => (
              <label key={i} className="flex items-center gap-2 text-xs text-gray-600 p-1.5 hover:bg-gray-50 rounded cursor-pointer">
                <input type="checkbox" className="w-3.5 h-3.5 rounded border-gray-300 text-primary" />
                {item}
              </label>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

// Sub-components

function Section({ icon, title, color, badge, children }: {
  icon: React.ReactNode; title: string; color: string; badge?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-100">
        <span className={color}>{icon}</span>
        <span className="font-semibold text-gray-800 text-xs">{title}</span>
        {badge && <span className="ml-auto text-xs">{badge}</span>}
      </div>
      <div className="px-4 py-3">{children}</div>
    </div>
  )
}

function StatBox({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-2 text-center">
      <div className="flex items-center justify-center gap-1 text-gray-500 mb-0.5">{icon}<span className="text-[10px]">{label}</span></div>
      <p className="text-sm font-bold text-gray-900">{value}</p>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="flex gap-2 py-0.5 text-xs">
      <span className="text-gray-400 w-16 flex-shrink-0">{label}</span>
      <span className="text-gray-700">{value}</span>
    </div>
  )
}

// WMO Weather codes → emoji
function getWeatherEmoji(code: number): string {
  if (code === 0) return '☀️'
  if (code === 1) return '🌤️'
  if (code === 2) return '⛅'
  if (code === 3) return '☁️'
  if (code >= 45 && code <= 48) return '🌫️'
  if (code >= 51 && code <= 55) return '🌧️'
  if (code >= 61 && code <= 65) return '🌧️'
  if (code >= 71 && code <= 75) return '🌨️'
  if (code >= 80 && code <= 82) return '🌦️'
  if (code >= 85 && code <= 86) return '🌨️'
  if (code >= 95) return '⛈️'
  return '🌡️'
}

function DetailTag({ icon, label, value, color = 'text-gray-600' }: { icon: string; label: string; value: string; color?: string }) {
  if (!value) return null
  return (
    <div className="flex gap-1.5 text-xs">
      <span className="text-gray-400 w-5 flex-shrink-0">{icon}</span>
      <span className="text-gray-400 flex-shrink-0">{label}</span>
      <span className={color}>{value}</span>
    </div>
  )
}

function MealItem({ item, compact }: { item: any; compact?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${compact ? 'py-0.5' : 'py-1'} text-xs border-b border-gray-50 last:border-0`}>
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="font-medium text-gray-700 truncate">{item.name}</span>
        {!compact && <span className="text-gray-400 text-[10px]">{item.brand}</span>}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {!compact && item.quantity > 1 && <span className="text-[10px] text-gray-400">x{item.quantity}</span>}
        <span className="text-[10px] text-gray-400">{item.price_est}</span>
        {item.calories && !compact && <span className="text-[10px] text-amber-500">{item.calories}kcal</span>}
      </div>
    </div>
  )
}

function EquipmentCategory({ name, items }: { name: string; items: any[] }) {
  const [open, setOpen] = useState(false)
  if (!items || items.length === 0) return null

  // Count by priority
  const essential = items.filter((i: any) => String(i.priority || '').includes('必备')).length
  const suggested = items.filter((i: any) => String(i.priority || '').includes('建议')).length

  return (
    <div className="mb-1 last:mb-0">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 py-1.5 hover:bg-gray-50 rounded text-xs">
        <ChevronRight className={`w-3 h-3 text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`} />
        <span className="font-medium text-gray-700">{name}</span>
        <span className="text-gray-400">{items.length}件</span>
        {essential > 0 && <span className="text-red-400 text-[10px]">{essential}必备</span>}
        {suggested > 0 && <span className="text-blue-400 text-[10px]">{suggested}建议</span>}
      </button>
      {open && (
        <div className="ml-5 space-y-1">
          {items.map((item: any, i: number) => (
            <div key={i} className="flex items-start gap-2 py-1 text-xs border-b border-gray-50 last:border-0">
              <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                String(item.priority || '').includes('必备') ? 'bg-red-400' : 'bg-blue-400'
              }`} />
              <div className="flex-1 min-w-0">
                <span className="font-medium text-gray-800">{item.name}</span>
                {item.quantity > 1 && <span className="text-gray-400 ml-1">x{item.quantity}</span>}
                {item.notes && <p className="text-gray-400 mt-0.5">{item.notes}</p>}
                {item.brand_suggestions?.length > 0 && (
                  <p className="text-gray-300 mt-0.5 text-[10px]">{item.brand_suggestions.slice(0, 3).join(' / ')}</p>
                )}
              </div>
              <span className={`text-[10px] px-1 py-0.5 rounded flex-shrink-0 ${
                String(item.priority || '').includes('必备') ? 'bg-red-50 text-red-500' : 'bg-blue-50 text-blue-500'
              }`}>{item.priority}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
