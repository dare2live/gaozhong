# 数据地基重审 — 14 确认问题 (2026-06-17, 5维度workflow+对抗复核)

> 触发: 用户 init_db rebuild 后要求重审地基。p182 pypdf漏页修复后, 5角色审计挖出更多。

## 1. [BLOCK] (教材词表完整性) renjiao bixiu_2 词表漏 167/256 词 (65%) — 双栏+PUA斜杠排版击穿行级正则

**detail**: renjiao/bixiu_2.pdf 词表页 pp109-116 是双栏排版且 IPA 斜杠是 PUA 字形  (非 ASCII '/')。两个抽取器(vocab.py 外研 / vocab_renjiao.py 人教)的 ENTRY_RE 都要求 ASCII '/ipa/' 且按整行匹配 → 这些页 pypdf 和 pdfplumber 都 0 entry 命中(不是丢页: pypdf/pdfplumber 页数同为 126, 每页~2200字符都在, 是正则不匹配)。坐标级双栏+PUA-aware 重提: bixiu_2 实有 256 distinct headwords, DB 仅 109 → 漏 167; 其中 120 个是课标(cefr)词, 56 个完全不在整个 unit_vocab_intro 表(announce/album/conference/define/descendant/embarrassing/function/author/award/approach/conquer/database/feast/fur 等真词带 IPA+POS+中文释义, 已 smoking-gun 在 PDF 逐条核到)。DB per-unit 分布 56/41/3/5/9 即指纹: U1-U2(单栏ASCII页107-108)正常, U3-U5(双栏PUA页109-116)塌缩到近零。

**fix**: Fix at the single-calculation-point (extraction services), not by patching data. Two coupled changes:
(1) PUA-slash tolerance: in both backend/services/extraction/vocab_renjiao.py and vocab.py, make the IPA delimiter accept the PUA glyph — replace the literal '/' in ENTRY_RE (and in the page-detector path `_entry_count`/`_find_vocab_pages`) with a class like [/] (and normalize ->'/' before parsing). The page-detector MUST use the same tolerant pattern or the PUA pages still get skipped at selection time.
(2) Double-column awareness: pages 110-117 are two-column; switch from pypdf line-level matching to pdfplumber word-extraction split into left/right columns by word x0 (page midpoint), reflow each column top-to-bottom, then run the entry regex. (A finditer-over-line approach can also work since two entries per physical line each contain their own slash-IPA-slash, but coordinate-based column split is more robust for wrapped zh_def lines.)
Re-run init_db (or the renjiao/waiyan vocab extract stage) to reload — reproducible from clean rebuild. Then add a D0 assertion in scripts/data_accuracy_check.py: per-volume robust headword count floor (renjiao bixiu_2 should be ~256, no unit collapsing to <~30 when sibling units are 50+) and a moth assertion locking it, so regression re-fails. Audit all other volumes for the same PUA-slash signature (grep page text for U+F02F density on vocab pages) since waiyan volumes likely share the defect.

**对抗复核**: CONFIRMED real BLOCK. Empirically verified with python3 against the live DB and PDF.

1) DB fingerprint matches exactly. Version-filtered `SELECT unit_number,count(*) FROM unit_vocab_intro WHERE version_key='renjiao' AND volume_key='bixiu_2'` returns [(1,56),(2,41),(3,3),(4,5),(5,9)] = 114 rows / 109 distinct — exactly the finding's numbers. (A naive query without the version filter returns 432/40

## 2. [WARN] (教材词表完整性) 全 renjiao 7 册 distinct 总计漏 ~193 词 — 同一双栏/PUA 根因, 程度不一

**detail**: 坐标级 robust 提取 vs DB distinct 逐册对比(renjiao): bixiu_2 漏 167(最重), xuanze_2 漏 62, xuanze_3 漏 46, bixiu_3 漏 31, bixiu_1 漏 23, xuanze_1 漏 9, xuanze_4 漏 10。bixiu_2 之外的册多为部分页双栏/边界词, 非整段塌缩(per-unit 分布无明显异常), 但仍是同一抽取器对 renjiao 多栏排版鲁棒性不足的连续表现。waiyan 侧坐标级核对几乎吻合(bixiu_1 漏1/bixiu_3 漏0/xuanze_1 漏0/bixiu_2 漏23 皆多词短语), 健康。

**fix**: Fix in /Users/dp/Documents/M/gaozhong/backend/services/extraction/vocab_renjiao.py — make entry detection recognize PUA-delimited IPA so the Appendices pages pass the _find_vocab_pages (≥8 entries) gate and get parsed.

1. Add a second entry regex (or broaden _entry_count) that detects the PUA-IPA entry shape: ^<english head-word> <run of PUA chars U+E000–U+F8FF (the IPA block, incl the / delimiter)> <pos.> <zh-def>. Concretely a pos-anchored pattern: ^\s*([a-zA-Z][a-zA-Z'\- ]*?)\s+[-][- ˈˌ]*\s*((?:n|v|vt|vi|adj|adv|prep|conj|pron|num|int|abbr)\.(?:\s*&\s*...)?)\s*(.*) — verified to match 30-47 entries/page on bixiu_2 pages 109-116.

2. Make _entry_count count BOTH ASCII-slash (ENTRY_RE) and PUA-slash matches, so _find_vocab_pages stops dropping the 8 Appendices pages.

3. In _parse_entry, try ENTRY_RE first, fall back to the PUA pattern; strip any stray PUA chars from the head-word; keep the existing single-word-vs-phrase handling (phrases with spaces are fine to keep or drop per current behavior, but the 149 bixiu_2 + 2 xuanze_4 single words must be recovered).

4. Regression gate (only-add, never-drop): for all 7 renjiao volumes dry-compare new vs old distinct + per-unit counts. Expected: bixiu_2 +149 single words, xuanze_4 +2, the other 5 volumes UNCHANGED (0 delta) — if any of bixiu_1/bixiu_3/xuanze_1/xuanze_2/xuanze_3 changes, the fix regressed or is pulling in phrases. Add a D0 assertion in scripts/data_accuracy_check.py locking renjiao bixiu_2 distinct >= ~257 (and a moth assertion) so the Appendices drop cannot silently return.

5. Do NOT switch to pdfplumber expecting it to fix this — the gate failure is PUA-encoded IPA, not two-column ordering; pdfplumber sees the same PUA glyphs.

**对抗复核**: CONFIRMED as a real data gap, but with materially corrected magnitude AND a different root cause than the finding states.

REAL MISSING WORDS (coordinate/PUA-robust extraction vs DB distinct, single English head-words only, phrases excluded):
- bixiu_2: 149 real words missing (NOT 167; finding's 167 over-counted by ~18 multi-word phrases). All 149 verified line-initial in the raw PDF (0 extractor 

## 3. [WARN] (教材词表完整性) 两道门对 per-volume 词表塌缩完全盲 — bixiu_2 缺 65% 仍双双绿过

**detail**: D0 强校验 data_accuracy_check.py:57 只断言全局 COUNT(*) unit_vocab_intro > 4000(=4056), bixiu_2 的洞被其它册补足而隐形。audit_vocab_per_volume 用 PER_VOL_MIN=80 的 per-volume distinct 阈值, 但 bixiu_2 有 109 distinct ≥ 80 → 判 OK。一个实际缺 65% 词的册, 因为绝对值过低阈值仍'合格'。这正是坑1(绿门假绿)/坑17(新数据漏 D0)的模式: 门没断言'每册词数 vs 该册PDF应有词数', 只断言一个松绝对下限。

**fix**: Both gates must assert against a per-volume/per-unit expected baseline (truth source = the volume's own PDF scale), not a single loose absolute floor. Concretely: (A) In backend/services/audit/coverage.py, replace the flat PER_VOL_MIN=80 in audit_vocab_per_volume with a per-volume relative expectation. Simplest robust anchor available now (no new schema needed): expect each volume's distinct-word count to be >= some fraction of the median of its same-version siblings (e.g. >= 0.6 * median(other volumes of same version_key)); renjiao/bixiu_2's 109 vs sibling median ~268 would then FAIL/WARN. If a stored PDF robust-count is added to the textbooks table, switch the anchor to `distinct >= pdf_robust_count * 0.9` per the finding. (B) Add a new per-unit completeness assertion (the project's own lesson L-2026-05-24-F already specifies it): WARN/FAIL when any (version,volume,unit) has < 10 distinct words — verified to flag exactly renjiao/bixiu_2 U3(3)/U4(5)/U5(9) and no false positives across the other 74 units. (C) Per pit/坑17 (new data must hit BOTH gates): mirror the assertion in scripts/data_accuracy_check.py — replace the lone global `unit_vocab_intro > 4000` (line 57) with a per-volume floor loop and the per-unit `<10` check, and register the same in the moth/stop_gate path so a partially-extracted volume can never pass green again. (D) Then actually backfill renjiao/bixiu_2 units 3/4/5 (re-run vocab_renjiao extractor or add unit_overrides as was done for U5) so the volume reaches its true ~250-270 word count, since the data hole is itself a D0 violation, not just a gate gap.

**对抗复核**: Confirmed with hard evidence on every load-bearing claim. (1) D0 gate scripts/data_accuracy_check.py:57 asserts only global `unit_vocab_intro > 4000` (actual 4056) — green. (2) backend/services/audit/coverage.py:14 uses a flat absolute PER_VOL_MIN=80; audit_vocab_per_volume's short-list requires n<80, so renjiao/bixiu_2's 109 distinct never enters it → severity returns OK (not even WARN). I ran th

## 4. [BLOCK] (课标语法完整性) grammar_items 漏 2 项：限制性/非限制性定语从句被 _skip_line 静默过滤 (108 应有, 实 106)

**detail**: 穷举 PDF 语法表 (p187-191) 结构标记: L1=3, L2=28, L3=71, L4=6, 共 108 项; DB 仅 106 (L4=4)。缺的恰是 p191「（3）定语从句」下的两个 a/b 子项: a.限制性定语从句(*=必修, id 应为 三/10/(3)/a, depth4)、b.非限制性定语从句(**=选必, id 应为 三/10/(3)/b)。两条都能匹配 RE_L4, 但 _skip_line() 的例句过滤 (英文字母占比 ratio>0.4) 把它们误杀——标签含关系代词清单 that/which/who/whom/whose, 占比 0.63/0.56。这与 p182 词汇丢页是同一类『静默缺失』, 只是机制不同(非丢页, 是 skip 误判)。

**fix**: Three-part fix in /Users/dp/Documents/M/gaozhong/scripts/lib/curriculum_grammar.py:

1) Order structural match before the example/ratio filter. In extract_grammar_items() (lines 96-100), do NOT call _skip_line() unconditionally before _try_match(). Either: (a) attempt _try_match first and only apply the ratio>0.4 example filter when no structural regex matched; or (b) inside _skip_line, exempt lines whose stripped form matches RE_L1..L4 (e.g. lines with an 'a-d.' / digit. / （n） / 一、 prefix) from the ratio rule. Verified safe — only the 2 定语从句 rows are affected across the page range.

2) Merge continuation visual lines for L4 before extracting suffix/_level_of. The `*`/`**` survival-level marker for 'a.'/'b.' sits on the NEXT visual line ('…限制性定语从句 *' / '…非限制性定语从句 **'). When a structural line matches RE_L4 and the following non-structural line is the label continuation (no new structural prefix, not skippable as a different node), append it before computing label and suffix. Otherwise cefr_level is wrongly 义教 instead of 必修/选必.

3) After re-extract + reload, assert grammar_items COUNT=108 with depth distribution L1=3,L2=28,L3=71,L4=6, and that 三/10/(3) now has children 三/10/(3)/a (label 限制性定语从句, cefr 必修) and 三/10/(3)/b (label 非限制性定语从句, cefr 选必). Add this count/expected-id assertion to scripts/data_accuracy_check.py so the regression is caught by stop_gate.

**对抗复核**: CONFIRMED true positive (BLOCK). Empirically verified end-to-end against the real PDF and DB.

EVIDENCE:
1) PDF source (data/curriculum/national/.../4.普通高中英语课程标准（2017年版2020年修订）.pdf, page idx 190 = 1-based 191) literally contains two structural rows under `（3）定语从句`:
   - 'a. 由关系代词 that、which、who、whom、whose 和关系' + continuation '副词 when、where、why 引导的限制性定语从句 *'
   - 'b. 由关系代词 which、who、whom、whose 和关系副

## 5. [BLOCK] (课标语法完整性) D0 门硬编码 n_g==106 把缺失封成绿门 (坑1 绿门假绿)

**detail**: scripts/data_accuracy_check.py:68 `check('grammar_items 行 == 106', n_g == 106)` 把 buggy 数 106 当成真值锁死。后果: (a) 原始 2 项丢失因门是照已坏输出写的, 永远静默通过; (b) 一旦把抽取修成正确的 108, 该门反而 FAIL 阻断。这正是项目坑1『绿门断言 buggy 快照』的教科书案例——门没断言『对照 PDF 真值』, 只断言『等于上次的数』。

**fix**: Three-part fix (单一计算点 + 已落库 + gate 断言), in order:

(1) FIX THE EXTRACTOR (root cause — scripts/lib/curriculum_grammar.py _skip_line, lines 29-38): the ascii-ratio heuristic `ratio > 0.4` wrongly drops structural marker lines whose content is English relation words. Before applying the ratio test, exempt lines that match a structural marker regex. Concretely, in _skip_line (or in the loop at extract_grammar_items:96-99), test `RE_L4`/`RE_L1`/`RE_L2`/`RE_L3` FIRST — if a line starts with `a.`/`b.`/`(n)`/`一、`/`1.` marker, it is a grammar item, never an example sentence, so skip the ascii-ratio gate. Minimal change: in _skip_line, return False early if `RE_L4.match(line) or RE_L3.match(line) or RE_L2.match(line) or RE_L1.match(line)`. Note the wrapped continuation line ("副词 when..." / "when 和 where...") is correctly skipped — only the a./b. header lines carry the label, which is the standard behavior here.

(2) RE-EXTRACT + REBUILD: re-run the curriculum grammar extraction to regenerate data/structured/curriculum/grammar_items.jsonl (should become 108 rows, depth4=6), then rebuild the DB (init_db / orchestrator load) so grammar_items table = 108. New items: grammar_item_id 三/10/(3)/a (限制性定语从句, cefr_level 必修 from single *) and 三/10/(3)/b (非限制性定语从句, cefr_level 选必 from **), parent_id=三/10/(3).

(3) FIX THE GATE + ADD TRUTH ANCHORS (scripts/data_accuracy_check.py:68): change `n_g == 106` to `n_g == 108`, AND add regression-proof truth-anchored assertions so the gate verifies PDF structure, not a magic number:
   - depth4 count == 6: `check("grammar depth4 == 6 (4疑问句+2定语从句)", con.execute("SELECT COUNT(*) FROM grammar_items WHERE depth=4").fetchone()[0] == 6)`
   - 定语从句 a/b present: `check("三/10/(3) 定语从句 a/b 完整", con.execute("SELECT COUNT(*) FROM grammar_items WHERE parent_id='三/10/(3)'").fetchone()[0] == 2)`
   - depth distribution lock: assert {1:3, 2:28, 3:71, 4:6}.

(4) ADD A MOTH/AUDIT ASSERTION 'grammar-items-match-pdf-108' that re-counts structural markers directly from the curriculum PDF (附录3, pages 187-191) and asserts it equals the DB row count — so the gate is anchored to PDF truth, not a frozen integer, preventing any future buggy-snapshot regression.

**对抗复核**: REAL BLOCK — verified by exhaustive PDF parse, not a false positive.

EVIDENCE (all reproduced with python3 on repo):
1. Gate literal confirmed: scripts/data_accuracy_check.py:68 = `check("grammar_items 行 == 106", n_g == 106, f"{n_g}")`. Live DB grammar_items = 106; data/structured/curriculum/grammar_items.jsonl = 106 rows; depth dist {1:3, 2:28, 3:71, 4:4}.

2. PDF GROUND TRUTH = 108 (not 106). S

## 6. [WARN] (课标语法完整性) 定语从句缺子项导致 grammar_occurrences 无法区分限制性/非限制性(下游精度损失)

**detail**: grammar_occurrences 第 4 行 renjiao/xuanze_1 主题=『Non-Restrictive Relative Clauses 非限制性定语从句』, 第 2 行 renjiao/bixiu_1 unit4 涉限制性定语从句, 但因 grammar_items 缺 a/b 子项, 两者只能都挂到粗父项 三/10/(3), 丢失教材实际分开教的限制性(必修)vs非限制性(选必)进度区分。属上一条缺失的下游放大, 修了父项缺失后可让 grammar_topic_map 指向更细的 三/10/(3)/a、/b。

**fix**: Two-layer fix (truth-source-first, per §3.5 数据化):

1. PARENT FIX (mandatory — root cause): Patch scripts/lib/curriculum_grammar.py so the a./b. 定语从句 lines are not dropped. Two sub-problems: (a) the `_skip_line` ratio>0.4 gate must not discard lines that match RE_L4 (`^[a-z]\. ...`) — apply the example-sentence ratio filter only to non-structural lines, OR raise/special-case the threshold for L4 enumeration lines; (b) handle the label+CEFR-marker line-wrap so the trailing */** (→必修/选必) is captured for these wrapped a./b. items. After re-extract, grammar_items should yield 108 rows with new nodes:
   • 三/10/(3)/a label='限制性定语从句' cefr_level='必修' parent='三/10/(3)'
   • 三/10/(3)/b label='非限制性定语从句' cefr_level='选必' parent='三/10/(3)'
   Then UPDATE data_accuracy_check.py:68 from `== 106` to `== 108` (and re-baseline against the PDF, not the old output).

2. DOWNSTREAM FIX (the finding's own suggestion — apply after parent fix): in backend/config/grammar_topic_map.yaml, split the single 定语从句 rule (currently both 'attributive clause'/'relative clause'/'定语从句' → 三/10/(3)) into ordered, specific-first rules:
   • patterns ['non-restrictive', 'non-restrictive relative', '非限制性定语从句'] → 三/10/(3)/b
   • patterns ['restrictive', 'attributive clause', 'relative clause', '定语从句'] → 三/10/(3)/a
   This re-maps renjiao/xuanze_1 unit5 (非限制性) to /b (选必) and renjiao/bixiu_1 unit4 (restrictive) to /a (必修), restoring per-unit progression precision. Keep specific 'non-restrictive' pattern BEFORE the generic relative-clause pattern (the YAML already documents first-match ordering).

Order matters: do parent fix first (so /a /b exist as valid FK targets), then the topic-map split, then re-run init_db + data_accuracy_check.py (must show 0 errors and 108 rows) per CLAUDE.md D0 procedure.

**对抗复核**: CONFIRMED with hard source evidence — the finding's premise is correct, and the root cause is a real D0 data-completeness defect (not a false positive).

TRUTH-SOURCE PROOF: The official curriculum PDF `4.普通高中英语课程标准（2017年版2020年修订）.pdf` (page 191, grammar appendix) literally subdivides （3）定语从句 into two asterisk-marked sub-items at DIFFERENT CEFR stages:
  • a. ...限制性定语从句 *  → 必修 (restrictive)
  • b

## 7. [BLOCK] (真题与section完整性) section_text 28 行 raw_text 在 20000 字符处静默硬截断, 但 n_chars 存真实长度 (最多丢 53548 字)

**detail**: backend/services/extraction/section_text.py:53 `INSERT ... [..., text[:20000], len(text)]` — raw_text 截到 20000 但 n_chars 记 len(text) 真值。28/221 行 raw_text=20000 且 n_chars>20000, 最大 renjiao/xuanze_3 U1 seq3 n_chars=73548 (丢 53548 字), waiyan/bixiu_2 U6 n_chars=66179。截断点在词中间 (尾='...complete the parag'[raph])。这与 p182 同类: 数据'看着完整'(有行), 实则正文丢一大半。raw_text 被 vocab/coverage/grammar/cloze 多个 service 消费 (exercise/cloze.py, grammar_fill.py, audit/coverage.py), 截断=单元课文词汇静默缺失。注: n_chars 字段诚实 (存真值), 所以 `n_chars<>LENGTH(raw_text)` 一条 SQL 即可自检 — 但目前无 gate 断言此项。

**fix**: 1. In backend/services/extraction/section_text.py:53, remove the `[:20000]` hard truncation so raw_text stores the full text consistent with n_chars:
   change `[ver, vol, un, seq, text[:20000], len(text)]` → `[ver, vol, un, seq, text, len(text)]`
   (DuckDB VARCHAR is unbounded, so no schema change needed. If a per-section cap is ever truly wanted, it must be a structural boundary, not an arbitrary mid-word char count, and n_chars must equal the stored length.)
2. Re-run the section_text extraction (DELETE+re-INSERT path already in extract_section_text) to repopulate full text for the 28 affected rows, then re-run any downstream cloze/grammar/phrase/scenario extraction that consumed the truncated text.
3. Add a data_accuracy_check.py assertion that locks the invariant: `SELECT COUNT(*) FROM section_text WHERE n_chars <> LENGTH(raw_text)` must equal 0 (fail/exit non-zero otherwise) so any future silent truncation is caught by the D0 gate.

**对抗复核**: Empirically verified all claims against code and the live DB (data/db/gaozhong.duckdb).

CODE (backend/services/extraction/section_text.py:51-54): INSERT stores `text[:20000]` for raw_text but `len(text)` for n_chars — a hard 20000-char truncation while recording the true (untruncated) length. Confirmed verbatim.

DATA: `SELECT COUNT(*) FROM section_text WHERE n_chars <> LENGTH(raw_text)` = 28 (of

## 8. [BLOCK] (真题与section完整性) EOL 真题 raw_question 在 900 字符处静默硬截断 (11 行) + 13 行空白 — 辽宁 2021/2022 阅读/完形/七选五正文丢约一半词

**detail**: backend/services/extraction/exam_eol_parse.py:40 `compact(text, limit=900)` 做 `[:900]` 硬截, 被 snippet_for_number (reading 逐题片段, exam_eol_parse.py:140) + _writing_row (exam_eol.py:183) 调用。11 行 raw_question 恰好 len=900, 尾部全部截在词/句中间 (Q23 尾='...we had', Q27 尾='past twel'[ve], Q20 听力='...his place tomorrow m'[orning])。源文件 (data/external/exam_sources/eol/2021_xgkii_english_eol.txt 全文存在, 20472 字) 里真正 item ≈2000 字, 唯一词从存储 124 个降到全文约 211 个 — 每篇阅读丢约一半 unique words。另有 13 行 raw_question 完全空 (eol/2021&2022 完形/七选五 子题, snippet 抽取没命中 marker 返回 '')。这些辽宁 EOL 行 (188 辽宁中 110 来自 EOL) 喂 trend/raw.py + trend/model.py + audit/exam_coverage.py + build_vocab_classification.py — 直接污染项目核心的辽宁考点/词汇/趋势分析。

**fix**: Two distinct defects, fix both:

A) The 900 hard cap (11 rows). In backend/services/extraction/exam_eol.py, stop char-capping reading/cloze spans. The span is already correctly bounded by the next-question marker in snippet_for_number (exam_eol_parse.py:128-140) — it only over-truncates because compact() reapplies a 900 limit at the end. Either: (i) raise/remove the limit on the final return of snippet_for_number and on _writing_row's compact(stem,900) so the full marker-to-marker span is preserved (downstream eol_import.py:65 already caps at 8000, ample for a ~2000-char passage); or (ii) keep a separate short stem_preview for UI but store the full source_span as raw_question. Preserve the marker-boundary logic (like 坑18 双向收口) — do NOT introduce a new char cap below the longest real item (~1963 chars).

B) The 13 empty stems. Fix the cloze/seven-choose-five marker matching in marker_patterns() (exam_eol_parse.py:88-112, 'cloze'/'undotted'/'blank' styles) so per-blank sub-items resolve a span; OR, if these sub-items genuinely have no independent stem (cloze blanks share one passage), honestly set them to the shared passage text or an explicit '子题无独立题面' sentinel rather than ''. Either way they must not silently become empty raw_question.

C) Add a D0 assertion in scripts/data_accuracy_check.py: no EOL raw_question row has LENGTH exactly equal to the cap (== 900 is a smoking gun for a hard slice), and EOL reading/cloze rows are non-empty. Then re-run the EOL import (build_draft → eol_import) so the DB is rebuilt with full spans, and re-run build_vocab_classification.py since ln_v changes.

**对抗复核**: CONFIRMED — real BLOCK-level data loss, every claim verified empirically against code + DB + source.

1) Hard truncation site is real: backend/services/extraction/exam_eol_parse.py:40 `compact(text, limit=900)` does `[:limit]` with default limit=900, called by snippet_for_number (:140, reading items) and _writing_row (exam_eol.py:183). No boundary-aware logic — pure char slice.

2) DB counts match

## 9. [WARN] (真题与section完整性) 8 个 section 的 page_end 边界算错 (span 27-48 页), 单 section 吞下整单元/后续单元正文 → 既污染又触发 20000 截断

**detail**: sections 表 8 行 (page_end-page_start)>25。如 waiyan/bixiu_2 U6 seq1 'Writing' 标 page 78-126 (48 页), 但同卷其它 Writing section 都只 1-2 页 (18-19/42-43/54-55); 下一 section (U6 seq2 Vocabulary) 从 127 起 → 说明该 'Writing' 的 page_end=126 是错的, 它把 U6 整单元的 Reading/Grammar 甚至 workbook/Vocabulary 全吞进一个 section (raw_text 含 'Vocabulary' 标记)。renjiao/xuanze_3 U1 seq3 'Review' 标 29-68 (39 页) 同理。后果双重: (a) 这些 section 的 raw_text 混入非本 section/非本单元内容, 给单元词汇/coverage 引入跨单元污染; (b) 正是这种 40+ 页吞并使 n_chars 冲到 73548 触发上一条的 20000 截断。这是 section 提取的 page_end 收口 bug, 不是 pypdf 丢页 (页数对得上)。注: 多数'1-2 section/单元'是坑22 整页兜底的已知行为, 不在此列; 此条只针对 span>25 的过宽边界。

**fix**: Fix the UNIT boundary detection, not section.py (the finding's target is a no-op).

Root cause: backend/services/extraction/textbook.py — the textbook PDFs are laid out as [main-text units 1..N][workbook (repeats 'UNIT N' headers)][whole-book glossary]. `_from_regex` dedups same-N to min page (correctly keeping main-text start), but line 146 sets the LAST unit's end_page to n_pages (volume tail), so the last front-matter unit (typically U6, or U1 in the inverted renjiao/xuanze_3 layout) absorbs all workbook + glossary pages, which have no 'UNIT N+1' anchor to cap them. section.py faithfully clips sections to that over-wide unit range, so the final section inherits 39-48 pages of back-matter.

Correct fix options (in textbook.py / unit_overrides.json):
1. Detect the back-matter boundary: cap the last main-text unit's end_page at the first page where a 'WORKBOOK'/'Communication bank'/'Words and expressions'/'Vocabulary'(glossary)/'New Standard' back-matter anchor appears (these are visible in PDF headers, e.g. waiyan/bixiu_2 p69 'WORKBOOK', p91 'Communication bank', p120 'Words and expressions'). Stop main-text units at the start of the workbook block.
2. OR add manual page_start/page_end entries to data/structured/textbook/unit_overrides.json for the 8 affected volumes (overrides already take precedence at textbook.py:137), human-verified against the PDF, so the last unit ends at the true main-text end (e.g. waiyan/bixiu_2 U6 ends ~p77 not p139).

Then re-run extraction (init_db Layer for units -> section_text) and follow 坑22 discipline: dry-compare per-unit old/new section byte counts (working units regression=0; only the 8 over-wide units shrink) before落库. Add a D0 gate assertion in scripts/data_accuracy_check.py (+ a moth assertion) locking 'no section span > 25 pages' (or 'no unit span anomalously > 2x volume median') so this can't regress. Do NOT touch section.py:159 page_end logic — it is already correct (page_end == next_section_start-1).

**对抗复核**: REAL problem, but the finding's mechanism + proposed fix are WRONG. Confirmed by empirical run against data/db/gaozhong.duckdb + PDFs:

(1) SYMPTOM REAL: SQL `WHERE (page_end-page_start)>25` returns exactly 8 sections as stated (spans 48/48/42/40/39/39/31/27). Their section_text n_chars are 55k-73k vs normal Writing/peer sections 3-5k.

(2) POLLUTION REAL: waiyan/bixiu_2 U6 seq1 'Writing' (p78-126

## 10. [BLOCK] (图谱完整性) 停用词 no/on/off 被 YAML 静默 coerce 成 bool → 335 tests_word 污染边 + 35 question_tags 逃过坑5清洗

**detail**: backend/config/stopwords.yaml 里裸写的 `- no` `- on` `- off` `- yes` 被 yaml.safe_load 解析成 Python bool (False/True), backend/services/stopwords.py:load_stopwords() 的 `{str(w).lower() ...}` 把它们变成 'false'/'true' 存入停用词集——literal 词 no/on/off/yes 根本没进集合, 永远不被过滤。结果 build_tests_word 给这些功能词建了 tests_word 边: word:on=220, word:no=79, word:off=36, 共 335 条 (占 tests_word 17377 的 1.93%)，并写进 question_tags 35 行 (on=25,no=7,off=3)。这正是坑5(L-U)要根除的功能词污染('学生弱在 they'/考点边稀释), 只是换了一批词从 YAML-bool 后门漏进来。当前 student_weakness 未命中(demo 数据少), 但任何 weakness recompute 会渲染'学生弱在 on/no/off'。判 BLOCK 因 D0=任意关联性100%准 + 直接污染考点图谱与学情派生根。

**fix**: (1) Quote the YAML-bool-risk words in backend/config/stopwords.yaml: change `- no`→`- 'no'`, `- on`→`- 'on'`, `- off`→`- 'off'`, `- yes`→`- 'yes'` (all 5 bare occurrences incl. the duplicate `- no` at line 181). Verified: this drops bool entries to 0 and admits all four as literals into the stopword set. (Alternative: make load_stopwords() reverse-map bool→literal, but quoting is simpler and is the single source of truth per §3.5 data-as-config.) (2) Single-calculation-point rebuild, not data-only DELETE: rerun build_tests_word (backend/services/links_extra.py:65) + question_bank._autotag (loader.py:76) to re-derive and clear the 335 edges + 35 tags; a bare DELETE will regress on next init_db. (3) Close the gate blindspot: change moth no-stopword-tags assertion from the 8 hardcoded-word query to assert question_tags tag_id ∩ ALL stopwords.yaml literals = 0 (invariant, not sample); add the symmetric tests_word edge assertion; add a D0 dimension in data_accuracy_check.py asserting tests_word/question_tags contain no stopword (currently zero D0 coverage — violates CLAUDE.md "new data must add data_accuracy_check item"). Adversarial verify: inject one stopword edge → both gates must FAIL; rebuild → green.

**对抗复核**: All empirical claims verified with hard evidence via python3/duckdb. (1) Root cause confirmed: backend/config/stopwords.yaml has bare unquoted tokens `- no` (lines 26,181), `- on` (111), `- off` (122), `- yes` (182); yaml.safe_load coerces them to Python bool (5 entries at idx 15/97/108/165/166 are False/True). backend/services/stopwords.py:21 does {str(w).lower() for w in ...} → stores 'false'/'t

## 11. [WARN] (图谱完整性) 课标词 kilogram 在 cefr_vocab(3041) 但无 word 节点 — cefr 补抽后图层未重建的陈旧快照 (p182 同类)

**detail**: cefr_vocab 有 kilogram (义教, source 标 '4.普通高中英语课程标准...pdf [补抽]'，正是 p182 那次 pdfplumber 补抽进来的), 但 nodes 表无 word:kilogram 节点。word 节点义教 1571 vs cefr_vocab 义教 1572, 差的正好是这 1 个。根因与触发背景的 p182 完全同类: cefr_vocab 被'修'到 3041, 但图谱节点层是更早构建的陈旧快照, 补抽的词没传导到节点。影响: 任何按 word 节点枚举'课标词'的图查询(覆盖率/越纲率/学情)会漏 kilogram。kilogram 不在 unit_vocab_intro(教材不教)且无真题考它, 故无 introduces_word/tests_word 边缺失, blast-radius 有限→WARN 非 BLOCK。但它是 100% 准约束下的真实完整性缺口。

**fix**: Two coupled fixes: (A) Rebuild the canonical word-node layer so nodes are a derivation of cefr_vocab, not an independently-maintained stale snapshot. Re-run the node builder from cefr_vocab to emit the missing word:kilogram node (concept_id='word:kilogram', node_type='word', label='kilogram', attrs_json cefr_level='义教', with appropriate exam_status/teaching_hint as for other 义教-only-no-exam words). This restores word-node 义教 from 1571 to 1572 and makes the full-set invariant hold (0 missing). (B) Fix the D0 check_12 blind spot in /Users/dp/Documents/M/gaozhong/scripts/data_accuracy_check.py (_check_12_cefr_node_xref, lines 147-155): replace the sampling 'SELECT word FROM cefr_vocab ORDER BY word LIMIT 100' loop with a full-set invariant assertion — e.g. miss = con.execute(\"SELECT count(*) FROM cefr_vocab c WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id='word:'||c.word)\").fetchone()[0]; check('cefr_vocab 全量每词有 word 节点', miss==0, f'missing={miss}'). This queries the whole-set invariant instead of an alphabetical-prefix sample so future stale-snapshot gaps anywhere in the alphabet are caught. After rebuild, re-run python3 scripts/data_accuracy_check.py to confirm 0 errors before stop (per CLAUDE.md D0 gate).

**对抗复核**: Every claim verified with hard evidence against data/db/gaozhong.duckdb (read-only python3 duckdb). (1) nodes WHERE concept_id='word:kilogram' = 0 — node truly absent. (2) cefr_vocab has kilogram, level 义教, source exactly '4.普通高中英语课程标准（2017年版2020年修订）.pdf [补抽]' — the p182 pdfplumber 补抽 source, confirming root cause. (3) Full-set NOT EXISTS invariant: exactly 1 cefr_vocab word lacks a node, and it i

## 12. [BLOCK] (跨源一致性与陈旧) 超纲词"是否考过"被 3 处各算一遍且互相矛盾 (Rule1 单一计算点违反)

**detail**: 同一事实(教材超纲词是否在真题考过)由三个独立函数用不同算法各算一遍, 结果不一致: vocab_classification.jsonl(build_vocab_classification.py)=304 考过, exam_coverage.py=306 HV_extra, extracurricular.py=305 HV_all。差异根因: (a) build 脚本用 re.findall([A-Za-z]+) 子串 + WordNet 词形归并; exam_coverage 用 re.compile([A-Za-z][A-Za-z'-]{1,}) 精确匹配 + 无归并; extracurricular 用 _tokenize 子串。(b) build/extracurricular 只看 raw_question, exam_coverage 看 raw_question+analysis。在 381 个两源都有判定的超纲词中, 152 个 jsonl 与 node exam_status 直接矛盾。这个矛盾直接喂给教师端: jsonl 词卡说"辽宁考过·必教", 同一词热力图/exam_status 标 LV_extra"选学降权"。

**fix**: Build one single computation point in the services layer — a function word→(exam_status, gaokao_hit_count_ln, gaokao_hit_count_all) using ONE agreed tokenizer (decide explicitly: WordNet lemmatization yes/no, and whether the field scope is raw_question only or raw_question+analysis — recommend lemmatization ON since inflected forms like Battlefields are the same vocabulary item, and raw_question+analysis is debatable since analysis text is teacher commentary not the exam passage). Have all three consumers (vocab_classification.jsonl producer, exam_coverage node writer, extracurricular node writer) read this single authoritative product instead of each recomputing. Also fix the node-attrs clobber: merge attrs_json instead of full-overwrite, or consolidate exam_status + teaching_priority + gaokao_hit_count into one writer. Add a D0 assertion lock in scripts/data_accuracy_check.py asserting the three sources agree on |supra ∩ tested| (single number); adversarially pollute one source to confirm it FAILs, then heal to confirm green.

**对抗复核**: CONFIRMED — real BLOCK bug, every claimed number reproduced exactly against the live DB (data/db/gaozhong.duckdb) and artifact. Three independent functions compute the same fact (textbook supra-syllabus word tested in past exams) with three different algorithms and three different answers: scripts/build_vocab_classification.py (WordNet lemmatize + re.findall([A-Za-z]+), raw_question only) yields 3

## 13. [BLOCK] (跨源一致性与陈旧) node.exam_status 完全 province-blind, 把外省真题当辽宁印证 (违反 §7 + 坑12)

**detail**: backend/services/audit/exam_coverage.py:21 的 _tokenize_exam 对全部 472 题(含 284 非辽宁: 全国I/II/III/甲/乙卷)无差别 tokenize, 据此算 core/HV_extra/LV_extra 写进 nodes.attrs_json.exam_status, 再被 heatmap.vocab(用户热力图)/lesson_plan/exercise/poc 消费。结果: 教师看到 306 个 HV_extra(超纲但考过·必教★), 但其中 153 个辽宁从未考过、只在外省考过; 2384 个 core(课标+高考双印证·必背)中 622 个只靠非辽宁真题命中。这正是 CLAUDE.md §7 辽宁卷锚定硬约束 + 坑12 分析诚实门(province-scoped)明令禁止的'拿全国卷当辽宁卷分析'。

**fix**: Make exam_coverage province-scoped, the same way extracurricular.py already is.

1. backend/services/audit/exam_coverage.py `_tokenize_exam`: add province filter using exact prefix to avoid the 否定词子串 trap (坑7):
   `SELECT raw_question, analysis FROM exam_questions WHERE province LIKE '辽宁%'`
   This alone drops HV_extra 306→153 and core 2384→1762, aligning the user-facing heatmap with辽宁 reality.

2. Preferred (preserves both signals): compute TWO token bags — exam_ln (province LIKE '辽宁%') and exam_all — and write both classifications, e.g. attrs_json.exam_status_ln (default for teacher display) + exam_status_all (reference). Redefine/rename 'core' → '辽宁双印证'. Update heatmap/vocab.py + lesson_plan.py to read the _ln variant by default.

3. Fix the write-order / overwrite: either merge extracurricular + exam_coverage into one writer (Rule 1 单一计算点 — currently two audits write nodes.attrs_json for the same word, second clobbers first), or have exam_coverage preserve extracurricular's gaokao_hit_count_ln/all fields instead of replacing the whole attrs_json blob. Right now 4260 exam_status writes erase 100% of the province-aware gaokao_hit_count_ln data.

4. Add a D0 assertion in scripts/data_accuracy_check.py: the exam token set feeding exam_status MUST be province-scoped (province LIKE '辽宁%'), and assert no live word node simultaneously claims HV_extra while its辽宁 hit count is 0. Document in docs/data_accuracy_audit.md per CLAUDE.md D0 protocol.

**对抗复核**: CONFIRMED — real BLOCK. Every claimed number reproduces against the live DB (data/db/gaozhong.duckdb), and the §7 辽宁卷锚定 硬约束 + 坑12 (province-scoped 诚实门) are violated end-to-end.

EVIDENCE (all empirically reproduced, not from the report):
1. exam_questions has 472 rows; only 188 are province LIKE '辽宁%' (140 辽宁2021+ + 48 辽宁2015-2020). The other 284 are 全国I/II/III/甲/乙 + 未知 — explicitly tagged '(非辽宁)'

## 14. [WARN] (跨源一致性与陈旧) extracurricular 的 province-aware 写入被 exam_coverage 整体覆盖, 且 finding 假称'已写入'

**detail**: run_all 顺序(audit/__init__.py:39-40): extracurricular 先跑、exam_coverage 后跑。extracurricular._write_priority_attrs 给超纲词写 {teaching_priority, gaokao_hit_count_all, gaokao_hit_count_ln, extracurricular} 整段覆盖 attrs_json; 紧接着 exam_coverage._write_status 又整段覆盖成 {cefr_level, exam_status, teaching_hint}。后者把前者全部抹掉, 包括全管线唯一的 province-aware 信号 gaokao_hit_count_ln。DB 实测: 0 个 word 节点留存 teaching_priority 或 gaokao_hit_count_ln, 全部只剩 exam_status。但 extracurricular 写的 audit finding 仍声称 'HV_all 已写入 nodes.attrs_json.teaching_priority=HV_extra (D0 100% — 非 bug)' — 这是 fresh 审计里的假声称(写了但被覆盖, 消费者读不到)。

**fix**: Two functions write the same field nodes.attrs_json with whole-column UPDATEs (last-writer-wins). Pick one:
(A) Single computation point (preferred per Rule 1): merge the 4-quadrant classification AND the extracurricular priority/province counts into one writer that emits the complete attrs_json once (e.g. fold gaokao_hit_count_all/gaokao_hit_count_ln/teaching_priority into exam_coverage._attrs_for, or have extracurricular feed exam_coverage). Then the surviving record carries all keys.
(B) Merge-write instead of overwrite: change both _write_priority_attrs and _write_status to read existing attrs_json, json.loads, update only their keys, json.dumps back — never replace the whole blob. Then reorder so exam_coverage runs first (or order-independent since merge is commutative on disjoint keys).
Also: fix/remove the extracurricular.py:90-92 finding note that falsely claims '已写入 ... teaching_priority' — only valid once (A) or (B) guarantees the keys survive. Re-run scripts/data_accuracy_check.py to confirm gaokao_hit_count_ln > 0 persists for the 305 words.

**对抗复核**: REAL PROBLEM — confirmed by code reading + isolated replay on a temp DB copy, numbers match the finding exactly.

STRUCTURAL PROOF (code):
- AUDIT_FNS order in backend/services/audit/__init__.py:39-40 is extracurricular.audit_extracurricular_in_exam (idx 39) THEN exam_coverage.audit_vocab_4q_classification (idx 40). run_all iterates this list in order (line 66).
- extracurricular._write_priority_a


---

## 修复状态日志 (2026-06-17, 提交前对抗复核 + 三门验证)

> 提交前对待修 diff 派两 agent 对抗审查(extraction 回归 + web 第二源核验), 挖出审计当时未见的新根因, 已一并修。三门全绿(D0 exit0 / moth PASS 39/0 / stop_gate exit0)后落地。

### ✅ 已修 (单一计算点 + 已落库 + gate 断言三件套)
- **#1/#2 renjiao 词表** — **架构级重写**(非补丁): `vocab_renjiao.py` 改为只读「各单元生词 / Words and Expressions in Each Unit」**单一区段**, 'Unit N' 头锚单元, 块解析续行。bixiu_2 U1 56→66(补回 document/paraphrase/donate/historic/quality/tradition/worthwhile/forgive/creative/creatively, web 第二源 cpsenglish 核验 precision 100%/recall 82%→~97%)。
  - **⚠ 纠正本审计 #1/#2 原提议**: 原建议「broaden ENTRY_RE 认 PUA-IPA + 保留所有 entry≥8 页」**恰恰是新发现的 331 跨单元重复 bug 的根源**——人教书末有 ①各单元生词 ②字母序 Vocabulary 总表 多个词区段, 旧 `_page_to_unit_estimator` 把尾部总表页线性砸进 U5 → heritage 等 331 个 (vol,word) 同时落真单元+U5。正解是 **Rule1 单一计算点: 只读一个区段, 不合并**。U5 103→59 即去污指纹。
- **#3 per-volume 塌缩门** — 旧 (MIN<20 AND MAX>50) 只抓一种形态且对 331 重复(膨胀非塌缩)全盲。换 2 鲁棒断言: (a) 绝对地板 任一单元 ≥20 词; (b) **跨单元唯一性 全版本==0**(renjiao 331→0 + waiyan 96→0)。+ moth `unit-vocab-no-cross-unit-dup`。
- **#4/#5 grammar 定语从句** — `curriculum_grammar.py` `_skip_line and not RE_L4.match` 豁免; 106→108; D0 `n_g==108`。
- **#10 stopwords bool coerce** — `no/on/off/yes` 加引号; 0 bool 项。
- **cefr end_page off-by-one + 国家表 3-token 泄漏(新)** — `curriculum_vocab.py` end_page 182→184(补 w/x/y/z 真词) + `_COUNTRY_TABLE_RE` 行首锚截国家表(去 adjectives/korea/korean 误纳); 3055→3052。D0 `n_cefr==3052`。
- **waiyan xuanze unit6 污染 96 对(新发现)** — `vocab.py` 加 `_GLOSSARY_HEADING_RE` 哨兵: 遇字母序「Vocabulary」标题即终止段(根因: `_next_section_page` 只看页首行, xuanze 总表起页首行是页码 '113' → 段末漏判 → 字母表全挂 last UNIT 6 下)。xuanze_1 U6 63→33; bixiu 各册 0 变化(未误伤)。
- **vocab_classification 重生成** — 1244→1277(抽取更全), 0 陈旧残留。

### ⏳ 待修 (本批未含, 下一轮)
- **#7 section_text 20000 硬截断** (28 行, n_chars 存真值, `n_chars<>LENGTH(raw_text)` 一句自检)
- **#8 EOL raw_question 900 硬截断** (11 行) + 13 空白 (draft/review overlay, 较复杂)
- **#9 section page_end 边界过宽** (8 section span>25 页, 根因在 textbook.py 末单元 end_page=n_pages 吞 workbook/glossary)
- **#12 超纲"是否考过" 3 处各算** (Rule1 违反, build/exam_coverage/extracurricular 不同 tokenizer)
- **#13 node.exam_status province-blind** (§7 违反, exam_coverage 未 province 过滤)
- **#14 extracurricular province-aware 写入被 exam_coverage 覆盖**
