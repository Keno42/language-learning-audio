"""Derive curricula/fr-ja-a1.toml from fr-en-a1.toml by translating the known-language strings.

Run from the repo root: python tools/derive_fr_ja.py
Add a translation to T for every new English string in fr-en-a1.toml; the script fails loudly on a missing one."""
import json, tomllib, pathlib

T = {
 # meanings
 "Hello.": "こんにちは。", "Thank you.": "ありがとう。", "Please.": "お願いします。", "Goodbye.": "さようなら。",
 "Yes.": "はい。", "No.": "いいえ。", "Excuse me.": "すみません。", "a coffee": "コーヒー",
 "I would like {thing}.": "{thing}をください。", "a tea": "紅茶", "some water": "お水", "a croissant": "クロワッサン",
 "a beer": "ビール", "with milk": "ミルク入り", "without sugar": "砂糖なし",
 "I would like {thing} {addon}.": "{thing}を{addon}でください。", "How much is it?": "いくらですか？",
 "The bill, please.": "お会計をお願いします。", "Is this seat free?": "この席、空いていますか？",
 "Sorry? (I didn't catch that)": "えっ、何ですか？", "Do you speak English?": "英語を話せますか？",
 "I don't understand.": "わかりません。", "More slowly, please.": "もっとゆっくりお願いします。",
 "the station": "駅", "Where is {place}?": "{place}はどこですか？", "the metro": "地下鉄",
 "Where are the toilets?": "トイレはどこですか？", "the hotel": "ホテル", "the pharmacy": "薬局",
 "on the left": "左", "on the right": "右", "straight ahead": "まっすぐ", "It's {direction}.": "{direction}です。",
 "Is it far?": "遠いですか？", "I come from Japan.": "日本から来ました。", "I'm on holiday.": "休暇中です。",
 "Nice to meet you.": "はじめまして。", "Where are you from?": "どちらから来ましたか？", "And you?": "あなたは？",
 "tomorrow": "明日", "this evening": "今晩", "today": "今日", "I'm leaving {time}.": "{time}出発します。",
 "At what time?": "何時に？", "OK, agreed.": "わかりました。", "See you tomorrow!": "また明日！",
 "making a sentence negative": "否定文にする",
 # transform
 "Make it negative:": "否定文にしてください。",
 "I understand.": "わかります。", "I speak English.": "英語を話します。", "I don't speak English.": "英語を話しません。",
 "It's far.": "遠いです。", "It's not far.": "遠くないです。", "I'm not on holiday.": "休暇中ではありません。",
 "I'm leaving tomorrow.": "明日出発します。", "I'm not leaving tomorrow.": "明日は出発しません。",
 # situations
 "You walk into a bakery in the morning. Greet the baker.": "朝、パン屋に入ります。店員にあいさつしてください。",
 "The waiter brings your coffee. Thank him.": "ウェイターがコーヒーを持ってきました。お礼を言ってください。",
 "You are leaving the shop. Say goodbye.": "お店を出ます。別れのあいさつをしてください。",
 "You need to get a stranger's attention in the street.": "道で知らない人に声をかけたいです。",
 "You want to know the price of the croissant.": "クロワッサンの値段を知りたいです。",
 "You've finished your meal. Ask for the bill.": "食事が終わりました。お会計を頼んでください。",
 "You meet someone at a café. Ask whether this seat is free.": "カフェで誰かに会いました。この席が空いているか聞いてください。",
 "Someone spoke too fast. Ask them to say it again.": "相手が早口で聞き取れませんでした。聞き返してください。",
 "You're not sure the receptionist understands you. Ask if she speaks English.": "受付の人に通じているか不安です。英語を話せるか聞いてください。",
 "The waiter explained the menu but you got lost. Tell him you don't understand.": "ウェイターがメニューを説明しましたが、わかりませんでした。そう伝えてください。",
 "The man is giving directions far too fast. Ask him to speak more slowly.": "男性の道案内が速すぎます。もっとゆっくり話すよう頼んでください。",
 "The receptionist gave you directions. Ask whether it's far.": "受付の人が道を教えてくれました。遠いか聞いてください。",
 "Someone asks where you're from. Tell them you come from Japan.": "どこから来たか聞かれました。日本から来たと答えてください。",
 "The woman asks if you're here for work. Tell her you're on holiday.": "仕事で来たのか聞かれました。休暇中だと答えてください。",
 "Your host introduces you to her friend. Say nice to meet you.": "ホストが友人を紹介してくれました。はじめましてと言ってください。",
 "You've just told the man you're from Japan. Ask where he is from.": "日本から来たと伝えました。相手にどこから来たか聞いてください。",
 "You've answered her question. Return it to her.": "質問に答えました。同じ質問を返してください。",
 "You're in a restaurant and need the toilets. Ask where they are.": "レストランでトイレに行きたいです。場所を聞いてください。",
 "He suggested meeting for dinner. Ask at what time.": "夕食に誘われました。何時か聞いてください。",
 "She suggests eight o'clock. Agree.": "8時を提案されました。承諾してください。",
 "You're parting after arranging to meet tomorrow.": "明日会う約束をして、別れるところです。",
 # dialogues
 "You are in a café. There is one free chair at a table where a woman is sitting.": "カフェにいます。女性が座っているテーブルに、空いている椅子が一つあります。",
 "Ask whether this seat is free.": "この席が空いているか聞いてください。",
 "Yes, of course. Where are you from?": "はい、どうぞ。どちらから来ましたか？",
 "Tell her that you come from Japan.": "日本から来たと伝えてください。",
 "Ah, Japan! Are you on holiday?": "ああ、日本！休暇ですか？",
 "Say yes, you're on holiday.": "はい、休暇中だと答えてください。",
 "Yes, I'm on holiday.": "はい、休暇中です。", "Welcome to Paris!": "パリへようこそ！", "Thank her.": "お礼を言ってください。", "Thank him.": "お礼を言ってください。",
 "A waiter comes to your table.": "ウェイターがテーブルに来ました。",
 "Hello. What would you like?": "こんにちは。ご注文は？",
 "Greet him and order a coffee, please.": "あいさつして、コーヒーを注文してください。",
 "Hello. I would like a coffee, please.": "こんにちは。コーヒーをください。",
 "With milk?": "ミルクは入れますか？", "Say: no, thank you.": "「いいえ、結構です」と言ってください。",
 "No, thank you.": "いいえ、結構です。", "Very well.": "かしこまりました。",
 "Later. Ask for the bill.": "しばらくして。お会計を頼んでください。",
 "Here you are. Four euros.": "どうぞ。4ユーロです。",
 "Thank him and say goodbye.": "お礼を言って、別れのあいさつをしてください。",
 "Thank you. Goodbye.": "ありがとう。さようなら。",
 "You are lost in the street. A man walks by.": "道に迷いました。男性が通りかかります。",
 "Get his attention and ask where the metro is.": "声をかけて、地下鉄はどこか聞いてください。",
 "Excuse me, where is the metro?": "すみません、地下鉄はどこですか？",
 "The metro? It's straight ahead, then on the left.": "地下鉄？まっすぐ行って、それから左です。",
 "You didn't catch that. Ask him to speak more slowly.": "聞き取れませんでした。もっとゆっくり話すよう頼んでください。",
 "Straight ahead… then on the left.": "まっすぐ…それから左。",
 "Ask if it's far.": "遠いか聞いてください。", "No, five minutes.": "いいえ、5分です。",
 "Evening, at the hotel reception. The receptionist looks up.": "夜、ホテルの受付です。受付の人が顔を上げます。",
 "Good evening.": "こんばんは。", "Ask if she speaks English.": "英語を話せるか聞いてください。",
 "A little. When are you leaving?": "少し。いつ出発しますか？",
 "Say you're leaving tomorrow.": "明日出発すると言ってください。",
 "OK. The taxi is at eight, is that alright?": "わかりました。タクシーは8時ですが、いいですか？",
 "Say you don't understand.": "わからないと言ってください。",
 "The taxi… tomorrow… eight o'clock.": "タクシー…明日…8時。",
 "Say OK, and thank her.": "わかりましたと言って、お礼を言ってください。",
 "OK. Thank you.": "わかりました。ありがとう。", "Have a good evening!": "良い夜を！",
}

def tr(s):
    if s not in T:
        raise SystemExit(f"missing translation: {s!r}")
    return T[s]

src = tomllib.load(open("curricula/fr-en-a1.toml", "rb"))
q = lambda v: json.dumps(v, ensure_ascii=False)
out = ["# French for Japanese speakers — derived from fr-en-a1.toml (same ids, same structure).",
       "# Regenerate with: python tools/derive_fr_ja.py", "",
       "[curriculum]", 'name = "フランス語 A1 — カフェ・道・ホテル"', 'target_lang = "fr"', 'known_lang = "ja"', 'level = "A1"', ""]
order = ["id", "kind", "target", "meaning", "difficulty", "tags", "topics", "prereqs", "components", "slots", "example", "chunks", "situation", "alternatives", "pronunciation_notes", "instruction"]
for it in src["items"]:
    out.append("[[items]]")
    it = dict(it)
    it["meaning"] = tr(it["meaning"])
    if "situation" in it: it["situation"] = tr(it["situation"])
    if "instruction" in it: it["instruction"] = tr(it["instruction"])
    it.pop("pronunciation_notes", None)
    for k in order:
        if k not in it: continue
        v = it[k]
        if isinstance(v, dict):
            out.append(f"{k} = {{ " + ", ".join(f"{a} = {q(b)}" for a, b in v.items()) + " }")
        else:
            out.append(f"{k} = {q(v)}")
    if "examples" in it:
        out.append("examples = [")
        for e in it["examples"]:
            out.append("  { source = %s, source_meaning = %s, result = %s, result_meaning = %s }," % (q(e["source"]), q(tr(e["source_meaning"])), q(e["result"]), q(tr(e["result_meaning"]))))
        out.append("]")
    out.append("")
for d in src["dialogues"]:
    out += ["[[dialogues]]", f"id = {q(d['id'])}", f"setting = {q(tr(d['setting']))}", f"topics = {q(d['topics'])}"]
    if "requires" in d: out.append(f"requires = {q(d['requires'])}")
    out.append("")
    for t in d["turns"]:
        out.append("  [[dialogues.turns]]")
        for k in ("opener", "opener_meaning", "cue", "expect", "expect_text", "expect_meaning", "partner", "partner_meaning"):
            if k in t:
                v = t[k]
                if k in ("opener_meaning", "cue", "expect_meaning", "partner_meaning"): v = tr(v)
                out.append(f"  {k} = {q(v)}")
        out.append("")
pathlib.Path("curricula/fr-ja-a1.toml").write_text("\n".join(out), encoding="utf-8")
print("ok")
