"""Email sending for The Monkey Puzzle (Phase 5) — "email me a copy".

Anonymous, opt-in only: the email address is used once, to send this
message, and is never persisted (no `Submission` column stores it) — the
whole point of this fork is no accounts, no stored PII.

Mail is dispatched in a background thread so SMTP latency/failures never
block or time out the user-facing request, mirroring the Donut Toolkit's
`email_utils.py` pattern.
"""
import threading

from flask import current_app, render_template
from flask_mail import Message

from app import mail
from app.pdf_utils import generate_result_pdf


def _send_async(app, msg_kwargs, persona, personas, fingerprint_svg, result_url, base_url) -> None:
    with app.app_context():
        msg = Message(**msg_kwargs)
        msg.body = render_template('email/result.txt', persona=persona, result_url=result_url)
        msg.html = render_template('email/result.html', persona=persona, result_url=result_url)

        try:
            pdf_bytes = generate_result_pdf(persona, personas, fingerprint_svg, base_url=base_url)
            filename = f"{persona['name'].replace(' ', '_')}_MonkeyPuzzle.pdf"
            msg.attach(filename, 'application/pdf', pdf_bytes)
        except Exception:
            app.logger.exception('Failed to generate PDF for result email — sending without attachment')

        try:
            mail.send(msg)
        except Exception:
            app.logger.exception('Failed to send result email to %s', msg.recipients)


def send_result_email(recipient_email: str, persona: dict, personas: dict, fingerprint_svg: str,
                       result_url: str, base_url: str = None) -> threading.Thread:
    """Fire-and-forget: email `recipient_email` a copy of their result + PDF.

    Returns the background `Thread` — the route ignores it, but tests can
    `.join()` it for a deterministic assertion point instead of racing the
    background send.
    """
    app = current_app._get_current_object()
    msg_kwargs = dict(
        subject='Your sustainable who — The Monkey Puzzle',
        sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
        recipients=[recipient_email],
    )
    thread = threading.Thread(
        target=_send_async,
        args=(app, msg_kwargs, persona, personas, fingerprint_svg, result_url, base_url),
        daemon=True,
    )
    thread.start()
    return thread
