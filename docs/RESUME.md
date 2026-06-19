# RESUME — 断点续传 (新 session 先读这个)

> 配 goal.md + CLAUDE.md + docs/architecture.md 用。本文件 = 最近进度 + 下一步, 更新于每个大节点。
> 🏛️ **平台级最高设计 = `docs/k12_platform_master_design.md`** (第一性原理顶层, 统一高中八铁律+初中子系统+核心竞争力)。新方向先读它。

## 最近 session (2026-06-17): 高中地基重审根治 + 初中子系统立项

### A. 高中数据地基重审 — 18 项数据正确性问题全清 (已 push)
前轮 14-问题审计 + 本轮对抗复核新发现 4 项, 全部根治。**三门全程绿** (D0 exit0 / moth PASS46 / stop_gate exit0)。
6 个 commit (e2dfc59→80e930c, 已 push origin/main):
1. **renjiao/waiyan 词表单一区段重写**: 跨单元重复 331+96→0 (字母总表/glossary 砸进尾单元污染); bixiu_2 U1 56→66; cefr 3055→3052(截国家表误纳)。
2. **exam-status 单一计算点** (#12/#13/#14): province-blind(§7违反) + 3处各算 + attrs整段覆盖 → 收口。grammar_4q 孪生同修。
3. **「考过」判定收口到 tests_word 边** (Rule1): core-无边 347→0 (你指出 token-bag vs 边不一致); build_tests_word 改 lemmatize+覆盖 cefr∪教材词。
4. **section 边界+截断** (#7/#9): 过宽 section 8→0(末单元吞 workbook/glossary, waiyan锚点cap + renjiao unit_overrides); section_text 20000截断 28→0。
5. **EOL 真题截断** (#8): raw_question 900硬截 11→0 + 空白13→0; 辽宁阅读 AVG 361→637。
6. **代码债**: data_accuracy_check<400 + _from_outline CC11→10。

教训沉淀: 每条修复都加 D0断言+moth(坑17双门); 门会假绿(坑1)——前轮审计漏 331/96 重复且其提议反是根源, 再审 Workflow 也误火过, **直接查 live DB 才靠谱**。moth coupling 验证: 单一真相拓扑健康(tests_word fan-in26=canonical读, 0孤儿引用)。

### B. 初中 + 中考 子系统 — 立项 + 顶层设计 (Phase 0 进行中)
用户立项: 拉沈阳中考+初中教材/课标, 像高中一样标注, 将来打通成"初中+高中统一平台"。
核心洞察: **stage 标注**(with/the 是小学词非高中词, 标 stage 后处理方便)。
- **顶层设计**: `docs/junior_high_subsystem_design.md` (architect-controller: genesis层 + stage原语 + separate-build-merge-later)。
- **已有资产**: 义务教育课标2022 PDF(三级体系,词汇表p94-152/语法p116,145) + 初中教材人教5册+外研6册 + renjiao_vocab.txt(4578)。
- **缺/待核**: 沈阳中考真题(命题方/卷型/源) + 沈阳初中教材版本(§1.4≥2源)。研究 Workflow wq9lacnsp 核验中。

### C. K12 分阶段 — 主业即时步 S3 落地 + 设计深化 (2026-06-17)
- **S3 stage 标注 (主业)**: 高中 word 节点加 `attrs_json.stage` (cefr_level 派生)。**with/the/and=义务教育**(修用户指出"非高中词处理不便", **tag-not-exclude 不删**)。分布: 义务教育1580/校本超纲1134/高中选修985/高中必修487/课标变形143。D0 加2断言(每分类词带stage + 义务教育==cefr义教1580)。单一writer exam_coverage 写。三门绿(moth PASS46)。
- **设计深化**: junior_high_subsystem_design.md §10 加**双向贯通+跨阶段语义扩展5维**(词义扩展/搭配/语法deepens/语篇/思维品质/主题spiral + 回溯补救+受控渗透+评估轨迹)。删重复 k12_staged_platform_design.md。
- ⚠️ power 案例: 当前 stage=高中必修(仅高中cefr口径); 用户举 power=初中力量 → 待 S1 初中三级加载后 S4 reconcile 重标。

### D. 定位已决「服务沈阳本市」+ 沪教牛津已获取 + Phase1 课标落地 (2026-06-17)
- **定位拍板 = 服务沈阳本市** → 主用版锚定**沪教牛津(广深沈通用,上海教育出版社)**; 中考=沈阳省统一卷(2024起)。
- **沪教牛津6册已下** `data/junior_high/textbooks/hujiao/{7a,7b,8a,8b,9a,9b}.pdf` (gitignore同高中, manifest track): 源 TapXWorld/ChinaTextbook(同高中渠道), §1.4 双源核验(版权页**辽宁批文[2018]3** + Oxford原作者 + 六三制7-9 ≠上海五四制 + 美英桥)。⚠️ 文本层 InDesign 乱码**待 OCR**(同高中坑)。⚠️ 别混同目录沪外教版。
- **Phase1 课标抽取**: 义务课标2022 → curriculum_vocab.jsonl(1647: 小学502+初中1145, 三级1593/1600 CMap漏~7不凑) + grammar(66)。stage切分用集合交(不靠损坏星标)。S4桥接: 义务∩高中义教=1333(84%)。
- **sherpa init**: `.sherpa/takeover.yaml` 定制为本仓3门+真相源(D0/stop/moth/map/junior), `sherpa takeover --repo .` 可用。

### E. Phase 2.5 — OCR 全局持久化 + 沪教词表 + S4 双向 stage reconcile (2026-06-17)
- **OCR 工具链全局持久**: PaddleOCR 官方装 `~/.venvs/ocr` (paddle3.3.1+paddleocr3.7.0), 全局入口 `ocr-python`/`paddleocr` (PATH 已含, **跨项目可用**), 模型缓存 `~/.paddlex`。docs/junior_high_ocr_setup.md。
- **纠正"文本层乱码"**: 沪教文本层**大体可读**(7a 122/138页), agent 的"全乱码"错(它用pymupdf)。**CID 只污染中文释义, 英文 word 可读** → stage 词表文本层全抽, OCR 仅补释义。交叉验证: 可读页文本层抽词 **171/171=100% 被OCR确证**。
- **沪教6册词表 926 distinct** (extract_hujiao_vocab.py): 首现去重 per-grade(七上159...九下127); 9b 29页累积总表回填 CID 卷释义 → **仅26释义待OCR**。∩课标三级=648(70%)。
- **S4 stage reconcile** (junior_stage_reconcile.py): 初中源(课标二级=小学/课标三级∪沪教=初中)细分高中 4329词 → **1763(40%)更精细**(义务教育1580→小学499+初中1264); **298 语义扩展候选**(power✓: 初中力量→高中power plant, design§10 边种子)。emit stage_refined.jsonl。

## 当前真相源 (live, 不引旧数字)
- 高中主门 (exit0/PASS): `data_accuracy_check.py` + `stop_gate.sh` + `moth assert` + `map doctor`
- 初中产物: `data/junior_high/structured/{curriculum_vocab,grammar_items,hujiao_vocab,stage_refined}.jsonl` (**尚无独立 D0 门** — 审计待补)
- 接手对账: `sherpa takeover --repo .`

### F. gaozhong 完全独立 + 主架构 v2 + Phase2.6 初中地基修复 (2026-06-17)
- **gaozhong↔gaokao 完全独立**: 切断 2 处运行时跨项目读(gaokao_bench/truth_baseline → 本地镜像);
  init_db 自包含复现 472/188; moth gaozhong-self-contained 守门。"不ATTACH"=跨项目非初中↔高中。
- **主架构 v2** (`docs/k12_platform_master_design.md`): 第一性原理 + 3视角对抗评审定稿(REVISE);
  sense级stage(power自反驳word单标签) + 单库node_type(弃双库三态) + 补学习者/语篇/思维节点 + tutorial契约。
- **Phase2.6 初中地基修复 — 初中 D0 全绿**: 建 junior_accuracy_check(8不变量, 坑17) + 接 stop_gate
  阻断路径(坑21, 对抗验证污染→exit2)。OCR 交叉验证(master§3)洗净课标: F1垃圾51→0 + goal恢复(glyph误解码)
  + F4沪教cid 176→0 + F6语法66→71 + 契约注册。词典门已证不净, OCR=视觉真值。

## 下一步 (Phase2.6 完成, 地基达标解锁 A/B/C)
- **A. Phase3 集成 (单库)**: stage_refined 回填高中 word 节点 stage + word_sense 节点(义项级) + 跨阶段 edges。
- **C. 沈阳中考真题** (可并行): 2024+省统一卷 → 中考考点 + 中考×高考**静态交叉点**(N=2 非趋势)。
- **B. 语义扩展边** (依赖 A+C): 298候选→跨stage语料 NLP pipeline → expands_sense/collocates_into。
- 余: F7 二级补转写3词(502→505, 低优先); F3 沪教*超纲词召回(926→~1200, 门现800-1400放行)。

## 真相源/门 (live, 不引文档旧数字)
- D0: `python3 scripts/data_accuracy_check.py` (exit0)
- 门: `bash scripts/stop_gate.sh` (exit0) + `moth assert --repo .` (PASS) + `moth coupling --repo .` (孤儿引用)
- 全库重建: `python3 scripts/init_db.py`; 重建后必重生成 `python3 scripts/build_vocab_classification.py`
- 状态总览: `python3 -m scripts.tools.map doctor`
