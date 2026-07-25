from evaluation.automated_checks import compute_automated_checks
from evaluation.schemas import CallMetrics, GeneratedContent, SystemRunResult


def _result(content=None):
    return SystemRunResult(
        case_id="test-case",
        system="single_agent",
        content=content,
        calls=[CallMetrics(step="monolithic", model="test-model", latency_ms=100.0, success=content is not None)],
    )


def test_failed_generation_is_flagged():
    checks = compute_automated_checks(_result(content=None))
    assert checks.schema_valid is False
    assert "generation_failed" in checks.flags


def test_clean_output_has_no_flags():
    content = GeneratedContent(
        question="A 45-year-old man presents with crushing chest pain radiating to the jaw.",
        options=[
            "Acute myocardial infarction due to coronary artery occlusion",
            "Gastroesophageal reflux disease",
            "Musculoskeletal chest wall pain",
            "Panic attack with somatic symptoms",
        ],
        correct_index=0,
        hint="Consider the radiation pattern and associated risk factors before settling on a diagnosis.",
        explanation=(
            "The presentation is most consistent with acute myocardial infarction due to coronary artery "
            "occlusion, given the crushing quality and jaw radiation of the pain, which are classic anginal "
            "features not typical of reflux, musculoskeletal pain, or panic attacks."
        ),
    )
    checks = compute_automated_checks(_result(content=content))
    assert checks.schema_valid is True
    assert checks.has_duplicate_options is False
    assert checks.has_empty_option is False
    assert "possible_answer_leak_in_question" not in checks.flags


def test_duplicate_options_are_flagged():
    content = GeneratedContent(
        question="Which finding is present?",
        options=["Fever", "fever", "Cough", "Rash"],
        correct_index=0,
        hint="Think about vital signs.",
        explanation="The correct finding relates to temperature elevation.",
    )
    checks = compute_automated_checks(_result(content=content))
    assert checks.has_duplicate_options is True
    assert "duplicate_options" in checks.flags


def test_answer_leaked_in_question_is_flagged():
    content = GeneratedContent(
        question=(
            "This patient has pigment dispersion syndrome from iris vaulting against the "
            "implanted lens — which structure is mechanically involved?"
        ),
        options=[
            "Pigment dispersion syndrome from iris vaulting against the implanted lens",
            "Age-related macular degeneration",
            "Bacterial conjunctivitis",
            "Retinal detachment",
        ],
        correct_index=0,
        hint="Think about mechanical contact between structures.",
        explanation=(
            "The correct mechanism is pigment dispersion syndrome caused by iris vaulting "
            "against the implanted lens, which releases pigment into the anterior chamber — "
            "unlike macular degeneration, conjunctivitis, or retinal detachment, none of which "
            "involve mechanical iris-lens contact."
        ),
    )
    checks = compute_automated_checks(_result(content=content))
    assert "possible_answer_leak_in_question" in checks.flags
