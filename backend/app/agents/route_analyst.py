"""Route Analyst — 50+ 热门路线知识库 + LLM 未知路线查询"""
from app.agents.base import BaseAgent, AgentResult
from app.agents.tools.gpx_tools import analyze_gpx
import json
import logging
import os

logger = logging.getLogger(__name__)

# 加载外部日程分段数据
_SEGMENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "route_segments.json")
_LOADED_SEGMENTS: dict = {}

def _load_segments():
    """加载外部日程分段 JSON 文件"""
    global _LOADED_SEGMENTS
    try:
        if os.path.exists(_SEGMENTS_FILE):
            with open(_SEGMENTS_FILE, "r", encoding="utf-8") as f:
                _LOADED_SEGMENTS = json.load(f)
            logger.info(f"加载日程分段: {len(_LOADED_SEGMENTS)} 条路线")
    except Exception as e:
        logger.warning(f"加载日程分段失败: {e}")
        _LOADED_SEGMENTS = {}

# 中国热门徒步路线知识库（50+ 条）
KNOWN_ROUTES = {
    # ===== 江西 =====
    "武功山": {
        "distance_km": 22, "elevation_gain_m": 1800, "max_elevation_m": 1918,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "高山草甸、碎石坡、木栈道",
        "water_sources": "沿途有客栈可补水",
        "best_season": "5-10月（绿草甸），11-2月（金色草甸+云海）",
        "trailhead": "萍乡市芦溪县沈子村/龙山村",
        "notes": "经典穿越，节假日人流量大，需提前订客栈",
        "segments": [
            {"day": 1, "from": "沈子村(海拔600m)", "to": "金顶(海拔1918m)", "distance_km": 12, "gain_m": 1300,
             "terrain": "竹林→灌木→高山草甸", "water": "沿途2处客栈可补水", "highlights": "金顶日落+云海",
             "risks": "连续爬升大，注意体力分配", "pace": "约6-8小时，建议早上7点前出发"},
            {"day": 2, "from": "金顶(海拔1918m)", "to": "龙山村(海拔500m)", "distance_km": 10, "gain_m": 300,
             "terrain": "山脊草甸→好汉坡碎石→下山土路", "water": "发云界客栈补水", "highlights": "绝望坡日出、草甸云海",
             "risks": "下山台阶多，伤膝盖；好汉坡碎石路滑", "pace": "约5-7小时"},
        ],
    },
    # ===== 云南 =====
    "虎跳峡": {
        "distance_km": 25, "elevation_gain_m": 1200, "max_elevation_m": 2670,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "悬崖栈道、碎石路段",
        "water_sources": "沿途客栈充足",
        "best_season": "3-6月、9-11月",
        "trailhead": "香格里拉市虎跳峡镇",
        "notes": "高路徒步线，部分路段暴露感强",
        "segments": [
            {"day": 1, "from": "虎跳峡镇桥头(海拔1900m)", "to": "茶马客栈/Halfway(海拔2400m)", "distance_km": 12, "gain_m": 500,
             "terrain": "悬崖栈道→碎石路", "water": "纳西雅阁、茶马客栈补水", "highlights": "28道拐、金沙江峡谷、玉龙雪山",
             "risks": "悬崖路段暴露感强，恐高慎入；28道拐爬升急", "pace": "约5-7小时，住Halfway看日照金山"},
            {"day": 2, "from": "茶马客栈(海拔2400m)", "to": "中虎跳→天梯→停车场(海拔1800m)", "distance_km": 13, "gain_m": 400,
             "terrain": "山腰平路→天梯→峡谷底部", "water": "Tina's客栈补水", "highlights": "中虎跳峡激流、天梯登攀",
             "risks": "天梯段垂直攀爬，恐高小心；下峡谷再爬升累人", "pace": "约6-8小时，下午3点前到停车场"},
        ],
    },
    "哈巴雪山": {
        "distance_km": 14, "elevation_gain_m": 2700, "max_elevation_m": 5396,
        "difficulty": "困难", "duration_days": 3,
        "terrain": "原始森林、高山草甸、雪线以上",
        "water_sources": "大本营有水源",
        "best_season": "4-6月、9-11月",
        "trailhead": "香格里拉哈巴村",
        "notes": "入门级雪山，需冰镐冰爪，建议请向导",
    },
    "梅里北坡": {
        "distance_km": 50, "elevation_gain_m": 4000, "max_elevation_m": 5200,
        "difficulty": "困难", "duration_days": 5,
        "terrain": "冰川、碎石坡、高山草甸",
        "water_sources": "冰川融水",
        "best_season": "6-10月",
        "trailhead": "德钦县亚贡村",
        "notes": "高海拔重装，需适应2天以上",
    },
    "尼汝徒步": {
        "distance_km": 30, "elevation_gain_m": 1500, "max_elevation_m": 4000,
        "difficulty": "中等", "duration_days": 3,
        "terrain": "原始森林、高山牧场、彩林",
        "water_sources": "沿途溪流",
        "best_season": "5-10月",
        "trailhead": "香格里拉尼汝村",
        "notes": "小众秘境，秋季彩林绝美",
    },
    "苍山徒步": {
        "distance_km": 18, "elevation_gain_m": 1800, "max_elevation_m": 4122,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "原始森林、山脊线、碎石路",
        "water_sources": "山泉",
        "best_season": "3-5月、10-11月",
        "trailhead": "大理古城→感通寺/中和寺",
        "notes": "可俯瞰洱海，注意高反",
    },

    # ===== 四川 =====
    "四姑娘山二峰": {
        "distance_km": 32, "elevation_gain_m": 2100, "max_elevation_m": 5276,
        "difficulty": "困难", "duration_days": 2,
        "terrain": "高山草甸、碎石坡、雪线以上",
        "water_sources": "大本营有水源",
        "best_season": "6-10月",
        "trailhead": "小金县日隆镇",
        "notes": "5000米级入门雪山，需冰爪冰镐",
        "segments": [
            {"day": 1, "from": "日隆镇(3200m)", "to": "大本营(4300m)", "distance_km": 16, "gain_m": 1100,
             "terrain": "森林→高山草甸→碎石坡", "water": "大本营溪流", "highlights": "四姑娘山全景、花海",
             "risks": "海拔爬升1100m，高反风险；碎石坡路滑", "pace": "6-8小时，下午2点前到适应海拔"},
            {"day": 2, "from": "大本营(4300m)", "to": "冲顶(5276m)→下撤回日隆", "distance_km": 16, "gain_m": 1000,
             "terrain": "碎石坡→雪线→山脊", "water": "出发前装满，途中无水源", "highlights": "冲顶日出、云海、幺妹峰",
             "risks": "凌晨2点出发；雪线需冰爪；高反+失温极高风险", "pace": "冲顶4-6h+下撤3h，下午撤出"},
        ],
    },
    "四姑娘山大峰": {
        "distance_km": 24, "elevation_gain_m": 1800, "max_elevation_m": 5025,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "高山草甸、碎石坡",
        "water_sources": "大本营有水源",
        "best_season": "6-10月",
        "trailhead": "日隆镇海子沟",
        "notes": "最易5000米级雪山，适合初次雪山体验",
    },
    "长穿毕": {
        "distance_km": 36, "elevation_gain_m": 1500, "max_elevation_m": 4668,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "原始森林、高山草甸、垭口",
        "water_sources": "沿途溪流",
        "best_season": "6-10月",
        "trailhead": "理县毕棚沟/长坪沟",
        "notes": "经典穿越，需翻越4668m垭口",
    },
    "贡嘎大环线": {
        "distance_km": 80, "elevation_gain_m": 4000, "max_elevation_m": 4920,
        "difficulty": "专业级", "duration_days": 6,
        "terrain": "原始森林、高山草甸、冰川、垭口",
        "water_sources": "沿途河流",
        "best_season": "5-10月",
        "trailhead": "康定老榆林/草科",
        "notes": "蜀山之王转山，需重装或雇马帮",
    },
    "格聂C线": {
        "distance_km": 80, "elevation_gain_m": 3500, "max_elevation_m": 5000,
        "difficulty": "困难", "duration_days": 7,
        "terrain": "原始森林、高山草甸、雪山、海子",
        "water_sources": "沿途河流湖泊",
        "best_season": "6-10月",
        "trailhead": "理塘县喇嘛垭乡",
        "notes": "川西秘境，格聂神山转山，需雇向导马帮",
    },
    "格聂V线": {
        "distance_km": 55, "elevation_gain_m": 2500, "max_elevation_m": 4800,
        "difficulty": "较难", "duration_days": 5,
        "terrain": "高山草甸、原始森林、海子群",
        "water_sources": "沿途海子",
        "best_season": "6-10月",
        "trailhead": "理塘县喇嘛垭乡",
        "notes": "格聂精华版，海子群绝美",
    },
    "稻城亚丁": {
        "distance_km": 14, "elevation_gain_m": 1000, "max_elevation_m": 4700,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "高原湖泊、雪山、原始森林",
        "water_sources": "景区内补给点",
        "best_season": "9-10月（秋色最佳）",
        "trailhead": "稻城县香格里拉镇→亚丁村",
        "notes": "牛奶海/五色海海拔高，注意高反",
        "segments": [
            {"day": 1, "from": "香格里拉镇(2900m)", "to": "亚丁村→冲古寺→珍珠海→返回亚丁村(3900m)", "distance_km": 6, "gain_m": 400,
             "terrain": "观光车道→森林木栈道", "water": "冲古寺补给点", "highlights": "仙乃日神山、珍珠海倒影、冲古寺",
             "risks": "第一天适应海拔，慢走防高反；亚丁村住宿条件简陋", "pace": "约3-4小时，轻松适应日"},
            {"day": 2, "from": "亚丁村(3900m)", "to": "洛绒牛场→牛奶海→五色海→返回(最高4700m)", "distance_km": 8, "gain_m": 600,
             "terrain": "栈道→碎石路→高原湖泊", "water": "洛绒牛场最后一个补给点", "highlights": "央迈勇雪山、牛奶海(蓝绿色)、五色海(最高点4700m)",
             "risks": "海拔4700m高反风险极高；碎石路段湿滑；下午2点前必须下撤", "pace": "约6-9小时，早上6点出发，下午3点前下山"},
        ],
    },
    "洛克线": {
        "distance_km": 70, "elevation_gain_m": 4000, "max_elevation_m": 4800,
        "difficulty": "专业级", "duration_days": 5,
        "terrain": "原始森林、高山草甸、垭口、海子",
        "water_sources": "沿途河流湖泊",
        "best_season": "6-10月",
        "trailhead": "木里县嘟噜村→亚丁",
        "notes": "中国十大徒步路线之一，需雇马帮",
    },
    "七藏沟": {
        "distance_km": 45, "elevation_gain_m": 2000, "max_elevation_m": 4200,
        "difficulty": "较难", "duration_days": 4,
        "terrain": "原始森林、高山海子、草甸",
        "water_sources": "沿途溪流",
        "best_season": "6-10月",
        "trailhead": "松潘县川主寺",
        "notes": "九寨沟后花园，海子不输九寨",
    },
    "雅拉雪山": {
        "distance_km": 35, "elevation_gain_m": 2000, "max_elevation_m": 4200,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "原始森林、高山草甸、垭口",
        "water_sources": "沿途溪流",
        "best_season": "6-10月",
        "trailhead": "康定中谷村/道孚八美",
        "notes": "雅拉神山穿越，秋季彩林绝美",
    },
    "党岭穿越": {
        "distance_km": 28, "elevation_gain_m": 1800, "max_elevation_m": 4300,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "原始森林、高山海子、温泉",
        "water_sources": "沿途溪流",
        "best_season": "6-10月",
        "trailhead": "丹巴县党岭村",
        "notes": "葫芦海绝美，可泡野温泉",
    },

    # ===== 陕西 =====
    "太白山南北穿越": {
        "distance_km": 45, "elevation_gain_m": 3000, "max_elevation_m": 3767,
        "difficulty": "困难", "duration_days": 3,
        "terrain": "石海、高山草甸、原始森林",
        "water_sources": "大爷海、二爷海",
        "best_season": "6-10月",
        "trailhead": "眉县汤峪/周至厚畛子",
        "notes": "鳌太线精华段，天气多变需备防雨保暖",
        "segments": [
            {"day": 1, "from": "汤峪(海拔600m)", "to": "下板寺→上板寺→大爷海(海拔3590m)", "distance_km": 18, "gain_m": 2990,
             "terrain": "针叶林→高山杜鹃→石海", "water": "大爷海（高山湖泊）", "highlights": "太白山石海、大爷海日落",
             "risks": "单日爬升近3000m，强度极大；海拔骤升注意高反；下午石海路段易迷路",
             "pace": "约9-11小时，建议早上5点出发，务必天黑前到大爷海"},
            {"day": 2, "from": "大爷海(3590m)", "to": "拔仙台(3767m)→跑马梁→老庙子", "distance_km": 15, "gain_m": 400,
             "terrain": "石海山脊→草甸", "water": "老庙子营地有水源", "highlights": "拔仙台日出(秦岭最高点)、跑马梁云海",
             "risks": "跑马梁暴露感强，大风天危险；天气变化极快，随时准备下撤",
             "pace": "约7-9小时，凌晨出发看拔仙台日出"},
            {"day": 3, "from": "老庙子", "to": "厚畛子(海拔1200m)", "distance_km": 12, "gain_m": 200,
             "terrain": "原始森林下山路", "water": "沿途溪流", "highlights": "秦岭原始森林",
             "risks": "长距离下坡伤膝盖；森林路段雨后湿滑", "pace": "约5-6小时，下午到达厚畛子"},
        ],
    },
    "鳌太线": {
        "distance_km": 80, "elevation_gain_m": 5000, "max_elevation_m": 3767,
        "difficulty": "专业级", "duration_days": 5,
        "terrain": "石海、高山草甸、山脊线",
        "water_sources": "季节性水源，需提前规划",
        "best_season": "6-9月",
        "trailhead": "太白县鳌山登山口",
        "notes": "中国十大顶级路线，天气多变极为危险，已管制",
    },

    # ===== 西藏 =====
    "珠峰东坡": {
        "distance_km": 80, "elevation_gain_m": 5000, "max_elevation_m": 5350,
        "difficulty": "专业级", "duration_days": 7,
        "terrain": "原始森林、高山草甸、冰川、垭口",
        "water_sources": "冰川融水",
        "best_season": "5-6月、9-10月",
        "trailhead": "定日县曲当乡",
        "notes": "世界顶级徒步路线，需雇牦牛队",
    },
    "冈仁波齐转山": {
        "distance_km": 52, "elevation_gain_m": 1000, "max_elevation_m": 5630,
        "difficulty": "困难", "duration_days": 2,
        "terrain": "高原土路、碎石坡、垭口",
        "water_sources": "沿途补给点",
        "best_season": "5-10月",
        "trailhead": "阿里地区塔钦",
        "notes": "海拔极高注意高反，卓玛拉垭口5630m",
    },
    "库拉岗日": {
        "distance_km": 35, "elevation_gain_m": 2000, "max_elevation_m": 5100,
        "difficulty": "困难", "duration_days": 3,
        "terrain": "高山海子、冰川、草甸",
        "water_sources": "沿途湖泊",
        "best_season": "5-10月",
        "trailhead": "洛扎县色乡",
        "notes": "西藏新晋网红路线，白马林措绝美",
    },
    "墨脱徒步": {
        "distance_km": 78, "elevation_gain_m": 3000, "max_elevation_m": 4200,
        "difficulty": "困难", "duration_days": 4,
        "terrain": "原始森林、热带雨林、雪山垭口",
        "water_sources": "沿途河流瀑布",
        "best_season": "5-11月",
        "trailhead": "派镇松林口→墨脱县城",
        "notes": "中国十大顶级路线，从雪山到热带雨林",
    },
    "希夏邦马": {
        "distance_km": 60, "elevation_gain_m": 3000, "max_elevation_m": 5500,
        "difficulty": "专业级", "duration_days": 5,
        "terrain": "冰川、高山草甸、垭口",
        "water_sources": "冰川融水",
        "best_season": "5-6月、9-10月",
        "trailhead": "聂拉木县",
        "notes": "唯一全境在中国8000米级雪山",
    },

    # ===== 新疆 =====
    "喀纳斯徒步": {
        "distance_km": 55, "elevation_gain_m": 1500, "max_elevation_m": 2400,
        "difficulty": "中等", "duration_days": 3,
        "terrain": "原始森林、草原、湖泊",
        "water_sources": "沿途河流",
        "best_season": "6-9月（绿）9-10月（秋色）",
        "trailhead": "贾登峪→禾木→喀纳斯",
        "notes": "中国最美秋色徒步路线之一",
    },
    "乌孙古道": {
        "distance_km": 120, "elevation_gain_m": 4000, "max_elevation_m": 3900,
        "difficulty": "专业级", "duration_days": 6,
        "terrain": "原始森林、高山草甸、冰川、河流",
        "water_sources": "沿途河流",
        "best_season": "6-10月",
        "trailhead": "特克斯县琼库什台→拜城黑英山",
        "notes": "新疆三大顶级路线，需雇马帮，多次涉水",
    },
    "夏特古道": {
        "distance_km": 100, "elevation_gain_m": 3500, "max_elevation_m": 3580,
        "difficulty": "专业级", "duration_days": 5,
        "terrain": "冰川、原始森林、河流",
        "water_sources": "冰川融水",
        "best_season": "5-6月、9-10月",
        "trailhead": "昭苏县夏特乡→温宿破城子",
        "notes": "新疆三大路线之一，需雇马帮过冰川",
    },
    "狼塔C线": {
        "distance_km": 120, "elevation_gain_m": 6000, "max_elevation_m": 4000,
        "difficulty": "专业级", "duration_days": 7,
        "terrain": "原始森林、高山草甸、冰川、垭口",
        "water_sources": "沿途河流",
        "best_season": "6-9月",
        "trailhead": "呼图壁县白杨沟→巴伦台",
        "notes": "中国最虐徒步路线，多次涉水过河",
    },
    "天山穿越": {
        "distance_km": 70, "elevation_gain_m": 3000, "max_elevation_m": 3600,
        "difficulty": "困难", "duration_days": 5,
        "terrain": "原始森林、草原、雪山",
        "water_sources": "沿途河流",
        "best_season": "6-9月",
        "trailhead": "独库公路乔尔玛",
        "notes": "穿越天山南北，风景壮阔",
    },

    # ===== 内蒙古 =====
    "腾格里沙漠": {
        "distance_km": 50, "elevation_gain_m": 200, "max_elevation_m": 1500,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "沙漠、绿洲、湖泊",
        "water_sources": "需自背或后勤车补给",
        "best_season": "4-6月、9-10月",
        "trailhead": "阿拉善左旗",
        "notes": "沙漠徒步需注意防晒防沙，建议后勤保障",
    },

    # ===== 北京周边 =====
    "长城箭扣": {
        "distance_km": 10, "elevation_gain_m": 600, "max_elevation_m": 1000,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "野长城、陡坡、断崖",
        "water_sources": "自备（全程无补给）",
        "best_season": "4-5月（山花）、9-10月（红叶）",
        "trailhead": "怀柔西栅子村→慕田峪方向",
        "notes": "野长城最险段，部分需攀爬。务必带走所有垃圾！",
        "segments": [
            {"day": 1, "from": "西栅子村(长城脚下)", "to": "箭扣→天梯→鹰飞倒仰→北京结→西栅子村(环线)", "distance_km": 10, "gain_m": 600,
             "terrain": "野长城城墙→碎石陡坡→断崖攀爬", "water": "全程无补给！自带3L水",
             "highlights": "箭扣日出、鹰飞倒仰(最险段)、北京结(三岔长城)、慕田峪全景",
             "risks": "天梯段接近垂直攀爬；鹰飞倒仰有坠落风险(已有多起事故)；碎石坡极滑",
             "pace": "约5-7小时环线，需一定攀爬能力，恐高慎入。早6点出发中午前下山"},
        ],
    },

    # ===== 安徽/浙江 =====
    "徽杭古道": {
        "distance_km": 20, "elevation_gain_m": 800, "max_elevation_m": 1050,
        "difficulty": "较易", "duration_days": 1,
        "terrain": "石板路、古道",
        "water_sources": "沿途村庄+补给点",
        "best_season": "全年（春秋最佳）",
        "trailhead": "绩溪县伏岭镇→临安区浙基田",
        "notes": "入门级古道，文化底蕴深厚",
        "segments": [
            {"day": 1, "from": "绩溪伏岭镇(江南第一关)", "to": "临安浙基田(古道出口)", "distance_km": 20, "gain_m": 800,
             "terrain": "古道石板→蓝天凹草甸→下山小路", "water": "黄茅培村、下雪堂、蓝天凹均有补给",
             "highlights": "江南第一关、蓝天凹(最高点)、徽派古村落",
             "risks": "石板路雨天湿滑；蓝天凹下山路段陡峭",
             "pace": "约5-7小时，轻松一日穿越"},
        ],
    },
    "黄山徒步": {
        "distance_km": 15, "elevation_gain_m": 1200, "max_elevation_m": 1864,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "石阶路、悬崖栈道",
        "water_sources": "山上有售",
        "best_season": "3-5月、9-11月",
        "trailhead": "汤口镇云谷寺/慈光阁",
        "notes": "建议缆车上徒步下或反向",
    },

    # ===== 福建 =====
    "武夷山徒步": {
        "distance_km": 18, "elevation_gain_m": 1000, "max_elevation_m": 717,
        "difficulty": "较易", "duration_days": 2,
        "terrain": "石阶路、原始森林、溪流",
        "water_sources": "景区补给",
        "best_season": "3-5月、10-11月",
        "trailhead": "武夷山市星村镇",
        "notes": "九曲溪竹筏+徒步结合",
    },

    # ===== 贵州 =====
    "梵净山": {
        "distance_km": 12, "elevation_gain_m": 1400, "max_elevation_m": 2572,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、悬崖栈道",
        "water_sources": "景区补给",
        "best_season": "4-10月",
        "trailhead": "江口县黑湾河",
        "notes": "8000级台阶，红云金顶绝景",
    },

    # ===== 广东 =====
    "船底顶": {
        "distance_km": 25, "elevation_gain_m": 2000, "max_elevation_m": 1586,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "原始森林、溪谷、草甸",
        "water_sources": "沿途溪流",
        "best_season": "10-5月",
        "trailhead": "韶关市罗坑镇/英德",
        "notes": "广东户外毕业线，地形复杂",
    },

    # ===== 香港 =====
    "麦理浩径": {
        "distance_km": 100, "elevation_gain_m": 4500, "max_elevation_m": 957,
        "difficulty": "困难", "duration_days": 4,
        "terrain": "海岸线、山脊、沙滩、石阶",
        "water_sources": "沿途补给点、士多店",
        "best_season": "10-4月（避开夏季台风和酷暑）",
        "trailhead": "西贡北潭涌→屯门",
        "notes": "香港最经典长线，第二段最美。沿途士多店多，可轻装补给。",
        "segments": [
            {"day": 1, "from": "北潭涌(起点)", "to": "水浪窝营地(第3段终点)", "distance_km": 33, "gain_m": 1300,
             "terrain": "石阶路→山脊→沙滩(第1-3段)", "water": "西湾村士多、咸田湾士多",
             "highlights": "万宜水库(六角柱石)、浪茄湾沙滩、西湾山全景、咸田湾",
             "risks": "首日距离长(33km)，体力消耗大；夏季暴晒无遮荫；第2段西湾山连续爬升",
             "pace": "约9-11小时，建议早上6点出发，天黑前到达水浪窝"},
            {"day": 2, "from": "水浪窝(第3段终点)", "to": "大埔公路(第6段终点)", "distance_km": 28, "gain_m": 1300,
             "terrain": "丛林山脊→猴山→城市景观(第4-6段)", "water": "昂平营地、城门水塘",
             "highlights": "马鞍山山脊线、昂平大草原(滑翔伞)、狮子山远眺九龙、城门水塘",
             "risks": "第4段马鞍山暴露感强，大风天小心；第6段金山郊野公园有猴子，勿喂食",
             "pace": "约8-10小时"},
            {"day": 3, "from": "大埔公路(第6段终点)", "to": "荃锦公路(第8段终点)", "distance_km": 16, "gain_m": 900,
             "terrain": "城门水塘→针山→草山→大帽山(第7-8段)", "water": "铅矿坳营地、大帽山游客中心",
             "highlights": "针山(尖峰)、大帽山(香港最高峰957m)、俯瞰新界全景",
             "risks": "针山陡升急降伤膝；大帽山天气多变，山顶常大雾大风",
             "pace": "约6-8小时，相对轻松的一天"},
            {"day": 4, "from": "荃锦公路(第8段终点)", "to": "屯门(终点/M200标距柱)", "distance_km": 23, "gain_m": 1000,
             "terrain": "山林小径→冲沟→水塘(第9-10段)", "water": "田夫仔营地、大榄涌水塘",
             "highlights": "大榄涌水塘(千岛湖)、终点M200里程碑",
             "risks": "最后一天体力下降注意安全；第9段部分路段被山洪冲毁，须绕行",
             "pace": "约7-9小时，下午到达屯门，终点有轻铁回市区"},
        ],
    },

    # ===== 山西 =====
    "五台山大朝台": {
        "distance_km": 55, "elevation_gain_m": 2100, "max_elevation_m": 3058,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "高山草甸、石板路",
        "water_sources": "寺庙补给",
        "best_season": "6-9月",
        "trailhead": "五台县鸿门岩",
        "notes": "顺时针大朝台：鸿门岩→东台→北台→中台→西台→南台→台怀镇，可在寺庙挂单住宿",
    },

    # ===== 河南 =====
    "太行山徒步": {
        "distance_km": 25, "elevation_gain_m": 1500, "max_elevation_m": 1700,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "悬崖绝壁、挂壁公路、峡谷",
        "water_sources": "沿途村庄",
        "best_season": "4-6月、9-10月",
        "trailhead": "辉县郭亮村/陵川王莽岭",
        "notes": "南太行最险段，挂壁公路绝景",
    },

    # ===== 甘肃 =====
    "扎尕那": {
        "distance_km": 55, "elevation_gain_m": 3500, "max_elevation_m": 4200,
        "difficulty": "较难", "duration_days": 4,
        "terrain": "高山草甸、碎石坡、峡谷、森林、垭口",
        "water_sources": "溪流、泉水（季节性）",
        "best_season": "6-9月",
        "trailhead": "迭部县扎尕那村(海拔约3000m)→卓尼县三角石",
        "notes": "藏区秘境，石头城穿越。雨季注意山洪，需雇佣向导+马帮",
    },

    # ===== 湖北 =====
    "神农架": {
        "distance_km": 30, "elevation_gain_m": 2000, "max_elevation_m": 3105,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "原始森林、高山草甸",
        "water_sources": "山泉溪流",
        "best_season": "5-10月",
        "trailhead": "木鱼镇",
        "notes": "神秘原始森林，生物多样性丰富",
    },

    # ===== 新疆采集 (23条) =====
    "车师古道": {
        "distance_km": 45, "elevation_gain_m": 1800, "max_elevation_m": 3400,
        "difficulty": "中等偏难", "duration_days": 3,
        "terrain": "山地、河谷、草原、达坂",
        "water_sources": "沿途有溪流和泉水，需过滤或煮沸后饮用",
        "best_season": "6月至9月",
        "trailhead": "新疆吐鲁番市大河沿镇（南端起点）",
        "notes": "车师古道是古代连接天山南北的重要通道，全程需翻越琼达坂，海拔较高，天气多变，建议结伴而行并携带专业装备。",
    },  # 新疆

    "博格达徒步": {
        "distance_km": 139, "elevation_gain_m": 3200, "max_elevation_m": 4500,
        "difficulty": "极高", "duration_days": 8,
        "terrain": "冰川、碎石坡、高山草甸、雪地",
        "water_sources": "冰川融水、溪流、湖泊",
        "best_season": "6月至9月",
        "trailhead": "新疆阜康市白杨沟",
        "notes": "需办理进山手续，配备专业向导和装备，注意高反和天气变化",
    },  # 新疆

    "库尔德宁徒步": {
        "distance_km": 8, "elevation_gain_m": 100, "max_elevation_m": 2450,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "草原、山地、森林",
        "water_sources": "沿途有溪流，需确认季节性水源",
        "best_season": "6月至9月",
        "trailhead": "喀拉峻洗羊池",
        "notes": "该路线为琼库什台至库尔德宁徒步的其中一段，实际全程约8天，此段为第一天行程，从伊宁市出发经特克斯至加撒干营地，徒步距离约8公里，无大爬升，适合适应海拔。",
    },  # 新疆

    "巴尔鲁克徒步": {
        "distance_km": 45, "elevation_gain_m": 1800, "max_elevation_m": 2800,
        "difficulty": "中等偏难", "duration_days": 3,
        "terrain": "山地草原、针叶林、碎石坡、河谷",
        "water_sources": "多处溪流及季节性泉水，需提前确认",
        "best_season": "6月至9月",
        "trailhead": "新疆塔城地区裕民县巴尔鲁克山景区入口",
        "notes": "路线位于边境地带，需提前办理边防证；天气多变，注意防雨保暖；部分路段信号弱，建议结伴并携带GPS。",
    },  # 新疆

    "恰西草原徒步": {
        "distance_km": 17, "elevation_gain_m": 200, "max_elevation_m": 1800,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "草原、丘陵、森林边缘",
        "water_sources": "溪流、季节性河流",
        "best_season": "6月至9月",
        "trailhead": "恰西草原景区入口",
        "notes": "适合作为喀拉峻徒步的辅助路线，可结合恰塔环线；部分路段可乘车，建议根据体力选择徒步或乘车。",
    },  # 新疆

    "禾木徒步": {
        "distance_km": 65, "elevation_gain_m": 1200, "max_elevation_m": 2400,
        "difficulty": "中等偏难", "duration_days": 4,
        "terrain": "森林、河谷、草原、木桥、山地",
        "water_sources": "禾木河及沿途溪流",
        "best_season": "9月中旬至10月初（秋季）",
        "trailhead": "贾登峪",
        "notes": "经典路线为贾登峪至禾木村，可延伸至喀纳斯湖。秋季白桦林金黄，风景绝佳。部分路段需涉水，注意天气变化和保暖。",
    },  # 新疆

    "白哈巴徒步": {
        "distance_km": 18, "elevation_gain_m": 800, "max_elevation_m": 2400,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地草甸、森林小径、河谷",
        "water_sources": "沿途有溪流，需携带净水设备",
        "best_season": "6月至9月",
        "trailhead": "喀纳斯景区游客中心",
        "notes": "白哈巴村位于中国与哈萨克斯坦边境，需办理边防证；徒步路线可结合喀纳斯至白哈巴段，全程约18公里，海拔起伏较大，建议预留充足时间；部分路段可骑马替代徒步。",
    },  # 新疆

    "琼库什台徒步": {
        "distance_km": 120, "elevation_gain_m": 3200, "max_elevation_m": 3800,
        "difficulty": "高", "duration_days": 6,
        "terrain": "森林、河谷、草原、达坂、碎石坡",
        "water_sources": "河流、溪流、高山湖泊（需净化）",
        "best_season": "6月至9月",
        "trailhead": "琼库什台村（乌孙古道起点）",
        "notes": "需重装或马帮驮运，部分路段需涉水，天气多变，需有高海拔徒步经验，建议结伴并提前办理边防手续。",
    },  # 新疆

    "可可托海徒步": {
        "distance_km": 60, "elevation_gain_m": 1800, "max_elevation_m": 2400,
        "difficulty": "中等偏难", "duration_days": 4,
        "terrain": "河谷、森林、草原、石海、达坂",
        "water_sources": "额尔齐斯河支流、季节性溪流（夏季可靠，秋季需备水）",
        "best_season": "6月至9月",
        "trailhead": "可可托海镇（新疆富蕴县）",
        "notes": "需办理边境通行证，部分路段无信号，建议结伴并携带GPS；昼夜温差大，注意防寒和防晒。",
    },  # 新疆

    "帕米尔高原徒步": {
        "distance_km": 120, "elevation_gain_m": 1800, "max_elevation_m": 4500,
        "difficulty": "高", "duration_days": 7,
        "terrain": "高原山地、冰川、戈壁、草原",
        "water_sources": "冰川融水、高山湖泊、季节性河流",
        "best_season": "6-9月",
        "trailhead": "喀什地区塔什库尔干塔吉克自治县",
        "notes": "海拔高，需适应高原环境；部分路段需越野车接驳；注意防寒防晒，备足氧气和药品",
    },  # 新疆

    "友谊峰徒步": {
        "distance_km": 120, "elevation_gain_m": 3500, "max_elevation_m": 4374,
        "difficulty": "极难", "duration_days": 10,
        "terrain": "冰川、雪原、高山碎石坡、河谷",
        "water_sources": "冰川融水、高山湖泊、季节性河流",
        "best_season": "7月至9月",
        "trailhead": "新疆阿勒泰地区布尔津县禾木村",
        "notes": "需办理边防证，必须聘请当地向导，配备专业冰川装备，注意高原反应和极端天气，全程无补给点",
    },  # 新疆

    "慕士塔格徒步": {
        "distance_km": 120, "elevation_gain_m": 1800, "max_elevation_m": 7546,
        "difficulty": "极高", "duration_days": 7,
        "terrain": "冰川、碎石坡、雪原、高山草甸",
        "water_sources": "冰川融水、夏季牧场溪流（需净化）",
        "best_season": "6月至8月",
        "trailhead": "新疆喀什地区塔什库尔干塔吉克自治县苏巴什村",
        "notes": "慕士塔格峰为海拔7546米的雪山，常规徒步路线为苏巴什村至夏牧场，属高海拔适应与冰川行进，需专业向导、高山协作及全套冰雪装备，存在高原反应和极端天气风险，非普通徒步路线，建议提前进行高海拔适应训练。",
    },  # 新疆

    "塔什库尔干徒步": {
        "distance_km": 80, "elevation_gain_m": 2200, "max_elevation_m": 4700,
        "difficulty": "高", "duration_days": 6,
        "terrain": "高原山地、河谷、碎石坡、冰川末端",
        "water_sources": "冰川融水、河谷溪流（需净化）",
        "best_season": "6-9月",
        "trailhead": "塔什库尔干县城（塔县）",
        "notes": "位于帕米尔高原，海拔高、昼夜温差大，需提前适应高原，办理边防证，注意防寒防晒，部分路段需涉水或绕行冰川，建议结伴并备好卫星通信设备。",
    },  # 新疆

    "莎车古道": {
        "distance_km": 120, "elevation_gain_m": 3500, "max_elevation_m": 4200,
        "difficulty": "高", "duration_days": 7,
        "terrain": "峡谷、碎石坡、达坂、河谷、草原",
        "water_sources": "季节性河流、冰川融水（需过滤）",
        "best_season": "6月至9月",
        "trailhead": "新疆喀什地区莎车县喀群乡",
        "notes": "需办理边防证，部分路段需涉水，建议结伴并聘请当地向导，注意高原反应和天气突变。",
    },  # 新疆

    "古尔班通古特沙漠徒步": {
        "distance_km": 80, "elevation_gain_m": 200, "max_elevation_m": 800,
        "difficulty": "高", "duration_days": 6,
        "terrain": "沙漠、沙丘、盐碱地、梭梭林",
        "water_sources": "需全程自备饮水，沿途无可靠水源，需提前规划补给点",
        "best_season": "4-5月或9-10月，避开夏季高温和冬季严寒",
        "trailhead": "新疆昌吉州奇台县或北屯市附近，通常从沙漠边缘的公路起点进入",
        "notes": "古尔班通古特沙漠为中国第二大沙漠，冬季寒冷夏季酷热，徒步需防风沙、防脱水，建议携带GPS和卫星电话，结伴而行，部分区域为自然保护区需提前报备",
    },  # 新疆

    "塔克拉玛干沙漠穿越": {
        "distance_km": 90, "elevation_gain_m": 800, "max_elevation_m": 1500,
        "difficulty": "极难", "duration_days": 10,
        "terrain": "流动沙丘、盐碱地、戈壁、沙漠公路",
        "water_sources": "需全程自备，沿途无可靠水源，需依赖补给点或提前埋藏",
        "best_season": "10月至次年4月（避开夏季高温）",
        "trailhead": "麦盖提县N39°沙漠旅游景区（西南边缘）",
        "notes": "必须聘请当地向导，严禁独自进入；需办理边防证和保护区许可；沙暴频发，需携带卫星电话、GPS、防风镜和充足饮水；冬季夜间气温可降至-20℃，夏季地表超70℃；全程无补给，需骆驼或越野车伴随保障。",
    },  # 新疆

    "巩乃斯徒步": {
        "distance_km": 35, "elevation_gain_m": 1200, "max_elevation_m": 2800,
        "difficulty": "中等", "duration_days": 3,
        "terrain": "草原、河谷、森林、山地",
        "water_sources": "巩乃斯河及支流，沿途有溪流",
        "best_season": "6月至9月",
        "trailhead": "巩乃斯国家森林公园入口",
        "notes": "路线以草原和河谷为主，部分路段需涉水，注意天气变化和野生动物，建议结伴出行。",
    },  # 新疆

    "大海道徒步": {
        "distance_km": 120, "elevation_gain_m": 800, "max_elevation_m": 1200,
        "difficulty": "高", "duration_days": 5,
        "terrain": "戈壁、雅丹、沙地、干涸河床",
        "water_sources": "需全程自备，沿途无可靠水源",
        "best_season": "4-5月、9-10月",
        "trailhead": "新疆哈密市五堡乡",
        "notes": "极端干旱区，需专业向导，备足水和补给，注意防风沙和高温",
    },  # 新疆

    "独库公路徒步": {
        "distance_km": 70, "elevation_gain_m": 6100, "max_elevation_m": 3400,
        "difficulty": "极难", "duration_days": 15,
        "terrain": "柏油公路、高山草甸、峡谷、达坂、雪山路段",
        "water_sources": "沿线河流（奎屯河、喀什河、库车河）及夏季融雪溪流，部分路段需自备水",
        "best_season": "6月至9月（全线通车期，7-8月最佳）",
        "trailhead": "北起独山子（G217起点），南至库车",
        "notes": "独库公路为公路，非传统徒步道，全程沿G217国道行走，需注意车辆安全；全程561公里，海拔起伏大，需翻越哈希勒根达坂（3400米）等三个达坂；补给点稀少，需提前规划物资；部分路段有牧民毡房可借宿；建议结伴并携带卫星通讯设备；实际徒步者多分段进行，或结合周边草原路线。分段数据覆盖北段（独山子→铁力买提达坂），南段至库车待补充。",
    },  # 新疆

    "巴音布鲁克徒步": {
        "distance_km": 20, "elevation_gain_m": 300, "max_elevation_m": 2500,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "草原、湿地、丘陵",
        "water_sources": "开都河支流、季节性溪流",
        "best_season": "6月至9月",
        "trailhead": "巴音布鲁克镇",
        "notes": "路线以草原徒步为主，可结合九曲十八弯观景台，注意保护湿地生态，夏季需防蚊虫，早晚温差大。",
    },  # 新疆

    "吐峪沟徒步": {
        "distance_km": 15, "elevation_gain_m": 300, "max_elevation_m": 1200,
        "difficulty": "休闲级", "duration_days": 1,
        "terrain": "峡谷、戈壁、丹霞地貌",
        "water_sources": "沟内有季节性溪流，需自备饮用水",
        "best_season": "7-9月",
        "trailhead": "吐峪沟乡（新疆吐鲁番市鄯善县）",
        "notes": "适合各类户外爱好者，注意防晒补水，部分路段需攀爬",
    },  # 新疆

    "赛里木湖徒步": {
        "distance_km": 72, "elevation_gain_m": 1200, "max_elevation_m": 2100,
        "difficulty": "中等", "duration_days": 9,
        "terrain": "湖畔草原、山地、山脊碎石路",
        "water_sources": "赛里木湖及沿途溪流（需净化）",
        "best_season": "6月至9月",
        "trailhead": "赛里木湖东门",
        "notes": "环湖逆时针徒步，部分路段需爬升科古尔琴山脊，注意防风保暖和防晒，湖边露营需遵守景区规定。",
    },  # 新疆

    "哈密大海道": {
        "distance_km": 100, "elevation_gain_m": 500, "max_elevation_m": 1200,
        "difficulty": "中等偏难", "duration_days": 3,
        "terrain": "雅丹地貌、戈壁、干涸河床、沙地",
        "water_sources": "全程无可靠水源，需自备全部饮用水",
        "best_season": "4-5月、9-10月（避开夏季高温）",
        "trailhead": "哈密市五堡乡或了墩停车区",
        "notes": "需四驱越野车补给，部分路段无信号，注意防风沙和高温，建议结伴并提前报备",
    },  # 新疆


    # ===== 批量采集 (72条) =====
    "莫干山蒋公古道": {
        "distance_km": 10, "elevation_gain_m": 600, "max_elevation_m": 758,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "古道、石阶、竹林土路",
        "water_sources": "沿途有溪流，但建议自备充足饮水",
        "best_season": "春秋两季（4-5月、9-11月）",
        "trailhead": "浙江省湖州市德清县莫干山镇莫干山风景区（通常从庾村或后坞出发）",
        "notes": "部分路段较陡，雨后湿滑，需穿防滑鞋；山上气温较低，注意保暖；旺季游客较多，建议早出发。",
    },  # 浙江

    "天目七尖": {
        "distance_km": 50, "elevation_gain_m": 3500, "max_elevation_m": 1500,
        "difficulty": "困难", "duration_days": 2,
        "terrain": "山脊、灌木丛、竹林、土路",
        "water_sources": "沿途水源较少，需自备或提前规划补水点",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "西天目山仙人顶（或东天目山大仙顶反穿）",
        "notes": "路线较长且爬升大，需有户外经验；部分路段灌木丛密集，注意防刮伤；天气多变，需备好雨具和保暖衣物；建议结伴而行。",
    },  # 浙江

    "清凉峰北环线": {
        "distance_km": 15, "elevation_gain_m": 1200, "max_elevation_m": 1787,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、土路、部分铺装路面",
        "water_sources": "沿途水源稀少，需自备饮水",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "浙江省杭州市临安区清凉峰镇",
        "notes": "清凉峰为国家级自然保护区，需遵守规定，注意防火和环保；天气多变，需备雨具和保暖衣物；部分路段陡峭，需注意安全。",
    },  # 浙江

    "千八": {
        "distance_km": 50, "elevation_gain_m": 3000, "max_elevation_m": 1900,
        "difficulty": "困难", "duration_days": 3,
        "terrain": "山地、防火道、草甸、灌木丛",
        "water_sources": "沿途有溪流，但部分路段需自备水",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "浙江省丽水市龙泉市或庆元县",
        "notes": "强度大，被誉为“华东第一虐”，需有丰富徒步经验，注意防滑、防失温，建议结伴并携带GPS。",
    },  # 浙江

    "雁荡山双龙谷羊角洞": {
        "distance_km": 14, "elevation_gain_m": 1000, "max_elevation_m": 800,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、岩石、林间小路",
        "water_sources": "可能有溪流，但需自备饮水",
        "best_season": "春秋季",
        "trailhead": "双龙谷",
        "notes": "部分路段较陡，需注意安全；建议结伴而行，避免偏离常规路线；备足水和食物，做好防迷路准备。",
    },  # 浙江

    "紫金山王家湾-灵谷寺": {
        "distance_km": 10, "elevation_gain_m": 400, "max_elevation_m": 448,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、台阶、林间土路",
        "water_sources": "沿途有售卖点，建议自备水",
        "best_season": "春秋两季",
        "trailhead": "王家湾（地铁4号线王家湾站附近）",
        "notes": "部分路段较陡，需穿防滑鞋；注意保护生态，不要偏离路线。",
    },  # 江苏

    "苏州灵白线": {
        "distance_km": 8, "elevation_gain_m": 300, "max_elevation_m": 200,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、土路、碎石路、部分台阶",
        "water_sources": "沿途有补给点，但建议自备水",
        "best_season": "春秋两季",
        "trailhead": "灵岩山景区门口",
        "notes": "部分路段有护栏围挡，注意安全；建议穿防滑鞋；沿途有补给点，但建议自备水和干粮。",
    },  # 江苏

    "太姥山": {
        "distance_km": 10, "elevation_gain_m": 600, "max_elevation_m": 917,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "花岗岩山岳、石阶、栈道、岩洞",
        "water_sources": "景区内有补给点，需自备饮用水",
        "best_season": "春秋两季（4-5月、9-11月）",
        "trailhead": "太姥山景区入口",
        "notes": "部分路段较陡，需注意安全；岩洞路段湿滑，建议穿防滑鞋；可携带登山杖但非必需。",
    },  # 福建

    "鼓山": {
        "distance_km": 7, "elevation_gain_m": 550, "max_elevation_m": 925,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、土路、古道",
        "water_sources": "沿途有补给点，山脚和山顶有水源",
        "best_season": "春秋两季",
        "trailhead": "福州鼓山风景区入口",
        "notes": "部分路段较陡，需注意安全；亲子游可选择较缓路线；建议携带足够饮水。",
    },  # 福建

    "青云山": {
        "distance_km": 10, "elevation_gain_m": 800, "max_elevation_m": 1130,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、台阶、部分岩石路段",
        "water_sources": "山间可能有溪流，建议自带饮用水",
        "best_season": "春秋两季",
        "trailhead": "青云山景区入口",
        "notes": "注意防滑，防蚊虫，带足水和食物，建议穿登山鞋",
    },  # 福建

    "丹霞山": {
        "distance_km": 20, "elevation_gain_m": 800, "max_elevation_m": 400,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "丹霞地貌，石阶、山路、栈道",
        "water_sources": "景区内有补给点，需自备饮用水",
        "best_season": "春秋两季（3-5月、9-11月）",
        "trailhead": "韶关丹霞山景区大门",
        "notes": "部分路段陡峭，需注意安全；夏季炎热，注意防暑；建议穿防滑鞋。",
    },  # 广东

    "罗浮山飞云顶": {
        "distance_km": 15, "elevation_gain_m": 1100, "max_elevation_m": 1296,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、台阶、竹林、土路",
        "water_sources": "沿途有少量溪流，建议自备充足饮用水",
        "best_season": "秋冬季节（10月至次年3月）",
        "trailhead": "罗浮山景区入口（朱明洞景区）",
        "notes": "部分路段陡峭，需穿防滑鞋；天气多变，注意防雨防晒；节假日人流量大，建议早出发。",
    },  # 广东

    "东西冲": {
        "distance_km": 9, "elevation_gain_m": 200, "max_elevation_m": 100,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "海岸线礁石、沙滩、山路",
        "water_sources": "沿途无淡水，需自备",
        "best_season": "10月至次年4月",
        "trailhead": "东冲村或西冲沙滩",
        "notes": "需穿防滑鞋，注意潮汐时间，防晒防蚊，垃圾请带走",
    },  # 广东

    "七娘山": {
        "distance_km": 10, "elevation_gain_m": 800, "max_elevation_m": 869,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、台阶、土路",
        "water_sources": "沿途无稳定水源，需自备",
        "best_season": "10月至次年4月",
        "trailhead": "深圳大鹏半岛国家地质公园",
        "notes": "需提前了解天气，注意防滑，部分路段陡峭，建议结伴而行",
    },  # 广东

    "漓江": {
        "distance_km": 18, "elevation_gain_m": 200, "max_elevation_m": 400,
        "difficulty": "中等", "duration_days": 3,
        "terrain": "江边步道、田间小路、碎石路、少量山路",
        "water_sources": "漓江水源丰富，沿途有村庄可补给",
        "best_season": "春秋季（3-5月、9-11月）",
        "trailhead": "桂林市阳朔县杨堤码头",
        "notes": "部分路段需乘竹筏过渡，注意防滑，雨季水位上涨时需绕行",
    },  # 广西

    "龙脊梯田": {
        "distance_km": 15, "elevation_gain_m": 800, "max_elevation_m": 1100,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "梯田田埂、石板路、山路",
        "water_sources": "沿途有溪流和村寨补给",
        "best_season": "秋季（9-10月）",
        "trailhead": "龙脊梯田景区入口（平安寨或大寨）",
        "notes": "注意防晒防雨，穿防滑鞋，部分路段陡峭，需注意安全。",
    },  # 广西

    "德天瀑布": {
        "distance_km": 8, "elevation_gain_m": 300, "max_elevation_m": 600,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、河谷、瀑布景观",
        "water_sources": "德天瀑布及周边溪流",
        "best_season": "春秋季（3-5月、9-11月）",
        "trailhead": "德天瀑布景区入口",
        "notes": "部分路段湿滑，需注意安全；建议携带防水装备；边境地区需携带身份证件。",
    },  # 广西

    "五指山": {
        "distance_km": 10, "elevation_gain_m": 800, "max_elevation_m": 1867,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "原始雨林山地，有瀑布和溪流",
        "water_sources": "多处溪流和瀑布",
        "best_season": "11月至次年4月",
        "trailhead": "海南省五指山市水满乡",
        "notes": "务必穿防滑徒步鞋、带登山杖，备足水和高热量零食，雨林蚊虫多，需带驱蚊液，避免单独行动。",
    },  # 海南

    "尖峰岭": {
        "distance_km": 10, "elevation_gain_m": 600, "max_elevation_m": 1412,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "热带雨林山路，部分陡峭台阶",
        "water_sources": "沿途溪流，天池水源",
        "best_season": "11月至次年4月（旱季）",
        "trailhead": "尖峰岭国家森林公园入口或天池",
        "notes": "需早起看日出，携带头灯，防雨防滑，注意蚂蟥",
    },  # 海南

    "张家界国家森林公园金鞭溪": {
        "distance_km": 10, "elevation_gain_m": 400, "max_elevation_m": 1262,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石板路、台阶、林间小径",
        "water_sources": "金鞭溪溪水（需净化）",
        "best_season": "4-6月、9-11月",
        "trailhead": "张家界国家森林公园大门",
        "notes": "部分路段较陡，注意安全；雨天路滑；需购买景区门票；可结合黄石寨、袁家界等景点。",
    },  # 湖南

    "南岳衡山全程": {
        "distance_km": 20, "elevation_gain_m": 1200, "max_elevation_m": 1300,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、山路、部分土路",
        "water_sources": "沿途有补给点、寺庙可补充水",
        "best_season": "春秋两季",
        "trailhead": "南岳大庙或胜利坊",
        "notes": "全程徒步约需6-8小时，注意防晒和补水，节假日人流量大，建议提前购票。",
    },  # 湖南

    "崀山丹霞": {
        "distance_km": 12, "elevation_gain_m": 600, "max_elevation_m": 818,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "丹霞地貌，石阶路、山脊路、栈道",
        "water_sources": "景区内有补给点，建议自备水",
        "best_season": "春秋季（3-5月，9-11月）",
        "trailhead": "崀山风景名胜区北门（邵阳市新宁县）",
        "notes": "部分路段陡峭，需注意安全；雨天路滑，建议穿防滑鞋；景区内需购买门票。",
    },  # 湖南

    "八大公山": {
        "distance_km": 30, "elevation_gain_m": 1500, "max_elevation_m": 1890,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "原始森林、山地、溪流",
        "water_sources": "多处溪流，需净化",
        "best_season": "春秋季",
        "trailhead": "桑植县八大公山镇",
        "notes": "需专业向导，注意防蛇虫，部分路段无信号",
    },  # 湖南

    "恩施大峡谷": {
        "distance_km": 8, "elevation_gain_m": 800, "max_elevation_m": 1700,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶、栈道、山路",
        "water_sources": "景区内有补给点，建议自带水",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "恩施大峡谷游客中心",
        "notes": "全程徒步约6小时，绝壁栈道恐高者慎行，注意安全。",
    },  # 湖北

    "武当山": {
        "distance_km": 18, "elevation_gain_m": 1400, "max_elevation_m": 1612,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、山路、部分栈道",
        "water_sources": "沿途有补给点，建议自备水",
        "best_season": "春秋两季（3-5月、9-11月）",
        "trailhead": "武当山山门（游客中心）",
        "notes": "需购买门票，部分路段陡峭，注意安全；建议早起避开人流；可乘坐景区巴士至半山腰再徒步。",
    },  # 湖北

    "大别山白马尖": {
        "distance_km": 15, "elevation_gain_m": 1200, "max_elevation_m": 1777,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、森林、岩石路",
        "water_sources": "沿途有溪流，但需确认季节性",
        "best_season": "春秋季",
        "trailhead": "安徽省六安市霍山县白马尖登山口",
        "notes": "部分路段陡峭，需注意安全；冬季可能有积雪，需防滑；建议携带足够水和食物。",
    },  # 安徽

    "嵩山太室山": {
        "distance_km": 9, "elevation_gain_m": 1000, "max_elevation_m": 1491,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、土路、山脊路",
        "water_sources": "沿途有少量补给点，建议自备水",
        "best_season": "春秋季（3-5月、9-11月）",
        "trailhead": "嵩阳书院或太室山广场",
        "notes": "部分路段陡峭，需注意安全；夏季注意防暑，冬季注意防滑",
    },  # 河南

    "云台山经典": {
        "distance_km": 15, "elevation_gain_m": 800, "max_elevation_m": 1300,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "景区石阶路、栈道、部分山野土路",
        "water_sources": "景区内多处补给点，可购买饮用水",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "百家岩停车场",
        "notes": "台阶较多，需穿防滑鞋；部分路段陡峭，注意安全；景区内禁止烟火。",
    },  # 河南

    "养子沟反穿老君山": {
        "distance_km": 20, "elevation_gain_m": 1400, "max_elevation_m": 2200,
        "difficulty": "较难", "duration_days": 1,
        "terrain": "山野土路、碎石路、台阶、栈道",
        "water_sources": "养子沟内溪流，老君山景区内有补给点",
        "best_season": "春秋两季（4-5月、9-10月）",
        "trailhead": "养子沟景区",
        "notes": "需提前预约徒步，关注景区公众号。部分路段陡峭，需注意安全。冬季可能有积雪，需准备冰爪。",
    },  # 河南

    "广州白云山": {
        "distance_km": 10, "elevation_gain_m": 300, "max_elevation_m": 382,
        "difficulty": "较易", "duration_days": 1,
        "terrain": "石阶路、柏油路、土路",
        "water_sources": "沿途有售卖点，可补水",
        "best_season": "全年（春秋最佳）",
        "trailhead": "白云山南门（云台花园旁）",
        "notes": "景区成熟，适合新手；节假日人多，建议早出发；需购门票。",
    },  # 广东

    "小五台山": {
        "distance_km": 30, "elevation_gain_m": 1800, "max_elevation_m": 2882,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "山地、草甸、碎石坡",
        "water_sources": "少量溪流，需自备水",
        "best_season": "6月至9月",
        "trailhead": "河北省张家口市蔚县赤崖堡村",
        "notes": "需提前报备，注意高山天气变化，防寒防晒，部分路段陡峭",
    },  # 河北

    "涞水蝎子沟": {
        "distance_km": 12, "elevation_gain_m": 500, "max_elevation_m": 800,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "峡谷、碎石路、山间小径",
        "water_sources": "沟内可能有季节性溪流，建议自备充足饮水",
        "best_season": "春秋季（4-6月、9-11月）",
        "trailhead": "河北省保定市涞水县野三坡镇蝎子沟入口",
        "notes": "沟内遍布蝎子草，触碰后剧痛，需穿长袖长裤，避免皮肤裸露；部分路段可能湿滑，需注意安全。",
    },  # 河北

    "桂林白石天生桥": {
        "distance_km": 10, "elevation_gain_m": 300, "max_elevation_m": 400,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "喀斯特地貌，包含天生桥、穿岩群、溪流、山路",
        "water_sources": "源头之水，清澈见底，沿途有溪流",
        "best_season": "春秋两季（气候宜人）",
        "trailhead": "桂林市白石乡附近",
        "notes": "该路线为小众徒步路线，需注意野外安全，部分路段可能湿滑，建议结伴而行，并做好防蚊虫措施。",
    },  # 广西

    "泰山经典": {
        "distance_km": 10, "elevation_gain_m": 1500, "max_elevation_m": 1545,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、山路",
        "water_sources": "沿途有售卖点，可补充饮用水",
        "best_season": "春季（4-5月）和秋季（9-11月）",
        "trailhead": "红门",
        "notes": "全程石阶，注意膝盖保护；节假日人流量大，建议错峰；需提前预约门票。",
    },  # 山东

    "崂山仰口经典": {
        "distance_km": 8, "elevation_gain_m": 600, "max_elevation_m": 800,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶步道、山间小路、部分陡峭台阶",
        "water_sources": "沿途有售卖点，建议自备饮水",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "崂山（仰口）游客服务中心",
        "notes": "部分路段陡峭，注意安全；需穿舒适徒步鞋；提前查看天气，雨天路滑。",
    },  # 山东

    "蒙山": {
        "distance_km": 12, "elevation_gain_m": 900, "max_elevation_m": 1156,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地土路、石阶、部分岩石路段",
        "water_sources": "沿途水源较少，需自备饮水",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "山东省临沂市蒙阴县云蒙景区入口",
        "notes": "部分路段较陡，需穿防滑徒步鞋；建议携带登山杖和充足补给；注意天气变化，避免雨天出行。",
    },  # 山东

    "恒山": {
        "distance_km": 12, "elevation_gain_m": 900, "max_elevation_m": 2016,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶路、土路、部分碎石坡",
        "water_sources": "沿途有少量补给点，建议自备饮用水",
        "best_season": "4-10月",
        "trailhead": "恒山风景区山门（或悬空寺附近）",
        "notes": "部分路段较陡，需注意安全；山顶风大，注意保暖；建议穿防滑鞋。",
    },  # 山西

    "芦芽山": {
        "distance_km": 18, "elevation_gain_m": 900, "max_elevation_m": 2736,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "高山草甸、原始森林、碎石路、山脊路",
        "water_sources": "沿途可能有溪流，但建议自备足够饮用水",
        "best_season": "5月至10月",
        "trailhead": "山西省忻州市宁武县东寨镇",
        "notes": "海拔较高，气温偏低，需携带防风保暖外套；穿防滑运动鞋；部分路段陡峭，注意安全；建议提前查看天气。",
    },  # 山西

    "历山舜王坪": {
        "distance_km": 15, "elevation_gain_m": 1200, "max_elevation_m": 2358,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、草甸、林间小路",
        "water_sources": "沿途可能有溪流，但需自备充足饮用水",
        "best_season": "5月至10月",
        "trailhead": "山西省运城市垣曲县历山镇",
        "notes": "部分路段可能涉及防火期管控，需提前了解当地政策；山区天气多变，需备好雨具和保暖衣物。",
    },  # 山西

    "华山": {
        "distance_km": 20, "elevation_gain_m": 2000, "max_elevation_m": 2155,
        "difficulty": "较难", "duration_days": 2,
        "terrain": "石阶、山脊、险峻路段（如苍龙岭、长空栈道）",
        "water_sources": "沿途有补给点，可购买饮用水和食物",
        "best_season": "春秋（3-5月、9-11月）",
        "trailhead": "玉泉院（华山徒步起点）",
        "notes": "部分路段险峻，需注意安全；建议提前规划时间，避免夜爬；携带头灯、手套等装备。",
    },  # 陕西

    "崆峒山": {
        "distance_km": 12, "elevation_gain_m": 900, "max_elevation_m": 2123,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶、山路、部分栈道",
        "water_sources": "景区内补给点，建议自带",
        "best_season": "春秋季（4-6月、9-10月）",
        "trailhead": "崆峒古镇北门游客服务中心或景区南门（前山）、东门（后山）",
        "notes": "景区门票约80元，索道单程约40元，可徒步或索道；建议提前预约门票，徒步线路从南门或东门进入；注意天气变化，备足水和食物。",
    },  # 甘肃

    "青海湖环湖": {
        "distance_km": 360, "elevation_gain_m": 500, "max_elevation_m": 3250,
        "difficulty": "中等", "duration_days": 10,
        "terrain": "环湖公路、草原、沙地、湿地",
        "water_sources": "沿途乡镇、补给点，需自备部分饮水",
        "best_season": "7月至8月",
        "trailhead": "西海镇（或二郎剑景区）",
        "notes": "高原地区注意防晒、防寒及高反；环湖距离长，需提前规划每日行程和补给；部分路段为公路，注意交通安全。",
    },  # 青海

    "年保玉则": {
        "distance_km": 60, "elevation_gain_m": 1500, "max_elevation_m": 4550,
        "difficulty": "较难", "duration_days": 3,
        "terrain": "高山草甸、碎石坡、垭口",
        "water_sources": "仙女湖、妖女湖及溪流",
        "best_season": "6月至8月",
        "trailhead": "年保玉则景区入口（青海久治县）",
        "notes": "需翻越两座垭口（4350米和4550米），高海拔易引发高原反应，需提前适应；天气多变，需备防雨保暖装备；移动和联通信号弱，电信信号较好；建议结伴并请向导。",
    },  # 青海

    "阿尼玛卿转山": {
        "distance_km": 150, "elevation_gain_m": 3000, "max_elevation_m": 5000,
        "difficulty": "专业级", "duration_days": 7,
        "terrain": "高山草甸、碎石坡、冰川、垭口",
        "water_sources": "沿途有溪流和湖泊，但部分路段需自备水",
        "best_season": "6月至9月",
        "trailhead": "青海省果洛州玛沁县雪山乡",
        "notes": "需办理边防证，注意高原反应，天气多变，建议结伴并请向导",
    },  # 青海

    "贺兰山丁香沟": {
        "distance_km": 15, "elevation_gain_m": 800, "max_elevation_m": 2500,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、沟谷、碎石坡、草甸",
        "water_sources": "沟内有泉水，但季节性强，需自备充足饮水",
        "best_season": "5-10月",
        "trailhead": "宁夏银川市贺兰山苏峪口国家森林公园或贺兰山岩画景区附近",
        "notes": "部分区域无手机信号，需结伴而行，注意野生动物（如岩羊），提前了解天气，装备需防风防寒。",
    },  # 宁夏

    "沙坡头沙漠": {
        "distance_km": 8, "elevation_gain_m": 100, "max_elevation_m": 1500,
        "difficulty": "较易", "duration_days": 1,
        "terrain": "沙漠、沙丘",
        "water_sources": "无天然水源，需自带饮水",
        "best_season": "春秋季（4-6月、9-11月）",
        "trailhead": "沙坡头景区入口",
        "notes": "注意防晒、防风沙，携带充足饮水，建议穿高帮鞋防沙，遵循景区规定。",
    },  # 宁夏

    "千山经典": {
        "distance_km": 15, "elevation_gain_m": 800, "max_elevation_m": 708,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶、山间土路、部分岩石路段",
        "water_sources": "沿途无固定水源，需自备饮水",
        "best_season": "春秋季（4-5月、9-10月）",
        "trailhead": "千山风景区无量观",
        "notes": "部分路段陡峭，需穿防滑登山鞋；注意防晒和补充体力；景区内需购票。",
    },  # 辽宁

    "珠海凤凰山猴路": {
        "distance_km": 8, "elevation_gain_m": 500, "max_elevation_m": 437,
        "difficulty": "较难", "duration_days": 1,
        "terrain": "山野土路、陡峭岩石、手脚并用路段",
        "water_sources": "沿途无补给，需自备水源",
        "best_season": "秋冬季节（10月至次年3月）",
        "trailhead": "珠海凤凰山森林公园入口",
        "notes": "路线陡峭，需手脚并用，建议携带手套和登山杖，注意安全。",
    },  # 广东

    "长白山": {
        "distance_km": 15, "elevation_gain_m": 1000, "max_elevation_m": 2691,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、火山地貌、部分栈道",
        "water_sources": "山间溪流、景区补给点",
        "best_season": "夏季（6-8月）和秋季（9-10月）",
        "trailhead": "长白山北坡或西坡景区入口",
        "notes": "天气多变，需准备防寒衣物和雨具；部分路段陡峭，需注意安全；建议提前了解景区开放情况。",
    },  # 吉林

    "松花湖环湖": {
        "distance_km": 15, "elevation_gain_m": 600, "max_elevation_m": 800,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、森林、湖畔小径",
        "water_sources": "松花湖及沿途溪流",
        "best_season": "春秋",
        "trailhead": "松花湖景区入口",
        "notes": "部分路段湿滑，需防滑鞋；夏季蚊虫较多，注意防护；天气多变，备好雨具。",
    },  # 吉林

    "五大连池风景区": {
        "distance_km": 15, "elevation_gain_m": 300, "max_elevation_m": 500,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "火山熔岩台地、湖泊、森林、栈道",
        "water_sources": "景区内有补给点，需自备饮用水",
        "best_season": "夏季（6-8月）和秋季（9-10月）",
        "trailhead": "五大连池风景区游客中心",
        "notes": "部分路段为火山石路面，建议穿防滑徒步鞋；注意防晒和补水；冬季寒冷，需做好保暖措施。",
    },  # 黑龙江

    "镜泊湖蓝冰": {
        "distance_km": 15, "elevation_gain_m": 200, "max_elevation_m": 400,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "冰面、雪地、湖岸、火山岩",
        "water_sources": "镜泊湖湖水（需净化）、沿途补给点",
        "best_season": "冬季（12月-2月）",
        "trailhead": "镜泊湖景区北门",
        "notes": "冬季气温极低，需防寒保暖；冰面行走需注意安全，听从向导安排；部分路段积雪较深，建议穿冰爪。",
    },  # 黑龙

    "玉山主峰": {
        "distance_km": 22, "elevation_gain_m": 1300, "max_elevation_m": 3952,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "高山步道、碎石坡、岩壁",
        "water_sources": "沿途有山屋供水，需自备水",
        "best_season": "4月至11月",
        "trailhead": "塔塔加登山口",
        "notes": "需申请入山入园证，注意高山症，需保暖",
    },  # 台湾

    "雨崩": {
        "distance_km": 55, "elevation_gain_m": 1500, "max_elevation_m": 3900,
        "difficulty": "中等", "duration_days": 4,
        "terrain": "高山草甸、原始森林、碎石坡、垭口",
        "water_sources": "沿途有溪流，但部分路段需自备饮水",
        "best_season": "5-6月及9-11月",
        "trailhead": "云南省迪庆州德钦县西当温泉",
        "notes": "需注意高原反应，提前适应海拔；部分路段较陡峭，建议使用登山杖；尊重当地藏族风俗。",
    },  # 云南

    "阿里山眠月线": {
        "distance_km": 20, "elevation_gain_m": 500, "max_elevation_m": 2300,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "森林铁路、步道、桥梁、隧道",
        "water_sources": "沿途无可靠水源，需自备",
        "best_season": "春秋两季",
        "trailhead": "阿里山森林游乐区",
        "notes": "需提前申请入园，注意天气变化，部分路段有崩塌风险",
    },  # 台湾

    "锥麓古道": {
        "distance_km": 10, "elevation_gain_m": 500, "max_elevation_m": 1100,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山径、悬崖步道、碎石路",
        "water_sources": "沿途无稳定水源，需自备饮水",
        "best_season": "10月至次年4月（避开雨季和台风季）",
        "trailhead": "太鲁阁国家公园燕子口",
        "notes": "需申请入山证，部分路段狭窄且临崖，需注意安全，建议早出发",
    },  # 台湾

    "金佛山": {
        "distance_km": 15, "elevation_gain_m": 1200, "max_elevation_m": 2238,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地台阶、土路、部分碎石路",
        "water_sources": "沿途无稳定水源，需自备",
        "best_season": "春秋季（4-5月、9-11月）",
        "trailhead": "金佛山景区北门或西大门",
        "notes": "部分路段陡峭，需注意安全；冬季有积雪，需防滑；建议携带登山杖和足够饮水。",
    },  # 重庆

    "仙女山": {
        "distance_km": 10, "elevation_gain_m": 600, "max_elevation_m": 2033,
        "difficulty": "较易", "duration_days": 1,
        "terrain": "高山草甸、森林步道、石板路",
        "water_sources": "景区内有补给点，建议自备饮水",
        "best_season": "夏季（6-9月）避暑，冬季（12-2月）赏雪",
        "trailhead": "仙女山国家森林公园景区入口",
        "notes": "景区设施完善，适合休闲徒步；冬季注意防滑，夏季注意防晒；部分路段有台阶，需穿舒适徒步鞋。",
    },  # 重庆

    "荔波茂兰喀斯特原始森林": {
        "distance_km": 8, "elevation_gain_m": 400, "max_elevation_m": 1000,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "喀斯特原始森林、洞穴、山地",
        "water_sources": "溪流",
        "best_season": "秋季",
        "trailhead": "荔波县",
        "notes": "需注意洞穴安全，建议结伴而行，部分路段湿滑，需穿着防滑徒步鞋。",
    },  # 贵州

    "雷公山": {
        "distance_km": 20, "elevation_gain_m": 1200, "max_elevation_m": 2178,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、丛林、草甸、溪流",
        "water_sources": "沿途有溪流，但需确认季节性水源",
        "best_season": "春秋两季（4-5月、9-11月）",
        "trailhead": "贵州省黔东南苗族侗族自治州雷山县",
        "notes": "需注意天气变化，山区气候多变，建议携带雨具和保暖衣物。部分路段可能湿滑，需穿防滑徒步鞋。建议结伴而行，并提前了解当地规定。",
    },  # 贵州

    "万峰林": {
        "distance_km": 10, "elevation_gain_m": 300, "max_elevation_m": 1200,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、栈道、土路",
        "water_sources": "沿途可能有补给点，建议自备水",
        "best_season": "春秋季",
        "trailhead": "万峰林景区入口",
        "notes": "部分路段较远，需4-6小时，注意防晒和补水",
    },  # 贵州

    "三清山": {
        "distance_km": 12, "elevation_gain_m": 1200, "max_elevation_m": 1819,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石阶、栈道、山间小路",
        "water_sources": "沿途有补给点，建议自备水",
        "best_season": "春秋季（4-5月、9-10月）",
        "trailhead": "外双溪或金沙索道站",
        "notes": "部分路段陡峭，需注意安全；西海岸栈道可能封闭，提前查询；建议早起避开人流。",
    },  # 江西

    "庐山": {
        "distance_km": 30, "elevation_gain_m": 1800, "max_elevation_m": 1400,
        "difficulty": "较难", "duration_days": 1,
        "terrain": "石阶路、山间土路、景区步道",
        "water_sources": "沿途有溪流，三叠泉附近水源充足，牯岭镇可补给",
        "best_season": "春秋两季（4-5月、9-10月）",
        "trailhead": "好汉坡起点（九江市莲花镇）",
        "notes": "全程约30公里，需一天时间完成，体力消耗大。部分路段（如五老峰、三叠泉）台阶陡峭，需注意安全。建议提前准备足够水和食物，穿防滑登山鞋。",
    },  # 江西

    "井冈山": {
        "distance_km": 11, "elevation_gain_m": 800, "max_elevation_m": 1400,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山地、林间小路、部分台阶",
        "water_sources": "沿途可能有溪流，但建议自备充足饮水",
        "best_season": "春秋两季（4-5月、9-10月）",
        "trailhead": "井冈山茨坪镇",
        "notes": "部分路段为红色旅游步道，注意安全；需提前了解天气，雨天路滑；建议穿徒步鞋，携带登山杖。",
    },  # 江西

    "北京凤凰岭": {
        "distance_km": 10, "elevation_gain_m": 600, "max_elevation_m": 1200,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山路、台阶、部分陡峭路段",
        "water_sources": "景区内有补给点，建议自备水",
        "best_season": "春秋季",
        "trailhead": "凤凰岭自然风景区入口",
        "notes": "部分路段陡峭，需注意安全；春季赏花人多，建议错峰出行。",
    },  # 北京

    "深圳阳台山": {
        "distance_km": 10, "elevation_gain_m": 500, "max_elevation_m": 587,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "土路、台阶、部分岩石路段",
        "water_sources": "沿途有少量补给点，建议自备饮水",
        "best_season": "全年，春秋最佳",
        "trailhead": "石岩登山口或西丽登山口",
        "notes": "部分路段陡峭，需注意安全；雨天路滑，建议穿着防滑鞋。",
    },  # 广东

    "佘山国家森林公园": {
        "distance_km": 8, "elevation_gain_m": 200, "max_elevation_m": 100,
        "difficulty": "轻松", "duration_days": 1,
        "terrain": "台阶路、步道、林间小路",
        "water_sources": "公园内有售卖点，建议自备",
        "best_season": "春秋两季",
        "trailhead": "佘山地铁站（9号线）",
        "notes": "东佘山和西佘山免费开放，需提前预约；注意台阶湿滑，穿防滑鞋。",
    },  # 上海

    "崇明岛环岛": {
        "distance_km": 30, "elevation_gain_m": 50, "max_elevation_m": 5,
        "difficulty": "较易", "duration_days": 1,
        "terrain": "湿地步道、森林小径、堤岸公路",
        "water_sources": "沿途有补给点，但建议自备充足饮水",
        "best_season": "春秋季（3-5月、9-11月）",
        "trailhead": "东滩湿地公园",
        "notes": "崇明岛地势平坦，适合初级徒步者；注意防晒和防风，部分路段无遮阴；湿地区域注意蚊虫。",
    },  # 上海

    "大夫山森林公园": {
        "distance_km": 10, "elevation_gain_m": 200, "max_elevation_m": 226,
        "difficulty": "轻松", "duration_days": 1,
        "terrain": "公园步道、水泥路、少量台阶",
        "water_sources": "公园内有小卖部和自动售货机，可购买饮用水",
        "best_season": "全年皆宜，春秋最佳",
        "trailhead": "大夫山森林公园南门或北门",
        "notes": "公园免费开放，适合家庭出游，可租自行车骑行，注意防晒和补水。",
    },  # 广东

    "梧桐山北路-好汉坡-大梧桐顶": {
        "distance_km": 8, "elevation_gain_m": 800, "max_elevation_m": 943,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "台阶路、土路、部分陡坡",
        "water_sources": "沿途有补给点，建议自备水",
        "best_season": "春秋季",
        "trailhead": "梧桐山北门",
        "notes": "好汉坡较陡，需注意安全；节假日人流量大；建议早出发。",
    },  # 广东

    "东西涌海岸线": {
        "distance_km": 6, "elevation_gain_m": 200, "max_elevation_m": 150,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "海岸礁石、沙滩、山路",
        "water_sources": "沿途无淡水，需自备",
        "best_season": "10月至次年4月",
        "trailhead": "东涌社区",
        "notes": "部分路段需攀爬，注意潮汐时间，建议结伴而行，做好防晒。",
    },  # 广东

    # ===== 补充路线（2026-09-01 二次采集，此前批量采集失败） =====
    "终南山徒步": {
        "distance_km": 30, "elevation_gain_m": 1800, "max_elevation_m": 2604,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "秦岭石海、高山草甸、原始森林",
        "water_sources": "甘湫池、沿途溪流",
        "best_season": "4-6月、9-11月",
        "trailhead": "西安市长安区石砭峪",
        "notes": "秦岭南北分界线，可经翠华山出山；石海路段注意防滑。",
    },  # 补充-陕西

    "翠华山徒步": {
        "distance_km": 10, "elevation_gain_m": 1000, "max_elevation_m": 2604,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "山崩石海、栈道、林间步道",
        "water_sources": "景区商店、天池周边补给",
        "best_season": "3-5月、9-11月",
        "trailhead": "西安市太乙宫翠华山景区大门",
        "notes": "山崩地质奇观，天池可游船；步道成熟，适合一日游。",
    },  # 补充-陕西

    "祁连山徒步": {
        "distance_km": 60, "elevation_gain_m": 2000, "max_elevation_m": 4100,
        "difficulty": "困难", "duration_days": 4,
        "terrain": "高山牧场、碎石坡、冰川、垭口",
        "water_sources": "冰沟河、沿途溪流（需过滤）",
        "best_season": "6-9月",
        "trailhead": "甘肃张掖肃南裕固族自治县",
        "notes": "高海拔地区注意高反与天气突变；牧民营地可借宿；建议结伴并携带卫星通讯。",
    },  # 补充-甘肃

    "马蹄寺徒步": {
        "distance_km": 15, "elevation_gain_m": 600, "max_elevation_m": 2800,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "石窟栈道、草甸、山地土路",
        "water_sources": "景区及镇上有补给",
        "best_season": "5-10月",
        "trailhead": "张掖市肃南县马蹄寺景区",
        "notes": "三十三天石窟值得一看；祁连山脚下牧场风光，适合休闲徒步。",
    },  # 补充-甘肃

    "茶卡盐湖徒步": {
        "distance_km": 10, "elevation_gain_m": 50, "max_elevation_m": 3100,
        "difficulty": "轻松", "duration_days": 1,
        "terrain": "盐壳湖面、盐堤、栈道",
        "water_sources": "景区内外补给充足，盐湖水不可饮用",
        "best_season": "6-9月（天空之镜最佳）",
        "trailhead": "青海海西州乌兰县茶卡镇",
        "notes": "高海拔注意防晒；盐壳锋利建议穿鞋套；清晨/傍晚倒影最美。",
    },  # 补充-青海

    "雪乡穿越": {
        "distance_km": 15, "elevation_gain_m": 800, "max_elevation_m": 1400,
        "difficulty": "中等", "duration_days": 1,
        "terrain": "积雪林道、雪原、翻越羊草山",
        "water_sources": "雪谷/雪乡有补给，途中需带热水",
        "best_season": "12月至次年2月（雪季）",
        "trailhead": "牡丹江市大海林雪乡（双峰林场）",
        "notes": "冬季线路注意保暖防滑，雪套冰爪必备；羊草山风大，午后天气多变。",
    },  # 补充-黑龙江

    "武隆天坑徒步": {
        "distance_km": 8, "elevation_gain_m": 400, "max_elevation_m": 1400,
        "difficulty": "轻松", "duration_days": 1,
        "terrain": "景区步道、喀斯特天坑栈道",
        "water_sources": "景区补给点充足",
        "best_season": "全年（夏季避暑）",
        "trailhead": "重庆市武隆区天生三桥景区",
        "notes": "天生三桥+龙水峡地缝经典联游；《满城尽带黄金甲》取景地；台阶较多注意膝盖。",
    },  # 补充-重庆

    "黄果树徒步": {
        "distance_km": 12, "elevation_gain_m": 300, "max_elevation_m": 1200,
        "difficulty": "轻松", "duration_days": 1,
        "terrain": "景区步道、河谷栈道",
        "water_sources": "景区补给点充足",
        "best_season": "6-10月（丰水期瀑布壮观）",
        "trailhead": "贵州省安顺市黄果树景区",
        "notes": "陡坡塘、黄果树大瀑布、天星桥三段联游；雨季注意栈道湿滑。",
    },  # 补充-贵州

    "龙虎山徒步": {
        "distance_km": 20, "elevation_gain_m": 800, "max_elevation_m": 800,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "丹霞峰林、泸溪河岸、竹海步道",
        "water_sources": "上清镇、景区补给充足",
        "best_season": "3-5月、9-11月",
        "trailhead": "江西省鹰潭市龙虎山景区",
        "notes": "道教发源地，天师府+象鼻山+仙水岩经典线路；可乘竹筏游泸溪河。",
    },  # 补充-江西

    "香山徒步": {
        "distance_km": 8, "elevation_gain_m": 500, "max_elevation_m": 575,
        "difficulty": "轻松", "duration_days": 1,
        "terrain": "公园步道、石阶路",
        "water_sources": "公园内售卖点充足",
        "best_season": "春秋季（10-11月红叶最佳）",
        "trailhead": "北京市海淀区香山公园东门",
        "notes": "香炉峰（鬼见愁）登顶俯瞰北京城；节假日人多建议早出发；可连走香八拉拉练线。",
    },  # 补充-北京

    "孟克德古道": {
        "distance_km": 70, "elevation_gain_m": 1800, "max_elevation_m": 3495,
        "difficulty": "困难", "duration_days": 4,
        "terrain": "天山河谷、高山草甸、碎石达坂",
        "water_sources": "孟克德河谷溪流（需过滤）",
        "best_season": "6-9月",
        "trailhead": "新疆乌苏市（独库公路沿线）",
        "notes": "翻越孟克德达坂，穿越天山腹地至唐布拉草原；无信号区需卫星通讯；马帮驮运可选。",
    },  # 补充-新疆

    "喀拉峻徒步": {
        "distance_km": 50, "elevation_gain_m": 1200, "max_elevation_m": 2800,
        "difficulty": "中等", "duration_days": 3,
        "terrain": "高山五花草甸、阔克苏峡谷、草原牧场",
        "water_sources": "牧民毡房、沿途溪流",
        "best_season": "6-8月（花海季）",
        "trailhead": "新疆特克斯县喀拉峻景区",
        "notes": "世界自然遗产，鲜花台-猎鹰台-阔克苏峡谷经典线；可徒步至琼库什台；牧民毡房可住宿。",
    },  # 补充-新疆

    "托乎拉苏徒步": {
        "distance_km": 40, "elevation_gain_m": 800, "max_elevation_m": 2600,
        "difficulty": "中等", "duration_days": 2,
        "terrain": "高山草原、松林、丘陵牧场",
        "water_sources": "沿途溪流、牧场水源",
        "best_season": "6-9月",
        "trailhead": "新疆伊宁县托乎拉苏草原",
        "notes": "草原穿越至赛里木湖方向；六月野花盛开；坡度平缓适合入门长线。",
    },  # 补充-新疆

    "罗布泊徒步": {
        "distance_km": 120, "elevation_gain_m": 200, "max_elevation_m": 1200,
        "difficulty": "专业级", "duration_days": 6,
        "terrain": "戈壁盐壳、雅丹群、干涸湖盆",
        "water_sources": "全程无水源，需补给车队",
        "best_season": "10月至次年4月（避开高温）",
        "trailhead": "新疆若羌县（需后勤补给车）",
        "notes": "极端干旱无人区，必须专业向导+补给车队；夏季地表 70°C+ 严禁进入；卫星电话必备。",
    },  # 补充-新疆

    "阿尔金山徒步": {
        "distance_km": 80, "elevation_gain_m": 1500, "max_elevation_m": 4800,
        "difficulty": "专业级", "duration_days": 5,
        "terrain": "高原荒漠、盐湖、雪山草甸",
        "water_sources": "阿牙克库木湖等盐湖不可饮用，需自备",
        "best_season": "6-8月（高反最轻时段）",
        "trailhead": "青海茫崖市/新疆若羌县",
        "notes": "高原无人区，海拔 4000m+，必须专业团队与车辆保障；严格高反预防；保护区需提前报批。",
    },  # 补充-新疆/青海

    "昆仑山徒步": {
        "distance_km": 60, "elevation_gain_m": 2000, "max_elevation_m": 4800,
        "difficulty": "专业级", "duration_days": 4,
        "terrain": "高原戈壁、雪山、冰川、碎石坡",
        "water_sources": "冰川融水（需过滤），补给稀少",
        "best_season": "6-8月",
        "trailhead": "青海格尔木市（昆仑山口方向）",
        "notes": "昆仑山口海拔 4768m 需先适应；玉虚峰/黑独山方向；高反风险极高，需专业向导。",
    },  # 补充-青海/新疆

}

# 初始化：加载外部日程分段 + 合并到知识库
_load_segments()
for _name, _segs in _LOADED_SEGMENTS.items():
    if _name in KNOWN_ROUTES and isinstance(KNOWN_ROUTES[_name], dict):
        KNOWN_ROUTES[_name]["segments"] = _segs


class RouteAnalystAgent(BaseAgent):
    name = "RouteAnalyst"
    role = "planner"
    description = "路线分析专家 Agent，41条知识库 + LLM 推理 + 联网搜索，覆盖全国路线"

    @property
    def output_schema_hint(self) -> str:
        return """```json
{
  "thinking": "路线分析的推理过程",
  "output": {
    "name": "路线名称",
    "distance_km": 22.0, "elevation_gain_m": 1800, "max_elevation_m": 1918,
    "difficulty": "中等", "duration_days": 2,
    "terrain": "地形特征", "water_sources": "水源", "best_season": "最佳季节",
    "trailhead": "起点", "notes": "注意事项"
  }
}
```"""

    @property
    def system_prompt(self) -> str:
        return """你是资深徒步路线分析师。根据用户提供的路线名称，输出路线数据 JSON。

如果路线的具体数据你了解，直接输出准确的数值。如果不完全确定，根据路线所在区域、海拔、地形特征进行合理估计。

输出包含: name, distance_km, elevation_gain_m, max_elevation_m, difficulty, duration_days, terrain, water_sources, best_season, trailhead, notes。

难度等级: 轻松/较易/中等/较难/困难/专业级
"""

    async def think(self, user_input: str, context: dict | None = None) -> AgentResult:
        """路线分析——三级查询：知识库 → LLM → 联网搜索"""
        gpx_data = (context or {}).get("gpx_data")
        if gpx_data:
            return await self._analyze_gpx_data(gpx_data)

        # 1. 知识库匹配
        result = await self._analyze_known_route(user_input, context)
        if result.success and "message" not in result.output:
            return result

        # 2. 知识库未匹配 → LLM 查询（基于模型知识）
        logger.info(f"[RouteAnalyst] 知识库未匹配，使用 LLM 查询路线...")
        llm_result = await self._try_llm_think(user_input, context)
        if llm_result:
            return llm_result

        # 3. LLM 也失败 → 联网搜索 → LLM 提取
        logger.info(f"[RouteAnalyst] LLM 未返回，启用联网搜索...")
        search_result = await self._search_and_extract(user_input, context)
        if search_result:
            return search_result

        # 4. 全部失败 → 返回通用提示
        return result

    async def _search_and_extract(self, user_input: str, context: dict | None = None) -> AgentResult | None:
        """联网搜索路线信息，用 LLM 提取结构化数据"""
        try:
            from app.services.search_service import search_route_info
            from app.services.llm_service import get_llm_service

            # 提取路线名
            route_name = self._extract_route_name(user_input)

            # 搜索
            search_results = await search_route_info(route_name)
            if not search_results:
                logger.info(f"[RouteAnalyst] 联网搜索无结果")
                return None

            # 用 LLM 从搜索结果中提取路线数据
            llm = get_llm_service()
            if not llm.available:
                return None

            search_text = "\n\n".join([
                f"来源{i+1}: {r['title']}\n{r['body']}"
                for i, r in enumerate(search_results[:8])
            ])

            system = """你是徒步路线数据提取专家。从以下网页搜索结果中提取路线的结构化数据。

## 输出格式
```json
{
  "thinking": "分析搜索结果中的数据来源和可靠性",
  "output": {
    "name": "路线名称",
    "distance_km": 数字(公里，必填！),
    "elevation_gain_m": 数字(累计爬升米，必填！),
    "max_elevation_m": 数字(最高海拔米，必填！),
    "difficulty": "轻松/较易/中等/较难/困难/专业级",
    "duration_days": 数字(天，必填！),
    "terrain": "地形特征描述",
    "water_sources": "水源情况",
    "best_season": "最佳季节",
    "trailhead": "起点位置",
    "notes": "注意事项",
    "data_source": "web_search"
  }
}
```

## 规则（极其重要！）
1. distance_km、elevation_gain_m、max_elevation_m、duration_days 这4个数字字段不能为0！
2. 如果搜索结果中有具体数值→优先使用
3. 如果搜索结果没有数值→必须根据地形、区域、类似路线进行有理有据的估算
4. 估算参考：单日徒步10-18km；高原路线海拔3000-5500m；爬升=距离×8%-15%
5. duration_days = distance_km / 15（向上取整，最少1天）
6. difficulty：<10km+<500m爬升=较易，<20km+<1000m=中等，>30km或>2000m=困难，>4000m海拔=专业级"""

            user_msg = f"## 搜索路线\n{route_name}\n\n## 搜索结果\n{search_text[:4000]}\n\n请提取路线数据。"

            result = await llm.think(
                system_prompt=system,
                user_message=user_msg,
                output_format="json",
                max_tokens=1024,
                temperature=0.2,
            )

            if result.get("success") and result.get("json"):
                data = result["json"]
                output = data.get("output", data)
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    output=output,
                    thinking=f"联网搜索: 从 {len(search_results)} 条结果中提取 {route_name} 路线数据",
                )

        except Exception as e:
            logger.error(f"[RouteAnalyst] 联网搜索失败: {e}")

        return None

    def _extract_route_name(self, user_input: str) -> str:
        """从用户输入中提取路线名称"""
        # 常见模式："走XX线"、"去XX"、"XX徒步"、"XX穿越"
        import re
        patterns = [
            r'走(.+?)(?:线|徒步|穿越|，|。|$)',
            r'去(.+?)(?:徒步|穿越|，|。|$)',
            r'(.+?)(?:徒步|穿越)(?:线|路线)?',
        ]
        for p in patterns:
            m = re.search(p, user_input)
            if m:
                name = m.group(1).strip()
                if len(name) >= 2 and len(name) <= 20:
                    return name
        # 取前15个字作为路线名
        return user_input[:15].strip()

    async def _analyze_gpx_data(self, gpx_data: dict) -> AgentResult:
        """分析 GPX 文件数据（精确算法）"""
        analysis = await analyze_gpx(gpx_data)
        return AgentResult(
            agent_name=self.name, success=True, output=analysis,
            thinking=f"GPX 分析: {analysis['distance_km']}km, 爬升{analysis['elevation_gain_m']}m",
        )

    async def _analyze_known_route(self, user_input: str, context: dict | None = None) -> AgentResult:
        """基于知识库匹配路线"""
        matched = None
        # 1. 精确匹配：KB 名称完整出现在 query 中
        for name, info in KNOWN_ROUTES.items():
            if name in user_input:
                matched = dict(info)
                matched["name"] = name
                break
        # 2. 前缀匹配：query 开头词是 KB 名称的子串（如"格聂"→"格聂C线"）
        if not matched:
            for name, info in KNOWN_ROUTES.items():
                # 提取 query 开头的 2-6 字词
                for n in range(2, min(7, len(user_input) + 1)):
                    prefix = user_input[:n]
                    if prefix in name:
                        matched = dict(info)
                        matched["name"] = name
                        break
                if matched:
                    break

        if matched:
            return AgentResult(agent_name=self.name, success=True, output=matched,
                thinking=f"知识库匹配: {matched['name']} {matched['distance_km']}km")
        else:
            return AgentResult(agent_name=self.name, success=True,
                output={"message": "知识库未匹配"})

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        return "[RouteAnalyst] 正在分析路线..."
