"""Persona classifier: turns raw survey answers into a winning persona plus
the full nine-dim score vector (the "fingerprint").

Reuses Donut Toolkit's scoring *helper style* (small pure functions,
negative-weight support) — not its per-section band thresholds, which do
not apply here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaResult:
    persona_id: str
    persona: dict            # the winning persona's config entry (incl. 'id')
    scores: dict              # full nine-dim vector {persona_id: float}, all 9 keys present


def score_submission(answers: dict, config: dict) -> dict:
    """Init every persona id to 0.0. For each answered scored question, resolve the
    chosen option(s) by stored index and add each option's `weights` into the vector.
    short_text questions contribute nothing. Ignore answers whose question id or option
    index is unknown (defensive)."""
    scores = {persona_id: 0.0 for persona_id in config['personas']}

    questions_by_id = {q['id']: q for q in config['questions']}

    for question_id, value in answers.items():
        question = questions_by_id.get(question_id)
        if question is None or question['type'] == 'short_text':
            continue

        options = question.get('options', [])
        options_by_index = {opt['index']: opt for opt in options}

        if question['type'] == 'multi':
            indices = value if isinstance(value, list) else []
        else:
            indices = [value] if isinstance(value, int) else []

        for index in indices:
            option = options_by_index.get(index)
            if option is None:
                continue
            for persona_id, weight in option.get('weights', {}).items():
                if persona_id in scores:
                    scores[persona_id] += weight

    return scores


def apply_modifiers(scores: dict, config: dict) -> dict:
    """Pure transform hook. When scoring.equity_modifier.enabled and
    scoring.rogers_curve.enabled are both false (MVP), return scores unchanged (a copy).
    Keep them as separate no-op branches so enabling later is a config flip."""
    scoring = config.get('scoring', {})
    result = dict(scores)

    if scoring.get('equity_modifier', {}).get('enabled'):
        pass  # deferred — not implemented in MVP

    if scoring.get('rogers_curve', {}).get('enabled'):
        pass  # deferred — not implemented in MVP

    return result


def classify(scores: dict, config: dict) -> PersonaResult:
    """Argmax over `scores`. Break ties deterministically by scoring.tie_break order
    (earliest in tie_break wins). Return PersonaResult with the winner + full vector."""
    tie_break = config['scoring']['tie_break']
    max_score = max(scores.values())
    winner = next(
        persona_id for persona_id in tie_break
        if scores.get(persona_id) == max_score
    )
    return PersonaResult(
        persona_id=winner,
        persona=config['personas'][winner],
        scores=dict(scores),
    )


def classify_submission(answers: dict, config: dict) -> PersonaResult:
    """Convenience: score_submission -> apply_modifiers -> classify."""
    scores = score_submission(answers, config)
    scores = apply_modifiers(scores, config)
    return classify(scores, config)
