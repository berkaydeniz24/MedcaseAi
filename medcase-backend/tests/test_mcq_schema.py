import pytest
from pydantic import ValidationError

from mcq.schemas import DistractorExplanation, MCQOption, MCQOutput

VALID_OPTIONS = [
    MCQOption(id="A", text="Acute myocardial infarction"),
    MCQOption(id="B", text="Gastroesophageal reflux disease"),
    MCQOption(id="C", text="Musculoskeletal chest pain"),
    MCQOption(id="D", text="Panic attack"),
]

VALID_RATIONALE = "The crushing pain radiating to the jaw with diaphoresis is classic for MI, not the other options."


def test_valid_mcq_contract():
    item = MCQOutput(
        question="What is the most likely diagnosis for this presentation?",
        options=VALID_OPTIONS,
        correct_option_id="A",
        rationale=VALID_RATIONALE,
    )
    assert item.correct_option_id == "A"
    assert item.option_text("A") == "Acute myocardial infarction"


def test_optional_distractor_explanations():
    item = MCQOutput(
        question="What is the most likely diagnosis for this presentation?",
        options=VALID_OPTIONS,
        correct_option_id="A",
        rationale=VALID_RATIONALE,
        distractor_explanations=[
            DistractorExplanation(option_id="B", explanation="No relation to meals or reflux symptoms."),
        ],
    )
    assert item.distractor_explanations[0].option_id == "B"


def test_duplicate_option_ids_are_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis for this presentation?",
            options=[
                MCQOption(id="A", text="Acute myocardial infarction"),
                MCQOption(id="A", text="Gastroesophageal reflux disease"),
                MCQOption(id="C", text="Musculoskeletal chest pain"),
                MCQOption(id="D", text="Panic attack"),
            ],
            correct_option_id="A",
            rationale=VALID_RATIONALE,
        )


def test_duplicate_option_text_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis for this presentation?",
            options=[
                MCQOption(id="A", text="Acute myocardial infarction"),
                MCQOption(id="B", text="acute myocardial infarction"),
                MCQOption(id="C", text="Musculoskeletal chest pain"),
                MCQOption(id="D", text="Panic attack"),
            ],
            correct_option_id="A",
            rationale=VALID_RATIONALE,
        )


def test_empty_option_text_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis for this presentation?",
            options=[
                MCQOption(id="A", text="Acute myocardial infarction"),
                MCQOption(id="B", text="   "),
                MCQOption(id="C", text="Musculoskeletal chest pain"),
                MCQOption(id="D", text="Panic attack"),
            ],
            correct_option_id="A",
            rationale=VALID_RATIONALE,
        )


def test_wrong_option_count_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis for this presentation?",
            options=VALID_OPTIONS[:3],
            correct_option_id="A",
            rationale=VALID_RATIONALE,
        )


def test_short_rationale_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis for this presentation?",
            options=VALID_OPTIONS,
            correct_option_id="A",
            rationale="Too short.",
        )


def test_trivial_rationale_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis for this presentation?",
            options=VALID_OPTIONS,
            correct_option_id="A",
            rationale="Because it is correct",
        )


def test_short_question_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="Why?",
            options=VALID_OPTIONS,
            correct_option_id="A",
            rationale=VALID_RATIONALE,
        )
