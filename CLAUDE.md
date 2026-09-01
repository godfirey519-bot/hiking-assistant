# 徒步助手 (Hiking Assistant)

多 AI Agent 协作的智能徒步规划助手。输入徒步意图 → 6 个 Agent 协作 → 生成完整方案（路线/装备/天气/路餐/安全/日程）。

## 启动

```bash
# 终端1: 后端 (8001)
cd D:\徒步助手\backend
uvicorn app.main:app --host 127.0.0.1 --port 8001

# 终端2: 前端 (5173)
cd D:\徒步助手\frontend
npm run dev

# 浏览器: http://localhost:5173
```

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **后端**: Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + SQLite
- **LLM**: DeepSeek (`deepseek-chat`), key 在 `backend/.env`
- **搜索**: DuckDuckGo (免费), ddgs 库
- **天气**: Open-Meteo (免费, 无需 API Key)

## 核心架构

```
用户输入 → POST /api/plans → asyncio.create_task(工作流)
                                    │
    Phase 1: RouteAnalyst (KB→LLM→WebSearch) → WeatherService → EquipmentPlanner
    Phase 2: EquipmentReviewer + SafetyAssessor (规则引擎)
    Phase 2.5: MealPlanner (知识库)
    Phase 3: Synthesizer (唯一 LLM 调用, ~15s)
                                    │
    前端轮询 GET /api/plans/{id} → 展示方案
```

### Agent 团队 (6 + 2 服务)
| Agent | 方式 | 耗时 |
|-------|------|------|
| RouteAnalyst | KB→LLM→联网搜索 三级 | 秒级/15s/20s |
| WeatherService | Open-Meteo API | 1s |
| EquipmentPlanner | 规则引擎 | 秒级 |
| EquipmentReviewer | 规则引擎 | 秒级 |
| SafetyAssessor | 规则引擎 | 秒级 |
| MealPlanner | 知识库+规则 | 秒级 |
| Synthesizer | LLM (唯一调用) | ~15s |

### 路线查询三级递进
```
知识库 42条 → LLM 模型知识 → DuckDuckGo 联网搜索 → LLM 提取
  秒级             ~15s              ~20s              自动
```

## 关键文件

### 后端
- `app/workflows/plan_workflow.py` — 工作流编排
- `app/agents/route_analyst.py` — 路线分析 + 42条知识库 + 联网搜索
- `app/agents/synthesizer.py` — LLM 汇总（装备个性化/日程/路餐）
- `app/agents/equipment_planner.py` — 装备规则引擎
- `app/services/weather_service.py` — Open-Meteo 天气
- `app/services/meal_service.py` — 路餐知识库（25+食材，3档预算）
- `app/services/search_service.py` — DuckDuckGo 联网搜索
- `app/services/route_coords.py` — 40+路线经纬度
- `app/services/llm_service.py` — DeepSeek/Anthropic 双 provider
- `app/api/equipment.py` — 装备 CRUD（13分类）
- `scripts/batch_collect_routes.py` — 批量采集82条路线
- `scripts/import_routes.py` — 导入采集结果到知识库

### 前端
- `src/pages/Equipment.tsx` — 装备管理（API持久化+首次引导+13分类）
- `src/pages/RoutesPage.tsx` — 路线管理（GPX上传+搜索+136条卡片）
- `src/pages/PlanNew.tsx` — 新建规划入口（聊天式）
- `src/pages/PlanDetail.tsx` — 方案详情（7大区块+Agent日志）
- `src/pages/PlanHistory.tsx` — 历史规划列表
- `src/pages/RouteDetail.tsx` — 路线详情（Leaflet 轨迹地图）
- `src/pages/TripRecords.tsx` / `TripDetail.tsx` — 徒步记录（真实API）
- `src/components/agent/AgentChat.tsx` — 聊天式交互（通用对话+规划分流）
- `src/components/agent/PlanResult.tsx` — 方案展示（7大区块）
- `src/utils/planMapper.ts` — sections→PlanResult 映射（对话/详情复用）
- `src/utils/planIntent.ts` — 规划意图 vs 通用对话分流

### 后端
- `app/api/chat.py` — 通用对话（徒步顾问人设+路线库上下文）

## 已完成功能 (2026-08-05)

- [x] 聊天式 Agent 交互（Q&A→方案）
- [x] **AI 通用对话**（可回答任意问题，徒步话题引导用户生成方案）
- [x] 136条路线知识库（135条有详细日程分段）
- [x] 联网搜索未知路线（DDG + LLM 提取）
- [x] 装备管理（13分类，API持久化，首次引导，预设模板）
- [x] GPX 上传（拖拽+按钮，自动解析距离/爬升/轨迹点）
- [x] **路线详情**（Leaflet 轨迹地图可视化）
- [x] 真实天气 API（Open-Meteo，5天预报，徒步建议）
- [x] 路餐推荐（每日三餐+品牌+价格+预算分层）
- [x] 日程详细分段（起终点/地形/水源/亮点/风险/节奏）
- [x] 装备个性化（LLM 画像提取+6场景自动调整）
- [x] PWA 支持（manifest+service worker+离线缓存）
- [x] 本地存储对话历史
- [x] **历史方案详情**（PlanDetail 7大区块+Agent日志）
- [x] **移动端适配**（390px 无横向溢出，触控目标≥44px）
- [x] **徒步记录创建表单**（modal，标题/日期/距离/爬升/评分/天气/描述/笔记）
- [x] **TripDetail 媒体展示**（后端 `/media` 静态服务 + 页面上传照片/视频 + 大图/内嵌播放）
- [x] **Service Worker 缓存名自动 bump**（`npm run build` 自动注入时间戳版本）
- [x] **历史规划搜索/筛选**（PlanHistory 关键词搜索 + 状态筛选 + 空态）
- [x] **路线对比**（多选勾选 + 对比表格弹窗，数值最低/最高高亮，移动端横向滑动）
- [x] **忘记密码 / 修改密码**（登录页邮箱重置流程 + 设置页改密，dev 模式直接返回重置凭证，E2E 脚本 `verify-password-reset.mjs`）

## 下一步

1. **真实用户测试**（让真人用浏览器走完整流程：规划→装备→历史→记录→传照片）
2. **路线对比 / 离线地图 / 社区分享**（新功能方向）
3. **历史规划搜索/筛选**（Option C）
4. **批量采集路线分段数据质量抽检**（五台山是反面例子）

## 记忆文件

项目记忆存储在 `C:\Users\20755\.claude\projects\D------\memory\`:
- `project-overview.md` — 初始架构
- `project-status.md` — 当前状态
- `session-2026-08-02.md` — 开发记录
