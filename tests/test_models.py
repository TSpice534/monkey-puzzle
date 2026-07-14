"""Submission model: creation, defaults, persistence, and the failure
case of violating the token uniqueness constraint."""
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Submission


def test_bare_submission_can_be_created_and_persisted(db):
    submission = Submission()
    db.session.add(submission)
    db.session.commit()

    assert submission.id is not None

    fetched = db.session.get(Submission, submission.id)
    assert fetched is not None


def test_token_auto_populates(db):
    submission = Submission()
    db.session.add(submission)
    db.session.commit()

    assert submission.token is not None
    assert isinstance(submission.token, str)
    assert len(submission.token) == 43  # secrets.token_urlsafe(32) length


def test_two_submissions_get_different_tokens(db):
    a = Submission()
    b = Submission()
    db.session.add_all([a, b])
    db.session.commit()

    assert a.token != b.token


def test_answers_defaults_to_empty_dict(db):
    submission = Submission()
    db.session.add(submission)
    db.session.commit()

    assert submission.answers == {}


def test_persona_id_and_score_vector_default_to_none(db):
    submission = Submission()
    db.session.add(submission)
    db.session.commit()

    assert submission.persona_id is None
    assert submission.score_vector is None


def test_timestamps_populated_on_create(db):
    submission = Submission()
    db.session.add(submission)
    db.session.commit()

    assert isinstance(submission.created_at, datetime)
    assert isinstance(submission.updated_at, datetime)


def test_repr_does_not_error(db):
    submission = Submission()
    db.session.add(submission)
    db.session.commit()

    assert str(submission.id) in repr(submission)


def test_answers_and_score_vector_round_trip_json(db):
    submission = Submission(
        answers={'q1': 'yes'},
        persona_id='the-curator',
        score_vector={'novelty': 0.5},
    )
    db.session.add(submission)
    db.session.commit()
    db.session.expire_all()

    fetched = db.session.get(Submission, submission.id)
    assert fetched.answers == {'q1': 'yes'}
    assert fetched.persona_id == 'the-curator'
    assert fetched.score_vector == {'novelty': 0.5}


def test_duplicate_token_violates_unique_constraint(db):
    """Failure case: two submissions cannot share the same token."""
    a = Submission(token='fixed-token-for-uniqueness-test-1234567890')
    db.session.add(a)
    db.session.commit()

    b = Submission(token='fixed-token-for-uniqueness-test-1234567890')
    db.session.add(b)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
