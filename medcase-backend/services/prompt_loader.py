# services/prompt_loader.py
"""
Loads prompt templates from medcase-backend/prompts/ as string.Template
objects ($variable syntax — deliberately NOT str.format()/f-strings, since
several prompts embed literal JSON examples with `{` `}` in their
instructional text, which would collide with {}-style placeholders).

Each agent picks a fixed PROMPT_VERSION and logs it on every call so a
thesis writeup can cite exactly which prompt version produced a given
result (e.g. "all Week 4 runs used dialogue prompt v1.0").
"""
import os
from string import Template

PROMPTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompts")
)


def load_prompt(name: str, version: str = "v1.0") -> Template:
    path = os.path.join(PROMPTS_DIR, f"{name}_{version}.txt")
    with open(path, "r", encoding="utf-8") as f:
        return Template(f.read())
