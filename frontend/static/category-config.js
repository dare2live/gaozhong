/* 数据域类目 → 颜色/标签 映射配置 (单一来源, 防多文件漂移).
 *
 * 用户 no-hardcode 硬约束。原 STAGE_C/STATUS/SKILL_COLOR 在 k12/dict/beike 各写一份且**已漂移**
 * (k12 有"小学"无"高中", dict 反之) → 收口此处, 各模块读 window.GZ_CAT。改色/加类目 = 改这一处。
 * 注: 这些是**数据编码色**(学段/考点状态/设问技能 → 色), 与 design-system.css 的 UI accent 令牌正交;
 * ECharts 需 JS hex 值, 故配置在 JS 而非 CSS 变量。
 */
window.GZ_CAT = {
  // 学段 → 色 (完整并集, 小学→高中全; 防 k12/dict 各缺一键的漂移 bug)
  stage: {
    "小学": "#9FE1CB", "初中": "#1D9E75", "义务教育": "#85B7EB",
    "高中": "#185FA5", "高中必修": "#378ADD", "高中选修": "#185FA5",
  },
  // 词汇 exam_status 四象限 → [标签, 色] (课标∩真题双可验集合)
  examStatus: {
    core: ["核心", "#185FA5"], standard: ["标准", "#1D9E75"],
    HV_extra: ["高频超纲", "#BA7517"], LV_extra: ["低频超纲", "#B4B2A9"],
  },
  // 设问技能 → 色 (推断=强调红, 与备课 D 区一致)
  skill: {
    "推断": "#993C1D", "理解具体信息": "#185FA5",
    "理解主旨要义": "#85B7EB", "理解词汇": "#B4B2A9",
  },
};
