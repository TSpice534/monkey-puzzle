import cairosvg
from email_validator import EmailNotValidError, validate_email
from flask import Response, abort, current_app, flash, redirect, render_template, request, url_for

from app import db, limiter
from app.asset_cache import get_or_render
from app.email_utils import send_result_email
from app.models import Submission
from app.pdf_utils import generate_result_pdf, html_to_pdf, render_result_html
from app.survey import bp
from app.survey.charts import render_fingerprint_svg, render_innovation_curve_svg, render_share_card_svg
from app.survey.loader import get_survey, survey_steps
from app.survey.persona import classify_submission, resolve_innovation_curve, resolve_now_next

# Max stored length for free-text (short_text) answers, in characters. Server-side
# cap bounding the size of the answers JSON column (DoS guard, #0021). The textarea
# maxlength in _question_short_text.html mirrors this as a client hint; this value
# is authoritative.
MAX_SHORT_TEXT_CHARS = 2000


def _get_submission_or_404(token):
    submission = db.session.scalar(db.select(Submission).filter_by(token=token))
    if submission is None:
        abort(404)
    return submission


def _require_classified(token):
    """Return (submission, survey, persona) for a completed submission, or
    404 — used by the asset routes (share image, PDF, email), which have
    nothing sensible to render before a persona exists."""
    submission = _get_submission_or_404(token)
    if submission.persona_id is None:
        abort(404)
    survey = get_survey()
    persona = survey['personas'][submission.persona_id]
    return submission, survey, persona


def _read_answer(question, form):
    """Read the submitted value(s) for `question` from a POSTed form."""
    qid = question['id']
    qtype = question['type']

    if qtype in ('multi', 'multi_exact', 'multi_range'):
        indices = []
        for raw in form.getlist(qid):
            try:
                indices.append(int(raw))
            except (TypeError, ValueError):
                continue
        return indices

    if qtype == 'short_text':
        return (form.get(qid) or '').strip()[:MAX_SHORT_TEXT_CHARS]

    if qtype == 'triangle':
        raw = form.get(qid)
        if raw is None:
            return None
        try:
            return int(raw)                 # corner pick
        except (TypeError, ValueError):
            pass
        try:
            i, j = raw.split(',')
            return [int(i), int(j)]         # edge pick
        except (AttributeError, TypeError, ValueError):
            return None

    # single / spectrum — a single chosen option index, or None if untouched
    raw = form.get(qid)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _innovation_context(submission, survey):
    """Return {'band', 'score', 'colour', 'tagline', 'description', 'curve_svg'}
    for the result surfaces, or None when the survey has no innovation_curve
    config or this submission has no stored band."""
    ic_cfg = survey.get('innovation_curve')
    if not ic_cfg or submission.innovation_band is None:
        return None
    band = next((b for b in ic_cfg['bands'] if b['name'] == submission.innovation_band), None)
    if band is None:
        return None
    return {
        'band': submission.innovation_band,
        'score': submission.innovation_score,
        'colour': band['colour'],
        'tagline': band.get('tagline'),
        'description': band.get('description'),
        'curve_svg': render_innovation_curve_svg(submission.innovation_score, ic_cfg['bands']),
    }


def _now_next_context(submission, survey):
    """{'now': <str|None>, 'next': <str|None>} for the result surfaces, or
    None when the survey has no now_next config."""
    return resolve_now_next(submission.answers, survey, submission.audience)


def _profile_grid_context(submission, survey):
    """Rebuild the (x, y)-shaped grid render context for _result_grid.html
    from the two profile questions + profile_matrix, or (None, None) when the
    survey has no profile_matrix. Axis convention matches
    resolve_profile_persona: profile_approach (Row 1) -> y (vertical),
    profile_scope (Row 2) -> x (horizontal).

    Returns (grid_question, grid_selected):
      grid_question — a dict shaped like the retired grid question:
        {'x_axis': {'label', 'options'}, 'y_axis': {'label', 'options'},
         'cells': [{'x', 'y', 'persona'}, ...]}
      grid_selected — [x, y] (i.e. [scope_answer, approach_answer]), or None
        if either answer is missing/malformed (defensive; both are mandatory).
    """
    matrix = survey.get('profile_matrix')
    if not matrix:
        return None, None
    questions_by_id = {q['id']: q for q in survey['questions']}
    approach_q = questions_by_id.get(matrix['approach_question'])
    scope_q = questions_by_id.get(matrix['scope_question'])
    if approach_q is None or scope_q is None:
        return None, None

    grid_question = {
        'x_axis': {
            'label': scope_q['prompt'],
            'options': [opt['label'] for opt in scope_q['options']],
        },
        'y_axis': {
            'label': approach_q['prompt'],
            'options': [opt['label'] for opt in approach_q['options']],
        },
        'cells': [
            {'x': c['scope'], 'y': c['approach'], 'persona': c['persona']}
            for c in matrix['cells']
        ],
    }

    approach = submission.answers.get(matrix['approach_question'])
    scope = submission.answers.get(matrix['scope_question'])
    grid_selected = None
    if (isinstance(approach, int) and not isinstance(approach, bool)
            and isinstance(scope, int) and not isinstance(scope, bool)):
        grid_selected = [scope, approach]   # [x, y]

    return grid_question, grid_selected


def _guard_message(question, value, survey):
    """Return a flash message if `value` fails `question`'s advance rule, else None."""
    qtype = question['type']
    if qtype == 'multi_exact':
        n = question['choose_exactly']
        if not (isinstance(value, list) and len(value) == n):
            return f'Please select exactly {n} option{"s" if n != 1 else ""}.'
    if qtype == 'multi_range':
        lo, hi = question['choose_min'], question['choose_max']
        if not (isinstance(value, list) and lo <= len(value) <= hi):
            return f'Please select between {lo} and {hi} options.'
    matrix = survey.get('profile_matrix') or {}
    if question['id'] in {matrix.get('approach_question'), matrix.get('scope_question')}:
        if not isinstance(value, int) or isinstance(value, bool):
            return 'Please choose an option to continue.'
    return None


def _render_step(survey, step_questions, submission, step, total, token, saved):
    """Render survey/step.html for either a single-question step or the
    combined profile step (approach_question immediately followed by
    scope_question — see loader.survey_steps)."""
    common = dict(title='The Monkey Puzzle', step=step, total=total,
                  token=token, audience=submission.audience)
    if len(step_questions) == 2:            # combined profile pair
        matrix = survey['profile_matrix']
        approach_q, scope_q = step_questions
        stem = matrix['sentence_stem']
        if submission.audience == 'organisation' and matrix.get('sentence_stem_organisation'):
            stem = matrix['sentence_stem_organisation']
        return render_template(
            'survey/step.html', combined_profile=True,
            profile_prompt=matrix['prompt'], sentence_stem=stem,
            approach_question=approach_q, scope_question=scope_q,
            saved_approach=saved.get(approach_q['id']),
            saved_scope=saved.get(scope_q['id']), **common)
    question = step_questions[0]
    return render_template(
        'survey/step.html', combined_profile=False,
        question=question, saved_value=saved.get(question['id']), **common)


def _why_context(submission, survey):
    """The respondent's free-text `output: why` answer for the result
    surfaces (stripped), or None when the survey has no `output: why`
    question, the submission never answered it, or the answer is blank
    (the question is skippable; old submissions predate it)."""
    q = next((q for q in survey['questions'] if q.get('output') == 'why'), None)
    if q is None:
        return None
    raw = submission.answers.get(q['id'])
    if not isinstance(raw, str):
        return None
    return raw.strip() or None


@bp.route('/start')
@limiter.limit('60 per minute')
def start():
    submission = Submission()
    db.session.add(submission)
    db.session.commit()
    return redirect(url_for('survey.step', token=submission.token, step=1))


@bp.route('/<token>/step/<int:step>', methods=['GET', 'POST'])
@limiter.limit('180 per minute')
def step(token, step):
    submission = _get_submission_or_404(token)

    survey = get_survey()
    steps = survey_steps(survey, submission.audience)
    total = len(steps)

    if step < 1 or step > total:
        abort(404)

    step_questions = steps[step - 1]

    if request.method == 'POST':
        saved = {q['id']: submission.answers.get(q['id']) for q in step_questions}
        read = {}
        for q in step_questions:
            value = _read_answer(q, request.form)
            saved[q['id']] = value
            msg = _guard_message(q, value, survey)
            if msg:
                flash(msg, 'danger')
                return _render_step(survey, step_questions, submission, step, total, token, saved)
            read[q['id']] = value

        # JSON columns need reassignment, not in-place mutation, to be
        # picked up reliably by SQLAlchemy.
        submission.answers = {**submission.answers, **read}

        # Router recompute (router is always its own single-question step 1)
        router_id = survey.get('respondent_type_question')
        if router_id in read:
            question = next(q for q in step_questions if q['id'] == router_id)
            value = read[router_id]
            options = question.get('options', [])
            chosen = options[value] if isinstance(value, int) and 0 <= value < len(options) else None
            submission.audience = chosen.get('audience_value') if chosen else None
            # Recompute — answering the router changes which questions
            # (and therefore what `total` is) apply for the rest of the flow.
            steps = survey_steps(survey, submission.audience)
            total = len(steps)

        if step < total:
            db.session.commit()
            return redirect(url_for('survey.step', token=token, step=step + 1))

        result = classify_submission(submission.answers, survey)
        submission.persona_id = result.persona_id
        submission.score_vector = result.scores
        ic = resolve_innovation_curve(submission.answers, survey, result.persona_id)
        if ic is not None:
            submission.innovation_band = ic.band
            submission.innovation_score = ic.score
        db.session.commit()
        return redirect(url_for('survey.result', token=token))

    saved = {q['id']: submission.answers.get(q['id']) for q in step_questions}
    return _render_step(survey, step_questions, submission, step, total, token, saved)


@bp.route('/<token>/result')
def result(token):
    submission = _get_submission_or_404(token)
    survey = get_survey()

    if submission.persona_id is None:
        steps = survey_steps(survey, submission.audience)
        next_step = next(
            (i for i, sq in enumerate(steps, start=1)
             if any(q['id'] not in submission.answers for q in sq)),
            1,
        )
        return redirect(url_for('survey.step', token=token, step=next_step))

    persona = survey['personas'][submission.persona_id]

    grid_question, grid_selected = _profile_grid_context(submission, survey)

    return render_template(
        'survey/result.html',
        title=persona['name'],
        submission=submission,
        persona=persona,
        personas=survey['personas'],
        grid_question=grid_question,
        grid_selected=grid_selected,
        innovation=_innovation_context(submission, survey),
        now_next=_now_next_context(submission, survey),
        why=_why_context(submission, survey),
        audience=submission.audience,
    )


@bp.route('/<token>/share.png')
def share_image(token):
    submission, survey, persona = _require_classified(token)
    svg = render_share_card_svg(persona, submission.score_vector, survey['personas'])
    png = get_or_render(
        svg, '.png',
        lambda: cairosvg.svg2png(bytestring=svg.encode(), output_width=1200, output_height=630),
    )
    response = Response(png, mimetype='image/png')
    # Deterministic per submission once classified — safe to cache.
    response.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    return response


@bp.route('/<token>/pdf')
def download_pdf(token):
    submission, survey, persona = _require_classified(token)
    fingerprint_svg = render_fingerprint_svg(submission.score_vector, survey['personas'])
    innovation = _innovation_context(submission, survey)
    now_next = _now_next_context(submission, survey)
    why = _why_context(submission, survey)
    html = render_result_html(
        persona, survey['personas'], fingerprint_svg,
        innovation=innovation, now_next=now_next, why=why, audience=submission.audience,
    )
    pdf_bytes = get_or_render(
        html + '\x00' + (request.url_root or ''), '.pdf',
        lambda: html_to_pdf(html, base_url=request.url_root),
    )
    filename = f"{persona['name'].replace(' ', '_')}_MonkeyPuzzle.pdf"
    response = Response(pdf_bytes, mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@bp.route('/<token>/email', methods=['POST'])
@limiter.limit('5 per hour')
def email_result(token):
    submission, survey, persona = _require_classified(token)

    if not current_app.config.get('MAIL_SERVER'):
        flash("Email isn't configured on this deployment yet.", 'warning')
        return redirect(url_for('survey.result', token=token))

    raw_email = (request.form.get('email') or '').strip()
    try:
        validated = validate_email(raw_email, check_deliverability=False)
    except EmailNotValidError:
        flash("That email address doesn't look right — please check it and try again.", 'danger')
        return redirect(url_for('survey.result', token=token))

    fingerprint_svg = render_fingerprint_svg(submission.score_vector, survey['personas'])
    result_url = url_for('survey.result', token=token, _external=True)
    innovation = _innovation_context(submission, survey)
    now_next = _now_next_context(submission, survey)
    send_result_email(
        validated.normalized, persona, survey['personas'], fingerprint_svg,
        result_url, innovation=innovation, now_next=now_next, base_url=request.url_root,
        audience=submission.audience,
    )
    flash('Sent! Check your inbox in a minute or two.', 'success')
    return redirect(url_for('survey.result', token=token))
