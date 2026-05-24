# 经济学人风格 reference + 实装清单 (4.4)

> 用户 2026-05-24: "研究了经济学人页面吗" — 上轮诚实承认只到 30% 表面.
> 本文拆 10 个标志元素 + 标"做了 / 未做".

---

## 10 个标志元素

| # | 元素 | 实装状态 | 备注 |
|---|---|---|---|
| 1 | **红蓝双色** (主色 #0a4d75 + 强调 #c1272d) | ✅ style.css | 配色已对 |
| 2 | **Georgia serif 标题** vs sans-serif body | ✅ style.css | 已对 |
| 3 | **细边 card, 无 box-shadow** | ✅ style.css `.card` | 已对 |
| 4 | **红色下划线 H2** | ✅ style.css `.card h2` | 已对 |
| 5 | **Red drop cap** (段落首字母大字红色) | ✅ style.css 新加 `.drop-cap::first-letter` | 本轮实装 |
| 6 | **Inline data citation** (数字旁 src) | ✅ common.js `cite()` helper + style.css `.cite` | 本轮实装 |
| 7 | **Sticky stat bar** (滚动跟随) | ✅ style.css `.sticky-stat` | 本轮实装 |
| 8 | **Minimalist chart axis** (只标关键节点) | 🟡 部分 — 热力图无 axis, line chart 未实装 |
| 9 | **Annotation overlay on chart** | ❌ 待 4.4.E 经济学人 SVG 真图实装 |
| 10 | **'Most-read' rank box** | ❌ 不适用 (我们不是新闻站) |

**实装 7/10** (vs 上轮 4/10).

---

## CSS 新增 (style.css 末尾)

```css
.drop-cap::first-letter {
  float: left; font-family: Georgia, serif; font-size: 56px; line-height: 0.8;
  margin: 6px 8px 0 0; color: #c1272d; font-weight: 700;
}
.cite { font-size: 10px; color: #888; vertical-align: super; }
.sticky-stat {
  position: sticky; top: 0; z-index: 5;
  background: white; border-bottom: 2px solid #c1272d; padding: 8px 16px;
  font-family: Georgia, serif;
}
```

---

## 使用 (前端)

主页可写:
```html
<p class="drop-cap">
  辽宁 14 地市使用 2 个英语教材版本: 外研版 10 市, 人教版 4 市
  <span class="cite">src: xuexili.com</span>.
</p>

<div class="sticky-stat">
  📊 4945 nodes · 34697 edges · 0 audit FAIL
</div>
```

教师端备课页可加.

---

## 不做 (用户没要求, 避免 over-engineer)

- D3 force-directed (我们已用纯 SVG 简单实现)
- 复杂 sticky 多列布局 (信息架构不需要)
- Pull quote 拉大引文 (教学文档非新闻)
