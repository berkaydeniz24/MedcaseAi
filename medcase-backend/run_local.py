# src/run_local.py
from dotenv import load_dotenv
load_dotenv()

import json
from tutor.schemas import TutorInput
from tutor.tutor_agent import TutorAgent

print("RUN_LOCAL STARTED")


def main():
    agent = TutorAgent()

    base_sample = {
        "case": {
            "id": "PMC123_01",
            "title": "Chest Pain Case",
            "summary": "60 yaşında erkek, ani başlayan göğüs ağrısı ve terleme.",
            "step": {
                "question": "İlk yapılması gereken işlem nedir?",
                "options": ["EKG çek", "Akciğer grafisi", "Kan şekeri ölç"],
                "correct": 0
            }
        },
        "user": {
            "selectedIndex": 1,  # B) Akciğer grafisi
            "ask": "Neden bu seçenek yanlış?"
        },
        "mode": "explain",   # hint | explain | teach
        "language": "tr",
        "userLevel": "beginner"
    }

    # 3 modu tek seferde test et
    for mode in ["hint", "explain", "teach"]:
        sample = dict(base_sample)
        sample["mode"] = mode

        inp = TutorInput(**sample)
        out = agent.run(inp)

        print("\n==== MODE:", mode, "====\n")
        print(json.dumps(out.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

print("RUN_LOCAL FINISHED")