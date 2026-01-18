# src/tutor/prompts.py

def tutor_system_prompt(language: str, mode: str) -> str:
    tr_base = """
Sen bir tıp eğitim asistanısın (TutorAgent). Görevin:
- Sadece eğitim amaçlı anlat; tıbbi teşhis/tedavi talimatı verme.
- Yalnızca verilen vaka özeti + soru + seçenekler üzerinden konuş. Dış bilgi ekleme.
- Net, yapılandırılmış ve kısa yaz (maksimum ~1200 karakter hedefle).
- Kullanıcının seçimi varsa: neden daha zayıf/kuvvetli olduğunu pedagojik şekilde açıkla.
- Kullanıcı seçim yapmadıysa “Seçilen şık” diye bahsetme.
- Doğru şık dataset.correct alanıdır.
""".strip()

    en_base = """
You are a medical education tutor (TutorAgent). Your job:
- Educational only; do not provide real medical diagnosis/treatment instructions.
- Only use the provided case summary + question + options. Do not add external facts.
- Be concise and structured (aim <= ~1200 chars).
- If the user selected an option: explain pedagogically why it is weaker/stronger.
- If the user did not select an option, do not mention “selected option”.
- The dataset.correct field is the ground truth.
""".strip()

    if language == "tr":
        if mode == "hint":
            return (tr_base + """
MODE=HINT:
- Doğru/yanlış şıkkı ASLA belirtme.
- Seçenek harfi (A/B/C...) yazma.
- “Doğru cevap”, “yanlış”, “ilk yapılması gereken değildir” gibi kesin hüküm cümleleri kurma.
- Sadece 2-3 ipucu ve karar mantığı ver.
""").strip()

        if mode == "teach":
            return (tr_base + """
MODE=TEACH:
- Final satırında mutlaka: “Dataset’e göre doğru seçenek: <HARF>) <metin>” yaz.
- Kısa mini-ders ver: (1) yaklaşım, (2) kritik ipucu, (3) sık yapılan hata.
""").strip()

        # explain
        return (tr_base + """
MODE=EXPLAIN:
- Final satırında mutlaka: “Dataset’e göre doğru seçenek: <HARF>) <metin>” yaz.
- 3-6 madde ile kısa gerekçe ver.
""").strip()

    # EN
    if mode == "hint":
        return (en_base + """
MODE=HINT:
- NEVER reveal which option is correct/incorrect.
- Do not mention option letters (A/B/C...).
- Avoid definitive judgments like “correct”, “wrong”, “not the first step”.
- Provide only 2-3 hints and the decision logic.
""").strip()

    if mode == "teach":
        return (en_base + """
MODE=TEACH:
- In the Final line, always write: “Dataset-correct option: <LETTER>) <text>”.
- Provide a micro-lesson: (1) approach, (2) key clue, (3) common mistake.
""").strip()

    # explain
    return (en_base + """
MODE=EXPLAIN:
- In the Final line, always write: “Dataset-correct option: <LETTER>) <text>”.
- Provide a short rationale in 3-6 bullets.
""").strip()


def tutor_user_prompt(payload: dict) -> str:
    c = payload["case"]
    step = c["step"]
    user = payload.get("user", {}) or {}

    options = step["options"]
    correct = step.get("correct", None)
    selected = user.get("selectedIndex", None)
    ask = user.get("ask", "")

    def fmt_idx(i):
        return f"{chr(65+i)}) {options[i]}" if i is not None and 0 <= i < len(options) else "N/A"

    lines = []
    lines.append(f"CASE_ID: {c.get('id','')}")
    lines.append(f"TITLE: {c.get('title','')}")
    lines.append(f"SUMMARY: {c.get('summary','')}")
    lines.append("")
    lines.append(f"QUESTION: {step.get('question','')}")
    lines.append("OPTIONS:")
    for i, opt in enumerate(options):
        lines.append(f"{chr(65+i)}) {opt}")
    lines.append("")
    lines.append(f"DATASET_CORRECT: {fmt_idx(correct)}")
    lines.append(f"USER_SELECTED: {fmt_idx(selected) if selected is not None else 'None'}")
    if ask:
        lines.append(f"USER_ASK: {ask}")
    lines.append("")
    lines.append("RESPONSE FORMAT (STRICT):")
    lines.append("Answer must be plain text with these sections:")
    lines.append("Final: (one short line)")
    lines.append("Why: (3-6 bullet points max)")
    lines.append("Takeaway: (1-3 lines)")
    lines.append("Do NOT include follow-up questions inside the answer (they will be returned separately).")

    return "\n".join(lines)