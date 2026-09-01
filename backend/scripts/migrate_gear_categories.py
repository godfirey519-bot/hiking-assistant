"""迁移 gear_categories 使其与代码 DEFAULT_CATEGORIES 对齐（幂等，可重复执行）。

背景: 早期版本的 DEFAULT_CATEGORIES 与当前代码不一致，导致前端 Equipment 页
"使用预设模板快速填充" 按分类名匹配模板时静默跳过多个分类。

迁移规则 (旧 → 新):
  炊具系统 → 饮食系统      (1:1 改名)
  急救     → 急救/药品     (1:1 改名)
  饮水/食物 → 合并入 饮食系统 (其装备条目改挂到饮食系统后删除分类)
  新增: 背负系统, 登山杖/冰爪
  其余分类: 修正 sort_order 对齐代码

用法: python scripts/migrate_gear_categories.py
"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update

from app.database import async_session
from app.models.gear import GearCategory, GearItem

# 与 app/api/equipment.py DEFAULT_CATEGORIES 保持一致
CANONICAL: dict[str, tuple[str, int]] = {
    "背负系统": ("backpack", 1),
    "睡眠系统": ("tent", 2),
    "饮食系统": ("cooking-pot", 3),
    "服装-上衣": ("shirt", 4),
    "服装-下装": ("pants", 5),
    "鞋袜": ("footprints", 6),
    "登山杖/冰爪": ("trekking-pole", 7),
    "照明": ("flashlight", 8),
    "电子设备": ("smartphone", 9),
    "急救/药品": ("heart-pulse", 10),
    "导航通讯": ("map", 11),
    "工具": ("wrench", 12),
    "其他": ("package", 99),
}

RENAME = {"炊具系统": "饮食系统", "急救": "急救/药品"}
MERGE_INTO = {"饮水": "饮食系统", "食物": "饮食系统"}


async def migrate() -> None:
    async with async_session() as db:
        result = await db.execute(select(GearCategory))
        cats = {c.name: c for c in result.scalars().all()}
        print(f"当前分类 ({len(cats)}): {list(cats.keys())}")

        # 1) 改名
        for old, new in RENAME.items():
            if old in cats and new not in cats:
                cats[old].name = new
                cats[new] = cats.pop(old)
                print(f"  改名: {old} -> {new}")

        # 2) 合并: 把 MERGE_INTO 的分类装备改挂目标分类后删除
        for src, dst in MERGE_INTO.items():
            if src in cats and dst in cats:
                await db.execute(
                    update(GearItem).where(GearItem.category_id == cats[src].id).values(category_id=cats[dst].id)
                )
                await db.delete(cats[src])
                print(f"  合并: {src} -> {dst} (装备改挂, 删除分类)")
                del cats[src]

        # 3) 补齐缺失分类
        for name, (icon, sort_order) in CANONICAL.items():
            if name not in cats:
                cats[name] = GearCategory(name=name, icon=icon, sort_order=sort_order)
                db.add(cats[name])
                print(f"  新增: {name} (icon={icon}, sort={sort_order})")

        # 4) 修正 icon + sort_order
        for name, (icon, sort_order) in CANONICAL.items():
            if name in cats:
                if cats[name].icon != icon or cats[name].sort_order != sort_order:
                    cats[name].icon = icon
                    cats[name].sort_order = sort_order
                    print(f"  修正: {name} -> icon={icon}, sort={sort_order}")

        await db.commit()

        # 验证
        result = await db.execute(select(GearCategory).order_by(GearCategory.sort_order))
        final = [(c.name, c.icon, c.sort_order) for c in result.scalars().all()]
        print(f"\n迁移完成 ({len(final)} 分类):")
        for name, icon, sort in final:
            print(f"  [{sort:>2}] {name} ({icon})")

        expected = set(CANONICAL)
        got = {n for n, _, _ in final}
        ok = got == expected and len(final) == len(CANONICAL)
        print(f"\n{'✅ 与代码 DEFAULT_CATEGORIES 完全一致' if ok else '❌ 仍有差异: 缺 ' + str(expected - got)}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(migrate())
