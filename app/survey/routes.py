import cairosvg
from email_validator import EmailNotValidError, validate_email
from flask import Response, abort, current_app, flash, redirect, render_template, request, url_for

from app import db, limiter
from app.email_utils import send_result_email
from app.models import Submission
from app.pdf_utils import generate_result_pdf
from app.survey import bp
from app.survey.charts import render_fingerprint_svg, render_share_card_svg
from app.survey.loader import effective_questions, get_survey
from app.survey.persona import classify_submission


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

    if qtype == 'multi':
        indices = []
        for raw in form.getlist(qid):
            try:
                indices.append(int(raw))
            except (TypeError, ValueError):
                continue
        return indices

    if qtype == 'short_text':
        return (form.get(qid) or '').strip()

    # single / spectrum — a single chosen option index, or None if untouched
    raw = form.get(qid)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@bp.route('/start')
def start():
    submission = Submission()
    db.session.add(submission)
    db.session.commit()
    return redirect(url_for('survey.step', token=submission.token, step=1))


@bp.route('/<token>/step/<int:step>', methods=['GET', 'POST'])
def step(token, step):
    submission = _get_submission_or_404(token)

    survey = get_survey()
    questions = effective_questions(survey, submission.audience)
    total = len(questions)

    if step < 1 or step > total:
        abort(404)

    question = questions[step - 1]

    if request.method == 'POST':
        value = _read_answer(question, request.form)
        # JSON columns need reassignment, not in-place mutation, to be
        # picked up reliably by SQLAlchemy.
        submission.answers = {**submission.answers, question['id']: value}

        if question['id'] == survey.get('respondent_type_question'):
            options = question.get('options', [])
            chosen = options[value] if isinstance(value, int) and 0 <= value < len(options) else None
            submission.audience = chosen.get('audience_value') if chosen else None
            # Recompute — answering the router changes which questions
            # (and therefore what `total` is) apply for the rest of the flow.
            questions = effective_questions(survey, submission.audience)
            total = len(questions)

        if step < total:
            db.session.commit()
            return redirect(url_for('survey.step', token=token, step=step + 1))

        result = classify_submission(submission.answers, survey)
        submission.persona_id = result.persona_id
        submission.score_vector = result.scores
        db.session.commit()
        return redirect(url_for('survey.result', token=token))

    saved_value = submission.answers.get(question['id'])
    return render_template(
        'survey/step.html',
        title='The Monkey Puzzle',
        question=question,
        saved_value=saved_value,
        step=step,
        total=total,
        token=token,
    )


@bp.route('/<token>/result')
def result(token):
    submission = _get_submission_or_404(token)
    survey = get_survey()

    if submission.persona_id is None:
        questions = effective_questions(survey, submission.audience)
        next_step = next(
            (i for i, q in enumerate(questions, start=1)
             if q['id'] not in submission.answers),
            1,
        )
        return redirect(url_for('survey.step', token=token, step=next_step))

    persona = survey['personas'][submission.persona_id]
    fingerprint_svg = render_fingerprint_svg(submission.score_vector, survey['personas'])

    return render_template(
        'survey/result.html',
        title=persona['name'],
        submission=submission,
        persona=persona,
        personas=survey['personas'],
        fingerprint_svg=fingerprint_svg,
    )


@bp.route('/<token>/share.png')
def share_image(token):
    submission, survey, persona = _require_classified(token)
    svg = render_share_card_svg(persona, submission.score_vector, survey['personas'])
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=1200, output_height=630)
    response = Response(png, mimetype='image/png')
    # Deterministic per submission once classified — safe to cache.
    response.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    return response


@bp.route('/<token>/pdf')
def download_pdf(token):
    submission, survey, persona = _require_classified(token)
    fingerprint_svg = render_fingerprint_svg(submission.score_vector, survey['personas'])
    pdf_bytes = generate_result_pdf(
        persona, survey['personas'], fingerprint_svg, base_url=request.url_root,
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
    send_result_email(
        validated.normalized, persona, survey['personas'], fingerprint_svg,
        result_url, base_url=request.url_root,
    )
    flash('Sent! Check your inbox in a minute or two.', 'success')
    return redirect(url_for('survey.result', token=token))
