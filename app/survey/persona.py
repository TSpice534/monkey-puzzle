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

        if question['type'] in ('multi', 'multi_exact'):
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


def resolve_profile_persona(answers: dict, config: dict) -> str | None:
    """Return the persona id the grid answer resolves to, or None if the survey
    has no profile grid, the grid is unanswered, or the answer is malformed.
    (The unanswered/malformed None path is defensive only — the UI makes the grid
    mandatory, so normal completed submissions always resolve here.)"""
    qid = config.get('profile_question')
    if not qid:
        return None
    grid = next((q for q in config['questions'] if q['id'] == qid), None)
    answer = answers.get(qid)
    if grid is None or not (isinstance(answer, list) and len(answer) == 2):
        return None
    x, y = answer
    for cell in grid.get('cells', []):
        if cell['x'] == x and cell['y'] == y:
            return cell['persona']
    return None


def classify_submission(answers: dict, config: dict) -> PersonaResult:
    """Convenience: score_submission -> apply_modifiers -> classify, preferring
    the profile grid's direct persona resolution when available (defensive
    fallback to the weighted classifier's tie_break-ordered argmax otherwise —
    see `resolve_profile_persona`)."""
    scores = score_submission(answers, config)      # keeps hook invocation below
    scores = apply_modifiers(scores, config)         # existing no-op hooks preserved
    winner = resolve_profile_persona(answers, config)
    if winner is not None:
        # Grid directly determines the persona; one-hot score_vector keeps the
        # existing radar/fingerprint chart rendering (highlighting the winner).
        vector = {pid: (1.0 if pid == winner else 0.0) for pid in scores}
        return PersonaResult(persona_id=winner, persona=config['personas'][winner], scores=vector)
    return classify(scores, config)                  # DEFENSIVE fallback (UI now blocks reaching it)
