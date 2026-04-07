# Workout Dashboard — Project Brief

## 项目概述
一个本地运动数据可视化 dashboard，读取 Apple Calendar 导出的 .ics 文件，生成静态 HTML 页面。这是一个 mini personal project。

---

## 数据来源

三个 .ics 文件（Apple Calendar 订阅导出）：
- `运动.ics`
- `锻炼.ics`
- `Eden.ics`（目前为空，但保留兼容）

**处理规则：**
- 同一天、同一课程名出现在多个 .ics → merge 成一条，不重复计算
- 非运动事件（考试、机票、酒店、押金等）全部过滤掉
- 过滤逻辑：只保留能匹配到以下分类的事件

---

## 运动分类（全英文，无「其他」）

| 分类 | 匹配关键词 / 课程名 |
|------|-------------------|
| **Pilates & Yoga** | pilates, reformer, yoga, moreyoga, flow ldn, tempo pilates, strength pilates, barre, barre fit |
| **Ride** | ride |
| **Tennis** | tennis, court, 网球, 🎾 |
| **Gym** | gym, strength & conditioning, wicked shapes, hyrox, body conditioning, functional fitness, boxfit, power pump, studio strength, bodypump, bodycombat, crossfit, gym session |
| **Hiking** | hiking, 徒步 |
| **Dance** | zumba, dance fitness, salsa, fitbounce, legs bums, step aerobics |
| **Swimming** | swim |
| **Squash** | squash |

> 如果一个事件无法匹配任何分类，直接跳过（不显示）。

---

## 功能需求

### 时间范围选择器
- 默认：**3个月**
- 可选项：1周 / 1个月 / 3个月 / 6个月 / 1年 / 全部
- 全局生效，影响所有图表和视图

### Tab 结构（tab 切换，不是单页滚动）

**Tab 1: Overview**
- 顶部 summary cards：
  - 总课程数
  - 运动天数
  - 累计运动时长（小时，基于 .ics 的开始/结束时间计算，若无时长信息则不显示）
  - 最常练的类型
- 趋势折线图（见下方说明）

**Tab 2: Weekly**
- 显示近4周（每周一到周日）
- 每天显示当天上了什么课（课程名 + 类型色块）
- 点击某一天 → 弹出详情：课程名称、类型、时长（如有）
- 每周小计：本周运动次数 + 累计时长

**Tab 3: By Type**
- 各类型的课程数量横向对比
- 柱状图，按所选时间范围统计

---

## 趋势折线图（Overview Tab 核心）

- X 轴粒度：默认**按周**，可切换为按月
- Y 轴：运动次数（or 时长，可切换）
- 多类型叠加显示：每个类型一条线，颜色区分
- Filter：可多选类型（默认全选），筛选后只显示选中的类型的线
- Filter 仅影响趋势图，不影响 Weekly 视图

---

## UI 风格

**整体感觉：** Linear / Apple 官网风格 — minimal、现代、克制、丝滑

**配色：**
- 背景：纯白 `#FFFFFF` 或极浅灰 `#F9F9F9`
- 文字：深黑 `#0A0A0A`（主）/ 中灰 `#6B6B6B`（次）/ 浅灰 `#D4D4D4`（border）
- 图表各类型配色（建议）：
  - Pilates & Yoga → `#0A0A0A`（黑）
  - Ride → `#3B3B3B`（深灰）
  - Tennis → `#6B6B6B`（中灰）
  - Gym → `#9B9B9B`
  - Hiking → `#B4B4B4`
  - Dance → `#C8C8C8`
  - Swimming → `#DCDCDC`
  - Squash → `#EFEFEF`

  > 如果纯灰阶在折线图上区分度不够，可以引入 1-2 个低饱和度的点缀色，保持整体克制感。

**字体：** 无衬线，优先 `-apple-system, BlinkMacSystemFont, "SF Pro Display"`，fallback `"Helvetica Neue", sans-serif`

**组件风格：**
- 无圆角或极小圆角（4px）
- border 用 `1px solid #E8E8E8`，不用阴影
- Tab 切换：下划线式，不用胶囊/按钮式
- Summary cards：极简数字卡片，label 小字灰色，数字大字黑色
- 按钮 / 选择器：outline 风格，无填充色

**参考图：** 黑白现代风格（已提供截图），高对比度文字 + 大量留白 + 几何感排版

---

## 技术要求

- 纯静态 HTML + CSS + JS（单文件输出）
- 图表库：Chart.js（CDN）
- 不依赖任何后端
- Python 脚本读取 .ics → 生成 dashboard.html

**文件结构：**
```
workout_dashboard/
├── generate_dashboard.py   ← 主脚本
├── dashboard.html          ← 生成物
└── data/
    ├── 运动.ics
    ├── 锻炼.ics
    └── Eden.ics
```

**运行方式：**
```bash
python3 generate_dashboard.py
open dashboard.html
```

---

## 给 Claude Code 的说明

以上是完整需求。请：
1. 先写 `generate_dashboard.py`，解析 .ics、分类、去重、生成数据
2. 再写 HTML 模板，实现所有 tab 和图表
3. 每完成一个模块告诉我，我会在浏览器里验证效果
4. UI 细节（间距、颜色、字体大小）按照上方风格规范执行，如有不确定的地方先问我
