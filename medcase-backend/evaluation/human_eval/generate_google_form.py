# evaluation/human_eval/generate_google_form.py
"""
Embeds blinded_eval_set.json into generate_google_form_template.gs to
produce the final generate_google_form.gs — a self-contained Google Apps
Script that, when run once in script.google.com under the user's own
Google account, builds a real Google Form (with a linked response
spreadsheet) covering the same 24-case blinded set and 5-criterion rubric
as rating_form.html. This project has no Google API credentials configured,
so the form itself can't be created directly from here — the user runs the
generated script themselves.

Usage:
    cd medcase-backend
    python3 -m evaluation.human_eval.generate_google_form
"""
import json
import os

HUMAN_EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HUMAN_EVAL_DIR, "generate_google_form_template.gs")
DATA_PATH = os.path.join(HUMAN_EVAL_DIR, "blinded_eval_set.json")
OUTPUT_PATH = os.path.join(HUMAN_EVAL_DIR, "generate_google_form.gs")


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, ensure_ascii=False)
    output = template.replace("__DATA_JSON__", data_json)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"{len(data)} cases embedded -> {OUTPUT_PATH}")
    print("Next: paste this file's contents into a new project at https://script.google.com and run createForm()")


if __name__ == "__main__":
    main()
