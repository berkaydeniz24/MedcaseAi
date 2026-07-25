import pytest
from pydantic import ValidationError

from mcq.schemas import MCQOutput


def test_valid_mcq_contract():
    item = MCQOutput(
        question="What is the most likely diagnosis?",
        options=["A", "B", "C", "D"],
        correctIndex=1,
        rationale="The case findings support B.",
    )
    assert item.correctIndex == 1
    assert item.options == ["A", "B", "C", "D"]


def test_duplicate_options_are_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis?",
            options=["A", "A", "C", "D"],
            correctIndex=0,
            rationale="Rationale",
        )


def test_duplicate_options_are_case_insensitive():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis?",
            options=["Sepsis", "sepsis", "Pneumonia", "PE"],
            correctIndex=0,
            rationale="Rationale",
        )


def test_empty_option_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis?",
            options=["A", "  ", "C", "D"],
            correctIndex=0,
            rationale="Rationale",
        )


def test_correct_index_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis?",
            options=["A", "B", "C", "D"],
            correctIndex=4,
            rationale="Rationale",
        )


def test_wrong_option_count_is_rejected():
    with pytest.raises(ValidationError):
        MCQOutput(
            question="What is the most likely diagnosis?",
            options=["A", "B", "C"],
            correctIndex=0,
            rationale="Rationale",
        )


def test_options_are_stripped():
    item = MCQOutput(
        question="What is the most likely diagnosis?",
        options=["  A  ", "B", "C", "D"],
        correctIndex=0,
        rationale="Rationale",
    )
    assert item.options[0] == "A"
