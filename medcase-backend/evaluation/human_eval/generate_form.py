# evaluation/human_eval/generate_form.py
"""
Embeds blinded_eval_set.json into rating_form_template.html to produce the
final, fully self-contained rating_form.html (no fetch() at runtime, so it
opens directly from disk or works as a static single-file share — no
external requests, matches the blinding file's "safe to share with raters"
status since it contains no system labels).

Usage:
    cd medcase-backend
    python3 -m evaluation.human_eval.generate_form
"""
import json
import os

HUMAN_EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HUMAN_EVAL_DIR, "rating_form_template.html")
DATA_PATH = os.path.join(HUMAN_EVAL_DIR, "blinded_eval_set.json")
OUTPUT_PATH = os.path.join(HUMAN_EVAL_DIR, "rating_form.html")


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, ensure_ascii=False)
    # </script>-safe: a case narrative or explanation could in principle
    # contain the literal substring "</script>", which would truncate the
    # inline JSON and break the page.
    data_json = data_json.replace("</script>", "<\\/script>")

    output = template.replace("__DATA_JSON__", data_json)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"{len(data)} cases embedded -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
