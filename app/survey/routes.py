from flask import abort, redirect, render_template, request, url_for

from app import db
from app.models import Submission
from app.survey import bp
from app.survey.charts import render_fingerprint_svg
from app.survey.loader import get_survey
from app.survey.persona import classify_submission


def _get_submission_or_404(token):
    submission = db.session.scalar(db.select(Submission).filter_by(token=token))
    if submission is None:
        abort(404)
    return submission


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
    questions = survey['questions']
    total = len(questions)

    if step < 1 or step > total:
        abort(404)

    question = questions[step - 1]

    if request.method == 'POST':
        value = _read_answer(question, request.form)
        # JSON columns need reassignment, not in-place mutation, to be
        # picked up reliably by SQLAlchemy.
        submission.answers = {**submission.answers, question['id']: value}

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
        next_step = next(
            (i for i, q in enumerate(survey['questions'], start=1)
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
