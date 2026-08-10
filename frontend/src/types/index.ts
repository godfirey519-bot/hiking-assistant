// 用户
export interface User {
  id: number
  username: string
  email: string
  avatar?: string
  created_at: string
}

// 背包
export interface Backpack {
  id: number
  user_id: number
  name: string
  base_weight: number  // 基础重量(g)
  created_at: string
}

// 装备分类
export interface GearCategory {
  id: number
  name: string
  icon: string
  sort_order: number
}

// 装备条目
export interface GearItem {
  id: number
  user_id: number
  category_id: number
  category?: GearCategory
  backpack_id?: number
  name: string
  brand: string
  model: string
  weight: number  // 重量(g)
  quantity: number
  description: string
  image_url?: string
  created_at: string
}

// 路线
export interface Route {
  id: number
  user_id: number
  name: string
  description: string
  distance: number  // 距离(m)
  elevation_gain: number  // 累计爬升(m)
  elevation_loss: number  // 累计下降(m)
  max_elevation: number
  min_elevation: number
  difficulty: 'easy' | 'moderate' | 'hard' | 'expert'
  duration_days: number
  gpx_file_path?: string
  start_point: string
  end_point: string
  created_at: string
}

// 路线轨迹点
export interface Waypoint {
  lat: number
  lng: number
  ele?: number
  time?: string
  name?: string
}

// 规划方案
export interface Plan {
  id: number
  user_id: number
  route_id?: number
  route?: Route
  title: string
  description: string
  status: 'draft' | 'planning' | 'reviewing' | 'completed' | 'failed'
  start_date: string
  end_date: string
  participants: number
  sections: PlanSection[]
  agent_logs: AgentLog[]
  created_at: string
}

// 方案子部分
export interface PlanSection {
  id: number
  plan_id: number
  type: 'equipment' | 'route' | 'budget' | 'commute' | 'safety' | 'schedule' | 'weather' | 'meal'
  title: string
  content: string  // JSON 格式的详细内容
  agent_name: string
  reviewed_by?: string
  review_result?: 'approved' | 'rejected' | 'needs_modification'
  review_notes?: string
}

// Agent 执行日志
export interface AgentLog {
  id: number
  plan_id: number
  agent_name: string
  role: 'planner' | 'reviewer' | 'orchestrator' | 'synthesizer'
  status: 'running' | 'completed' | 'failed'
  input: string
  output: string
  thinking: string
  started_at: string
  completed_at?: string
}

// 徒步记录
export interface TripRecord {
  id: number
  user_id: number
  plan_id?: number
  route_id?: number
  route?: Route
  title: string
  description: string
  start_date: string
  end_date: string
  actual_distance?: number
  actual_elevation_gain?: number
  rating: number  // 1-5 星
  notes: string
  weather: string
  media: TripMedia[]
  created_at: string
}

// 徒步媒体
export interface TripMedia {
  id: number
  trip_id: number
  file_type: 'image' | 'video'
  file_path: string
  thumbnail_path?: string
  description: string
  taken_at?: string
  created_at: string
}

// API 响应
export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  total: number
  page: number
  page_size: number
}
