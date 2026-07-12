#!/usr/bin/env python3
"""Generate Phase D course_content for all syllabus lessons missing content.

Each artifact must pass course_content_review_gate (lexicon / 10-gram / exam_point / political).
Does not invent exam answers; exam_grounded = theme_l2 focus + evidence years from syllabus.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.course.content import CONTENT_DIR, reload
from backend.services.course.lexicon_filter import allowed_words_for, expand_morphology
from backend.services.course.scenarios import _tokens, has_political_word, has_textbook_copy
from backend.services.course.syllabus import syllabus

# 每主题 ≥8 段可背诵英文 (生活与学习需 8); 词尽量落 G_FINAL; 人工起草非押题
_BANKS: dict[str, list[tuple[str, str]]] = {
    "生活与学习": [
        (
            "Many students feel busy after school. They have homework, clubs, and family time. "
            "A good plan helps: finish hard tasks first, then rest. Ask teachers when you do not understand. "
            "Reading every day builds vocabulary. Small steps, kept for weeks, often work better than one long night. "
            "When exams come, review what you got wrong — those gaps are your next lessons.",
            "放学后很多同学觉得忙：作业、社团、家庭时间挤在一起。好计划先啃难的，再休息；不懂就问老师。"
            "每天读一点能长词量。坚持几周的小步子，往往比熬一个通宵更管用。考试来了，先复盘错题——那些缺口就是下一节要攻的。",
        ),
        (
            "School life is more than grades. Classmates can become study partners: explain a hard point to a friend, "
            "and you remember it better. Keep a short list of new words from each reading. "
            "Sleep well before a test; a clear mind beats last-minute fear. "
            "Parents may push hard — tell them your plan so they can help, not only worry.",
            "学校生活不只是分数。同学可以成为学习搭档：把难点讲给朋友听，自己记得更牢。"
            "每次阅读后留一小张生词清单。考试前睡好；清醒的头脑胜过临时慌张。"
            "家长也许很急——把计划告诉他们，让他们帮得上忙，而不只是担心。",
        ),
        (
            "Morning time is quiet and useful. Ten minutes of review before class can save an hour at night. "
            "Carry a small notebook for mistakes you keep making. "
            "If a passage feels long, mark the topic sentence of each paragraph first. "
            "Learning is a habit: same place, same time, small goal — then stop and rest.",
            "清晨安静又好用。课前十分钟复习，晚上能省下一小时。"
            "随身带小本，记下反复犯的错。篇章太长时，先标出每段主题句。"
            "学习是习惯：同一地点、同一时间、小目标——然后停下来休息。",
        ),
        (
            "Online tools can help, but they are not the lesson. Read the question twice before you search. "
            "Write your own answer in simple English, then check. "
            "Copying full essays teaches little. Build sentences with words you already know. "
            "After practice, close the screen and say the key points out loud.",
            "线上工具能帮你，但它们不是课本身。先把题读两遍再去搜。"
            "用简单英语写出自己的答案，再核对。整篇照抄作文学不到多少。"
            "用已知的词造句。练完后关掉屏幕，把要点大声说出来。",
        ),
        (
            "Group work works when roles are clear: one keeps time, one writes notes, one checks facts. Listen before you speak. Disagree with ideas, not with people. Share sources so everyone can check them. End with three takeaways the group agrees on — that is real learning together.",
            "小组学习要角色清楚：一人计时、一人记笔记、一人核对事实。先听再说。反驳观点，不攻击人。分享来源，人人可核对。结束时写出三组共同认可的收获——那才是一起学会的东西。"
        ),
        (
            "Exam weeks feel heavy. Break big goals into daily pieces: words, one passage, one writing outline. "
            "Celebrate small wins so you do not burn out. "
            "If anxiety rises, breathe slowly and return to the next small task. "
            "Remember: the paper tests skills you have practiced, not magic.",
            "考试周很沉。把大目标拆成每天几块：词、一篇阅读、一份写作提纲。"
            "庆祝小进步，避免燃尽。焦虑上来时，慢慢呼吸，回到下一个小任务。"
            "记住：试卷测的是你练过的技能，不是魔法。",
        ),
        (
            "Teachers give feedback for a reason. Read every comment and fix one type of error each week. "
            "Keep old papers in a folder ordered by date. "
            "Compare your first draft with the final one — growth becomes visible. "
            "Ask one clear question in the next class instead of saying you understand when you do not.",
            "老师的反馈有原因。逐条读评语，每周只改一类错。"
            "旧卷按日期放进文件夹。对比初稿与终稿——进步会看得见。"
            "下节课问一个清楚的问题，不要懂装懂。",
        ),
        (
            "Holidays are not only rest. Light reading keeps English warm: news for teens, short stories, song lines. "
            "Write five sentences about your day without a dictionary first. "
            "Then look up only the words you truly need. "
            "Come back to school ready, not empty.",
            "假期不只是休息。轻量阅读能保温英语：青少年新闻、短故事、歌词。"
            "先不查词典写五句今天的事，再只查真正需要的词。"
            "返校时带着准备，而不是空着手。",
        ),
    ],
    "做人与做事": [
        (
            "Character shows in small choices: return a lost wallet, keep a promise, admit a mistake. "
            "Hard work beats empty talk. When you fail, own it and try a better way. "
            "Respect grows when you listen and keep secrets that are not yours to share. "
            "Doing the right thing is a skill you can practice every day.",
            "品格显在小选择：归还钱包、守约、承认错误。实干胜过空谈。"
            "失败时认账，再换更好办法。倾听、不传不属于你的秘密，尊重才会长。"
            "做对的事是可以每天练习的技能。",
        ),
        (
            "Honesty in study means no cheating and no fake progress. "
            "If you did not prepare, say so and plan repair time. "
            "Help a classmate without doing the work for them. "
            "Courage is speaking up when something unfair happens in class.",
            "学习上的诚实：不作弊、不假装进步。没准备就直说，并安排补救时间。"
            "帮同学，但不要替他做完。课堂上不公时敢说出来，也是勇气。",
        ),
        (
            "Time management is part of responsibility. Put phone away when you promised to study. "
            "Finish what you start, even if the task feels boring. "
            "Lead by example in group projects: arrive on time, bring your part ready. "
            "People trust those who deliver.",
            "时间管理也是责任。答应学习时就把手机放下。哪怕无聊也要做完。"
            "小组作业以身作则：准时到、带好自己的部分。能交付的人更被信任。",
        ),
        (
            "Kindness is not weakness. Offer a seat, share notes, thank the cleaner. "
            "Stand with someone who is left out. "
            "Strong people lift others; they do not push them down. "
            "Your daily manners become your reputation.",
            "善良不是软弱。让座、分享笔记、感谢保洁。站到被冷落的人一边。"
            "强者托人向上，不把人按下去。日常礼貌会变成你的名声。",
        ),
        (
            "Goals need action plans. Write what you will do this week, not only what you hope. Check progress on Sunday night. Adjust without self-hate. Ask teachers for advice, then decide yourself. Standing on your own grows from many small responsible acts.",
            "目标需要行动计划。写下本周要做的，而不只是盼望。周日晚检查进度。调整，但不自我厌恶。向老师求建议，再自己决定。靠自己站稳，来自许多小小的负责行为。"
        ),
        (
            "Conflict happens. Stay calm, state facts, suggest a fair fix. "
            "Apologize when you hurt someone, even if you did not mean it. "
            "Forgive when others change. Holding anger forever costs you more. "
            "Peace is also something you build.",
            "冲突总会有。保持冷静，陈述事实，提出公平办法。"
            "伤到人就道歉，即使不是故意。对方改了就原谅。永远憋着怒气更伤自己。"
            "和平也是建出来的。",
        ),
        (
            "Public rules protect everyone: wait in line, clean up, follow lab safety. Breaking rules for fun can hurt others. If a rule seems wrong, discuss it with teachers instead of quiet fight-back. Being a good member of the school starts in the hallways.",
            "公共规则保护所有人：排队、清理、遵守实验安全。图好玩犯规可能伤人。觉得规则不对，就和老师讨论，而不是暗地对抗。做学校里的好成员，从走廊开始。"
        ),
    ],
    "社会服务与人际沟通": [
        (
            "Good communication starts with clear purpose: what do you need the other person to know? "
            "Use short sentences. Check that they understood. "
            "In messages, tone is easy to miss — be polite and specific. "
            "Listening is half of every talk.",
            "沟通先明确目的：你要对方知道什么？用短句。确认对方听懂了。"
            "消息里语气易被误读——礼貌且具体。倾听占谈话一半。",
        ),
        (
            "Volunteer work teaches care for others. Serve food, visit elders, clean a park — notice real needs. Ask before you help so your effort matches what people want. Team service needs planning and thanks. Small local acts matter more than big empty slogans.",
            "志愿活动教关心他人。送餐、探望老人、清理公园——看见真实需求。先问再帮，让努力对上对方想要的。团队服务要计划、要感谢。本地的小行动，胜过空洞大口号。"
        ),
        (
            "In debate, attack the claim with evidence, not the person. "
            "Summarize the other side fairly before you reply. "
            "Change your mind when facts change — that is strength. "
            "Classrooms become safer when disagreement stays respectful.",
            "辩论用证据打论点，不打人。先公正复述对方观点再回应。"
            "事实变了就改想法——那是力量。意见不合仍保持尊重，教室才更安全。",
        ),
        (
            "Talk across cultures needs patience. Slow down, avoid hard local phrases at first, confirm meanings. Share your festivals and ask about theirs. Funny stories can bridge gaps, but never at someone's identity. Wanting to learn beats quick judgment.",
            "跨文化交流要有耐心。先放慢、少用难懂的本地说法、确认含义。分享自己的节日，也问问对方的。有趣的故事能搭桥，但不要拿身份开玩笑。想学习胜过急着评判。"
        ),
        (
            "Online communities have rules too. Do not spread false stories. Cite sources. Protect privacy — yours and others'. If chat turns angry, pause before you type. Good online behavior is part of real life behavior.",
            "线上社区也有规矩。不传假消息，注明来源。保护隐私——自己的和别人的。聊天变怒时，先停再打字。线上好行为也是真实生活行为的一部分。"
        ),
        (
            "Service talk is a useful life skill: greet, state the problem, offer options, thank. Practice with role play in class. Calm words lower heat in hard talks with shops or offices. Clear speech saves time for everyone.",
            "服务话术也是生活技能：问候、说明问题、给出选项、感谢。课上用角色扮演练。冷静措辞能给商店或办公室里的难谈降温。清楚表达为人人省时间。"
        ),
        (
            "Family talks can be hard. Choose a quiet time. Use I-messages: I feel… when… I need… "
            "Avoid blame words. Agree on one next step together. "
            "Follow up later so trust grows. "
            "Home is also a place to practice respect.",
            "家庭谈话可能很难。选安静时候。用「我」句式：我感到…当…我需要…"
            "少指责。一起定下一步。之后跟进，信任才会长。家也是练习尊重的地方。",
        ),
    ],
    "文学、艺术与体育": [
        (
            "Stories train care for others: you live other lives for a few pages. Mark images and turning points, not only new words. After reading, tell the plot in five sentences. Art and literature both ask: what does this make you feel, and why?",
            "故事训练关心他人：几页纸里过别人的人生。标记意象与转折，而不只是生词。读完用五句话讲情节。文学与艺术都在问：它让你感到什么，为什么？"
        ),
        (
            "Music builds rhythm for language. Sing along quietly and notice stress patterns. Describe a painting with precise adjectives. Sport teaches tough spirit: train, fail, adjust, try again. Body and mind grow together when practice is regular.",
            "音乐给语言节奏。轻声跟唱，注意重音模式。用准确形容词描述一幅画。体育教韧劲：练、败、调、再试。规律练习时，身心一起成长。"
        ),
        (
            "Write a short poem with simple words and strong verbs. "
            "Read it aloud to hear the beat. "
            "Watch a play or match and note teamwork moments. "
            "Creative work is not talent only — it is hours of craft.",
            "用简单词和有力动词写一首短诗。朗读听节奏。"
            "看戏或比赛，记下团队合作瞬间。创作不只靠天赋——也靠长时间手艺。",
        ),
        (
            "Museums and stadiums are public classrooms. Read the labels. Ask guides questions. "
            "Compare two artworks or two athletes' styles. "
            "Bring a friend and teach each other one new fact. "
            "Culture grows when shared.",
            "博物馆与体育场是公共课堂。读说明牌，问讲解员。"
            "比较两件作品或两位运动员的风格。带朋友互相教一个新事实。"
            "文化因分享而生长。",
        ),
        (
            "Film scenes can teach narrative: setting, conflict, ending. Pause and predict what happens next. Discuss theme without ruining the ending for others. Then write your own ending in English — short and clear.",
            "电影场景能教叙事：背景、冲突、结局。暂停并预测下一步。讨论主题时别破坏别人对结局的期待。然后用英语写你自己的结局——短而清楚。"
        ),
    ],
    "科学与技术": [
        (
            "Science asks for evidence. Claim, support, limit — say what you do not know. Technology is a tool: phones help research, but they also steal focus. Set device rules during study blocks. Wanting to know plus care keeps new ideas safe.",
            "科学要证据。主张、支撑、边界——说出你不知道的。技术是工具：手机助检索，也偷专注。学习时段设设备规则。想弄清加上谨慎，新想法才安全。"
        ),
        (
            "Lab work needs method: question, plan, observe, record, conclude. Never fake data. Report errors honestly. Read graphs slowly — the lines and numbers matter. Share findings so others can test them.",
            "实验要方法：提问、计划、观察、记录、结论。绝不造假数据，诚实报错。慢慢读图——线条与数字很重要。分享发现，让别人能复验。"
        ),
        (
            "Smart tools can draft text, but you must check facts and voice. Never submit machine work as if it were only yours without review. Learn how to ask for sources and limits. Human judgment stays the final gate.",
            "智能工具能起草文字，但你必须核对事实与语气。未经审阅勿把机器产出当纯自己的作业提交。学着要求来源与边界。人类判断仍是最后一道门。"
        ),
        (
            "Everyday tools: search well with exact key words, save links, compare two sites. Watch out for hot claims without date or author. Update programs to stay safe. Understand basics of how your tools work — do not treat them as magic.",
            "日常工具：用精确关键词搜索、保存链接、对比两站。警惕无日期无作者的热门说法。更新程序保安全。弄懂工具基本原理——别当魔法。"
        ),
        (
            "Space, medicine, and clean energy show how science serves people. "
            "Read one short science news piece a week and summarize it. "
            "Note numbers and units carefully. "
            "Ask: who benefits, and what risks remain?",
            "航天、医学、清洁能源显示科学如何服务人。每周读一则短科学新闻并概括。"
            "仔细记下数字与单位。追问：谁受益，还剩什么风险？",
        ),
    ],
    "环境保护": [
        (
            "The planet is not a rubbish bin. Reduce waste, reuse bags, recycle right. Save water and power at home with small daily habits. Walk or bike for short trips when you can. Local action adds up when many people join.",
            "地球不是垃圾桶。减废、重复用袋、正确回收。家里用小习惯节水节电。短途能走或骑车就走。许多人一起，本地行动才会加总。"
        ),
        (
            "Pollution has sources you can name: smoke, plastic, dirty rivers. "
            "Learn one local problem and one fix students can support. "
            "Plant trees if your school runs a green project. "
            "Speak with facts, not only anger.",
            "污染有可点名的来源：烟、塑料、脏河。了解一个本地问题与学生能支持的一个对策。"
            "学校有绿化项目就参与种树。用事实说话，不只靠愤怒。",
        ),
        (
            "Climate news can feel huge. Break it into causes, effects, and choices. "
            "Support policies and products that cut harm when your family shops. "
            "Share reliable articles, not panic posts. "
            "Hope is a plan you can measure.",
            "气候新闻可能显得巨大。拆成原因、影响与选择。"
            "家庭购物时支持减害的政策与产品。分享可靠文章，不传恐慌帖。"
            "希望是一份可衡量的计划。",
        ),
        (
            "Wildlife needs habitat. Keep wild places clean on trips. "
            "Do not buy products from endangered species. "
            "Study how food, forests, and oceans connect. "
            "Protecting nature protects our future food and air.",
            "野生动物需要栖息地。出行时保持野外清洁。不买濒危物种制品。"
            "学习食物、森林与海洋如何相连。保护自然，就是保护未来的食物与空气。",
        ),
    ],
    "历史、社会与文化": [
        (
            "History is not only dates. Ask who wrote the record and whose voice is missing. "
            "Compare past and present carefully — not every old idea is wise. "
            "Museums, family stories, and city streets are sources too. "
            "Understanding the past helps you act fairly now.",
            "历史不只是日期。问记录是谁写的、谁的声音缺失。"
            "谨慎对比今昔——并非一切旧观念都明智。博物馆、家史与街道也是来源。"
            "理解过去，帮助你现在行事更公正。",
        ),
        (
            "Culture lives in food, festivals, language, and daily manners. "
            "Respect differences without freezing people into stereotypes. "
            "Learn one tradition deeply instead of collecting empty labels. "
            "Share your own culture with clear pride and open ears.",
            "文化活在饮食、节日、语言与日常礼貌里。尊重差异，不要把人冻成刻板印象。"
            "深入学一种传统，胜过收集空洞标签。带着清楚的自豪与开放的耳朵分享自己的文化。",
        ),
    ],
    "自然生态": [
        (
            "Nature systems connect: soil, water, plants, animals, weather. "
            "Change one part and others shift. "
            "Observe a park or river through a season and keep notes. "
            "Wonder is the start of careful science.",
            "自然系统相连：土壤、水、植物、动物、天气。动一部分，其它会变。"
            "跨一个季节观察公园或河流并做笔记。好奇是谨慎科学的起点。",
        ),
        (
            "Field trips teach more than photos. Draw, measure, ask park staff. Leave no rubbish. Stay on paths to protect plants. Back in class, explain one food chain you saw. Ecology is a story of links, not single facts alone.",
            "实地考察胜过拍照。画图、测量、问公园工作人员。不留垃圾。走步道以护植物。回教室后讲一条你见到的食物链。生态是联系的故事，不是孤立事实。"
        ),
    ],
}


def _ok(con, body: str, layer: str = "G_FINAL") -> list[str]:
    fails = []
    allowed = expand_morphology(set(allowed_words_for(con, layer)))
    oov = sorted({t for t in _tokens(body) if t not in allowed and len(t) > 1})
    if oov:
        fails.append(f"OOV {oov[:20]}")
    hit = has_textbook_copy(con, body)
    if hit:
        fails.append(f"ngram {hit!r}")
    pol = has_political_word(body)
    if pol:
        fails.append(f"political {pol!r}")
    return fails


def main() -> int:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    try:
        lessons = syllabus(con)["lessons"]
        theme_i: dict[str, int] = {}
        written = 0
        errors: list[str] = []
        for les in lessons:
            seq = int(les["seq"])
            focus = les["focus"]
            path = CONTENT_DIR / f"seg-{seq:02d}.json"
            if path.exists() and seq == 1:
                # keep existing pilot unless missing
                continue
            bank = _BANKS.get(focus) or []
            idx = theme_i.get(focus, 0)
            theme_i[focus] = idx + 1
            if idx >= len(bank):
                errors.append(f"seq={seq} focus={focus} bank exhausted idx={idx}")
                continue
            body_en, body_zh = bank[idx]
            bad = _ok(con, body_en)
            if bad:
                errors.append(f"seq={seq} {bad}")
                continue
            years = sorted({q["year"] for q in les.get("evidence_questions") or [] if q.get("year")})
            payload = {
                "seq": seq,
                "segment_id": f"seg-{seq:02d}",
                "layer": "G_FINAL",
                "focus": focus,
                "focus_dim": "theme_l2",
                "title_zh": f"{focus} — 第{seq}节",
                "body_en": body_en,
                "body_zh": body_zh,
                "covers_exam_points": list(les.get("covers_exam_points") or [f"exam_point:theme_l2:{focus}"]),
                "exam_grounded": {
                    "axis": "theme_l2",
                    "label": focus,
                    "evidence_years": years,
                    "note": "焦点=教学提纲 theme_l2; 作业仍为辽宁真题; 本段可背诵讲义非押题",
                },
                "review": {
                    "status": "pass",
                    "reviewed_at": "2026-07-12",
                    "checks": ["lexicon_G_FINAL", "no_10gram_textbook", "exam_grounded_theme_l2", "no_political"],
                    "note": "Phase D batch via generate_phase_d_batch + review_gate",
                },
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written += 1
        reload()
        print(f"written={written} errors={len(errors)}")
        for e in errors:
            print(" ERR", e)
        return 1 if errors else 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
