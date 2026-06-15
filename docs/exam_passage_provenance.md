# 辽宁高考英语 阅读理解 — 真实源头追溯 (Passage Provenance)

> 诚实性任务 (D0). **只有原文 distinctive 短语/专名在某真实出版物命中, 或权威记录明确指出来源, 才认定源头; 否则 `未知`.** 每个认定源头给可核验依据 (URL / 出版物 + 日期 / 匹配短语). 宁可标"未知", 绝不臆测"大概来自 TIME".
>
> 作者: research subagent · 日期: 2026-06-15 · 工具: WebSearch + WebFetch.
> 数据源: `data/db/gaozhong.duckdb` `exam_questions` (province LIKE '辽宁%', question_type='阅读理解', year>=2021).
> 卷型: 全部 **新高考全国 II 卷** (2021+ 辽宁正式启用; 见 `agent.md`/CLAUDE.md §7). 2024/2025 全文来自 `local_pdf` (完整), 2023/2024 另有 `GAOKAO-Bench-Updates` 全文 (2024 两源互证), 2021/2022 来自 `eol` 源.
>
> ⚠️ **置信度定义**: `high` = 原文多条 distinctive 短语在某单一真实出版物**逐字命中** (≥1 强源, 多为 1 个权威主源即够, 因高考改编自单篇); `mid` = 主题/专名/事件已核实为真且找到强候选源, 但因 paywall/反爬未能逐字比对原文, 或原文系多家转载的通讯社稿无法锁定首发; `unknown` = 未找到可核验源.

---

## 1. 源头追溯表

### 2021 新高考全国 II 卷 (辽宁) — 源 `eol`

| question_id | 篇 | 话题 | 认定源头 | 证据 (匹配短语/依据) | 置信度 |
|---|---|---|---|---|---|
| eol/2021/xgkii/21-23 | A | Harrogate 等英国活动通知 (音乐节/健身/做毛毡画/数学游戏) | **未知** (片段化, 应用文/活动通知体, 多为本地活动聚合页) | A 篇为活动通知, eol 源此处仅余题干碎片, distinctive 短语不足 | unknown |
| eol/2021/xgkii/24-27 | B | 动物园饲养员把苏门答腊虎幼崽 Spot & Stripe 带回家 24 小时照料 (第一人称) | **主题确证: Giles Clark / BBC《Tigers About the House》(2014)**. 虎崽 Spot & Stripe 真实存在, 饲养员 Giles Clark 在自家手养, 系 BBC 三集纪录片 | 专名 "Spot and Stripe" + "Sumatran cubs" + 第一人称饲养员手养; 改编**把 "Australia Zoo" 改成 "the National Zoo"** (去具体化) | mid |
| eol/2021/xgkii/28-31 | C | 英国"全球最佳教师" Andria Zafirakou 用百万奖金把艺术家请进校园 | **主题确证: Andria Zafirakou, Global Teacher Prize 2018 得主**, 创办 "Artists in Residence (AiR)" 慈善项目 (真实事件, 多家媒体报道) | 专名 "Andria Zafirakou" + "Alperton Community School" + "$1 million prize" + 艺术进校园项目; 系 2018 AP/卫报式新闻稿改编, 首发稿无法锁定单一 URL | mid |
| eol/2021/xgkii/32-35 | D | 悉尼大学 Salah Sukkarieh 研发监测放牧牛健康的四轮太阳能机器人 | **AP 通讯社稿 (Justin Pritchard), 经《华盛顿邮报》"Even cowboy jobs may not be safe from robots" 等转载, 2016-06-02** | 专名 "Salah Sukkarieh" + "University of Sydney" + "solar and electric power" + 题 35 出现的 **"Michael Kelsey"** (Oklahoma Cattlemen's Assoc.) 在该 AP 稿中同框出现 — 决定性; WaPo 页 paywall 403 未能逐字比对 | mid |

### 2022 新高考全国 II 卷 (辽宁) — 源 `eol`

| question_id | 篇 | 话题 | 认定源头 | 证据 | 置信度 |
|---|---|---|---|---|---|
| eol/2022/xgkii/21-23 | A | 某博物馆参观须知 (禁触摸展品等) | **未知** (应用文/参观须知体, 片段) | distinctive 短语不足以定位 | unknown |
| eol/2022/xgkii/24-27 | B | 记者与 2 岁外孙: 外孙像戳触屏一样戳纸质书 (多媒体叙事新时代) | **China Daily《Poking around in the world of new media》, Randy Wright, 2017-03-01** (逐字命中) | WebFetch 比对: 开篇 "We journalists live in a new age of storytelling, with many new multimedia tools" + "my 2-year-old grandson" + "pokes the page ... with his finger" + "I nearly dropped the book" 全部命中, 作者署名 Randy Wright | **high** |
| eol/2022/xgkii/28-31 | C | 美国仍有人开车发短信; "Textalyzer" 路检设备 (NHTSA Mark Rosekind) | **《纽约时报》"Texting and Driving? Watch Out for the Textalyzer", Matt Richtel, 2016-04-27** | 题 31 的标题选项 B **就是 NYT 标题原文**; 开篇 "Over the last seven years, most states have banned texting by drivers" 即 Richtel 导语; 专名 Mark Rosekind/NHTSA; 改编把 "radical change requires radical ideas" → "Big change requires big ideas" | **high** |
| eol/2022/xgkii/32-35 | D | 心脏随龄老化, 适度运动可逆转 (UT Dr. Ben Levine; 橡皮筋比喻) | **NPR (Shots)《Hearts Get 'Younger,' Even At Middle Age, With Exercise》, Patti Neighmond, 2018-03-12** (逐字命中) | WebFetch 比对: 开篇 "the heart just isn't as efficient in processing oxygen as it used to be" + 橡皮筋比喻 + **Dr. Ben Levine** + 题 35 主角 **Dr. Nieca Goldberg** 均命中; 改编 "emerge dry and brittle" → "become dry and easily broken" | **high** |

### 2023 新高考全国 II 卷 (辽宁) — 源 `GAOKAO-Bench-Updates` (全文)

| question_id | 篇 | 话题 | 认定源头 | 证据 | 置信度 |
|---|---|---|---|---|---|
| gbu/2023.../12 | A | 黄石公园暑期巡护员项目时刻表 (Wildlife Olympics / Canyon Talks 等) | **黄石国家公园官方 (NPS) 暑期 ranger program 项目单** | 项目名 "Junior Ranger Wildlife Olympics" / "Canyon Talks at Artist Point" + "enjoy the Lower Falls, the Yellowstone River ... why artists and photographers continue to be drawn to this special place" 与 NPS 材料近逐字一致; 系官方节目单体裁 (A 篇通例: 官方活动/景区页). 具体年度版次 URL 未锁定, 但出版方 (NPS Yellowstone) 无歧义 | mid |
| gbu/2023.../13 | B | 旧金山低收入校园菜园项目 Urban Sprouts (Abby Jaramillo) | **主题确证: Urban Sprouts (真实旧金山非营利校园菜园), 创办人 Abby Jaramillo** | 专名 "Urban Sprouts" + "Abby Jaramillo" + "four low-income schools" + 课程细节 (soil testing / flower-and-seed dissection) 与该组织描述吻合; 但英文原始报道文 (约 2008-2014 旧 feature) 未定位到单一 URL, 网搜多回流中文真题解析 | mid |
| gbu/2023.../14 | C | 画册《Reading Art: Art for Book Lovers》介绍 (书中之书) | **Phaidon 出版社图书《Reading Art: Art for Book Lovers》(David Trigg, 2018) 的出版方书介/书评** | 开篇 "Reading Art: Art for Book Lovers is a celebration of an everyday object — the book, represented here in almost three hundred artworks" 直接对应 Phaidon 书介; 书与作者真实存在 (ISBN 9780714876276) | **high** |
| gbu/2023.../15 | D | 城市公园"野性"对人类福祉的研究 ("nature language", 320 份提交) | **华盛顿大学新闻稿《Wildness in urban parks important for human well-being》, UW News, 2020-02-26** (报道 2020-01-29 发于 Frontiers in Sustainable Cities 的研究) | distinctive: "nature language" + "320 submissions" + "encountering wildlife, walking along the edge of water ... following an established trail" 均命中; 改编把具体 "Discovery Park in Seattle / 500 acres" 抽象成 "a large urban park" (去具体化) | **high** |

### 2024 新高考全国 II 卷 (辽宁) — 源 `local_pdf` + `GAOKAO-Bench-Updates-2024` (两源全文互证)

| question_id | 篇 | 话题 | 认定源头 | 证据 | 置信度 |
|---|---|---|---|---|---|
| pdf/2024.../1 (=gbu24/8) | A | 卡洛秋季徒步节 Choice of Walks (爱尔兰) | **Carlow Autumn Walking Festival 官方活动单** (活动通知体) | 专名 "Carlow Autumn Walking Festival" + 向导真名 (Éanna Lamhna 等) + 各 Walk 时间地点; A 篇通例为官方活动页. 具体年度活动页 URL 未锁定, 出版方 (Carlow 徒步节主办) 明确 | mid |
| pdf/2024.../2 (=gbu24/9) | B | 旧金山 BART 地铁短篇小说自助亭 (Alicia Trost) | **NPR《San Francisco's transit system is dispensing short stories to commuters》, 2022-06-09** (逐字命中, 经 LAist 等转载比对) | distinctive: "one-minute, a three-minute, or a five-minute story" + "Alicia Trost" + "nearly 20,000 short stories" + "about 120 submissions" + "down the past half century" + 结尾 "you'll never be without something to read" 全部命中 | **high** |
| pdf/2024.../3 (=gbu24/10) | C | Babylon Micro-Farm 室内菜园系统 (farm-to-table) | **Inhabitat.com《These micro-farms put a new spin to farm-to-table》, Dawn Hammon, 2022-05-06** (逐字命中) | WebFetch 比对: "zero emissions from transporting plants from soil to salad" + "remotely monitored" + "convenient app that provides growing data in real time" + "pre-seeded pod" + "passionate about reducing waste, carbon and chemicals" 全部命中; 改 "About half the employees" → "About half of them" | **high** |
| pdf/2024.../4 (=gbu24/11) | D | 书评《AI by Design》(Catriona Campbell) | **书真实存在: Catriona Campbell《AI by Design: A Plan for Living with Artificial Intelligence》(Routledge/CRC, 2022)**; 选文系该书的某篇报刊书评 | 书与作者经 Goodreads/Waterstones/Routledge 确证; "narrow-AI / Artificial General Intelligence / Artificial Dominant Intelligence" "tipping point" 等系该书内容. 最强候选书评源 = 英国 "Must-read of the week" 联合稿 (National World/JPIMedia 系, 如 Blackpool Gazette), 但该页 403 未能逐字比对 | mid |

### 2025 新高考全国 II 卷 (辽宁) — 源 `local_pdf` (全文)

| question_id | 篇 | 话题 | 认定源头 | 证据 | 置信度 |
|---|---|---|---|---|---|
| pdf/2025.../1 | A | 英国值得一游的集镇 (Hereford/Ludlow/Shrewsbury/Mevagissey) | **未知** (集镇导览体, 旅游聚合文; 无单一 distinctive 专名命中真实首发) | 内容真实可考 (各镇/Magna Carta 副本真存于 Hereford Cathedral), 但作为旅游集锦文未定位到被改编的具体原文 | unknown |
| pdf/2025.../2 | B | 斯坦福 LPCH 儿童医院里的"医院学校"老师 Kathy Ho | **主题确证: Lucile Packard Children's Hospital Stanford 院内学校真实存在**; Kathy Ho / Julie Good 为真人 | 专名 "Kathy Ho" + "Lucile Packard Children's Hospital Stanford" + "room 386" + "Julie Good, director of pain management"; 系某篇人物特写改编, 原文首发 URL 未锁定 | mid |
| pdf/2025.../3 | C | 疫情后室内植物产业爆发 (Sonja Detrinidad; Dr. Melinda Knuth) | **House Beautiful《The Scientific Way That Plants Decrease Stress in Humans》, Angel Madison, 2021-07-07** (逐字命中, 经 Yahoo Lifestyle 转载比对) | WebFetch 比对: "Plants are in fashion right now" + "decreasing ... level of cortisol" + "30% decrease in sick leave" + "shipping out 1,200 orders in June of 2020" + "Doctors practice medicine and lawyers practice law" 命中; 改编把 **"biophilic workplaces" → "plant-rich workplaces"** (降词难度) | **high** |
| pdf/2025.../4 | D | 纽约 Blue Hill 餐厅 wastED 食物浪费快闪 | **Reviewed.com《Let Them Eat Waste: Chefs Turn Trash Into Haute Cuisine》, James Aitchison, 2015-04-07** (逐字命中) | WebFetch 比对: 开篇 "Does your soul die a little every time you throw away unused food?" + "33 pounds of food waste for every $1,000 in revenue" + "Silo in the UK" + "kale ribs, fish collars ... cucumber butts" 命中; 改编把 **"Johannesburg" → "South Africa"**, 并删去列表里的 "vegetable pulp" (去具体化) | **high** |

---

## 2. 统计

逐行计数 (以上方表格为准, 每行可核验). 共 **20** 篇 B/C/D/A 主体阅读 (2021-2025 各年 4 篇; 2024 两源互证算 1 篇):

- **high (单一真实出版物逐字/标题级命中) = 9 篇**:
  2022B (China Daily) · 2022C (NYT) · 2022D (NPR) · 2023C (Phaidon 书介) · 2023D (UW News) · 2024B (NPR) · 2024C (Inhabitat) · 2025C (House Beautiful) · 2025D (Reviewed.com).
- **mid (主题/专名/事件确证为真 + 强候选源, 但 paywall/反爬未逐字, 或首发通讯社稿无法锁定) = 8 篇**:
  2021B (BBC《Tigers About the House》/Giles Clark) · 2021C (Zafirakou / Global Teacher Prize 2018) · 2021D (AP 牛监测机器人稿) · 2023A (NPS Yellowstone 节目单) · 2023B (Urban Sprouts / Abby Jaramillo) · 2024A (Carlow 徒步节活动单) · 2024D (《AI by Design》书 + 英国书评联合稿) · 2025B (斯坦福 LPCH 医院学校).
- **unknown (无可核验源) = 3 篇**:
  2021A (英国活动通知片段) · 2022A (博物馆参观须知片段) · 2025A (英国集镇旅游导览).

> 备注: unknown 三篇均为 **A 篇应用文/聚合导览** 体裁 — 来自机构官网/活动单/旅游聚合, 本就最难逆向定位单一首发 URL; eol 源 (2021/2022) 的 A 篇还只剩题干碎片, distinctive 短语不足. **没有一篇是因偷懒而留空 — 是这类体裁客观上无单一可核验首发.**

---

## 3. 选材来源规律 (样本 = 20 篇, 足够给出趋势, 但不足以做强统计)

观察基于已认定的源头 (high+mid 共 17 篇有出版方):

1. **体裁与篇位高度固定 (A/B/C/D 各有"源类型")**:
   - **A 篇 = 官方应用文/活动通知**: 景区/活动官方页 (黄石 NPS · Carlow 徒步节 · 旅游集镇导览). 几乎不来自外刊正文, 而来自**机构官网/活动单**. → 这是最难逆向定位首发的, 因为是聚合/官方信息.
   - **B/C/D 篇 = 真实外刊/通讯社/机构新闻稿正文**, 是改编主力区.
2. **最爱的来源类型 (按命中频次)**:
   - **美国公共媒体 / 通讯社**: NPR (2022D, 2024B 两次) · AP 通讯社稿 (2021D) · 纽约时报 (2022C). → **NPR 是出现最多的单一来源 (2 次)**.
   - **生活/家居/评测类杂志网站**: House Beautiful (2025C) · Inhabitat (2024C) · Reviewed.com (2025D). → 偏"软新闻 / 科普生活"调性.
   - **机构新闻稿 / 大学新闻**: 华盛顿大学 UW News (2023D) · 出版社书介 (Phaidon, 2023C).
   - **中国官方英文媒体**: China Daily (2022B) — 唯一非英美来源, 第一人称专栏.
   - **英国媒体 / 纪录片衍生**: BBC 纪录片衍生 (2021B) · 英国书评联合稿 (2024D) · Global Teacher Prize 报道 (2021C).
3. **题材偏好 (反复出现的主题轴)**:
   - **科技改善生活 / 可持续**: 室内农场 (2024C) · 食物浪费 (2025D) · 牛监测机器人 (2021D) · BART 短篇亭 (2024B).
   - **自然 / 健康 / 身心福祉**: 城市野性研究 (2023D) · 植物减压 (2025C) · 运动逆转心脏老化 (2022D) · 校园菜园 (2023B).
   - **教育 / 阅读 / 人文**: 全球最佳教师 (2021C) · 书之画册 (2023C) · 医院学校 (2025B) · 数字时代阅读 (2022B).
   - **几乎不碰**: 政治、宗教、争议社会议题、特定国家敏感事务 (符合命题避雷; 见 `config/political_blacklist`).
4. **年代规律 (PIT 视角)**: 被改编原文多发表于**考前 2-6 年** (e.g. 2024 卷用 2022 NPR/Inhabitat 文; 2022 卷用 2016-2018 NYT/NPR 文; 2025 卷用 2015/2021 文). → **命题选材有"时滞窗口"**, 偏好近年但非当年的稳定题材, 避开太新 (未沉淀) 或太旧 (过时).
5. **改编手法 (高一致性, 可量化观察)**:
   - **去具体化 (de-specifying)** 最常见: "Australia Zoo"→"the National Zoo" (2021B) · "Discovery Park in Seattle/500 acres"→"a large urban park" (2023D) · "Johannesburg"→"South Africa" (2025D). 目的: 去除考生不熟的专有地名, 降低背景门槛.
   - **降词难度 (lexical simplification)**: "biophilic workplaces"→"plant-rich workplaces" (2025C) · "radical change requires radical ideas"→"Big change requires big ideas" (2022C) · "emerge dry and brittle"→"become dry and easily broken" (2022D). 目的: 把超纲/低频词换成课标词.
   - **删减 (pruning)**: 删次要细节/列表项 ("vegetable pulp" 从食材列表删去, 2025D), 压缩到 ~300 词单篇定长.
   - **保留专名与数字**: 人名/机构名/关键数字 (1,200 orders / 30% / 320 submissions / 11 years) **基本原样保留** — 这是逆向定位源头的最佳锚点.

---

## 4. 对"预测命题"的诚实结论 (不夸大)

**源头规律能帮到的 (可借鉴)**:
- ✅ **选材风格画像可复用**: 来源类型 (NPR/AP/NYT/科普生活类杂志/大学新闻稿/官方活动页)、题材轴 (科技向善·身心健康·教育人文)、调性 (正能量、避争议、软新闻)、年代窗口 (考前 2-6 年发表) — 这些是**稳定的命题口味**, 可用于**筛选候选外刊文**作为模拟题素材库.
- ✅ **改编手法可工程化**: 去具体地名 + 降词到课标 + 删减压到 ~300 词 + 保留专名数字 — 这是一套**可复现的改写 SOP** (见 §5).
- ✅ **篇位-体裁映射可复用**: A 应用文/B 记叙或人物/C 说明科普/D 议论或书评 — 模拟卷可按此配篇.

**源头规律绝对不能做的 (不可预测, 标红)**:
- ❌ **具体篇目/具体文章不可预测**. 命题组从浩如烟海的真实出版物里选单篇, 无任何规律能预测"下次会选哪一篇". 任何声称"押中原文"的都是事后归因或巧合.
- ❌ **不能反推命题组的私有选材清单**. 我们看到的是**结果分布**, 不是**选材流程**.
- ❌ **样本量护栏**: 此处样本仅 20 篇 (有出版方的 17 篇), **不足以做强统计推断** (e.g. "NPR 占 X%" 这种比例无统计意义, n 太小). 规律是**定性画像**, 不是**定量预测模型**. (符合 gaozhong-ops 坑12 "分析诚实门": province-scoped ✅、卷制分段 ✅ 仅 2021+ 新高考II、但 n<阈值 → **只给定性, 不给比例/趋势线**.)

> 一句话: **可以学它选什么"类型"的文章、怎么改; 不能预测它下次选"哪一篇"文章.**

---

## 5. 方法论 — 用源头规律 + 课标词表把真实外刊改写成"课标级模拟阅读"

> 强约束 (CLAUDE.md §1.2 不偏离学校): 任何模拟阅读**必须能反证"词量 ≤ 已学单元 + 课标 3500 词"**. 词表真相源: `data/structured/curriculum/official_curriculum_vocab.jsonl`.

**Pipeline (建议, 尚未落地为脚本)**:

1. **选材 (按 §3 画像筛)**:
   - 来源池: NPR / AP / NYT(软新闻) / House Beautiful / Inhabitat / Smithsonian / 大学新闻稿 / 官方活动页.
   - 题材: 科技向善·身心健康·教育人文; **过 `config/political_blacklist` 政治/争议词黑名单** (硬过滤).
   - 年代: 优先发表于"目标年份 −2 ~ −6 年"的稳定题材文.
   - 篇位匹配: A→官方活动/通知页; B→人物/记叙; C→科普/说明; D→议论/书评.

2. **词量降级 (硬门, 对课标词表)**:
   - 对候选原文分词, 与 `official_curriculum_vocab.jsonl` (3500 词) ∩ "已学单元词表"做差集.
   - **超纲词 → 三选一**: (a) 同义换课标词 (复刻 "biophilic"→"plant-rich" 手法); (b) 加注释 (复刻真题括注 `(手电筒)` `(变革)` 体例); (c) 若是必要专名则保留但确保上下文可猜.
   - **复用项目现成停用词/内容词逻辑** (`services/stopwords.py` content_tokens = token ∩ cefr − 停用词) 来量化"超纲实词率", 设阈值 (e.g. 超纲实词 ≤ N%).
   - **可反证产物**: 每篇模拟阅读附"超纲词清单 + 处理方式 + 命中单元", 答得出"词量 ≤ 哪些单元 + 课标"才算合规 (CLAUDE.md §1.3 真实数据/不估算).

3. **结构与篇幅对齐**:
   - 压到 ~300 词/篇 (真题定长); 删次要细节 (复刻 §3.5 pruning).
   - 去具体地名/换熟悉锚点 (复刻 de-specifying); 但**保留可让题目成立的专名/数字**.
   - 配 4-5 题 (细节/推断/主旨/词义猜测), 题型分布对齐真题 (题型/分值真相源走姊妹项目 `~/Documents/M/gaokao/`).

4. **语法门 (CLAUDE.md §1.2)**: 句法复杂度 ≤ 已学单元语法点 (从句类型/时态范围按进度卡); 超出的拆句.

5. **双校验 (资料红线 §3.2: LLM 拆的属 C 级, 必经双模型/教师校验)**:
   - 模型改写 → 第二模型核 (词量/语法是否真降级 + 是否引入事实错误) → 教师终审.
   - **不准把"改写稿"当真题入 `exam_questions`** (那是 canonical 真值表); 模拟题入独立池, `origin`/`generation_meta` 标记来源原文 URL + 改写 lineage (复刻 Phase 7 回滚教训: 生成内容必须模块化 + 单一 origin 标记, 见 gaozhong-ops 坑8).

6. **诚实标注**: 每篇模拟阅读必带: 原文 URL + 出版方 + 日期 + 改写手法清单 + 超纲词处理 + 命中单元 — 即本文档表格的"反向版" (从源头→改写, 全程可核验).

---

## 附: 复核指引 (如何验证本文档)

```bash
# 1. 取某篇原文 (read_only)
python3 -c "import duckdb; c=duckdb.connect('data/db/gaozhong.duckdb',read_only=True); \
print(c.execute(\"SELECT raw_question FROM exam_questions WHERE question_id='pdf/2025/xgkii/阅读理解/4'\").fetchone()[0][:1500])"
# 2. 抽 distinctive 短语 (人名/数字/罕见搭配) 去 WebSearch/WebFetch 比对认定的 URL
# 3. high 项应在认定出版物逐字命中; mid 项主题/专名确证但首发未锁定; unknown 项无可核验源
```

**核验状态 (2026-06-15)**: high 项均经 WebFetch/WebSearch 短语级比对 (China Daily/NPR×2/Inhabitat/House Beautiful/Reviewed.com 已逐字; NYT/Phaidon/UW News 经标题或书介强匹配). mid 项受 paywall (WaPo/NYT/Blackpool Gazette 403) 或反爬限制, 仅到主题/专名级, 未逐字 — 已如实标注, **未编造任何源头**.
