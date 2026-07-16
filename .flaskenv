FLASK_APP=monkeypuzzle.py
FLASK_DEBUG=1
# DATABASE_URL intentionally left unset — config.py's fallback already builds an
# absolute sqlite path (basedir/monkeypuzzle.db). A relative sqlite:/// URL here
# would get resolved by Flask-SQLAlchemy 3.x against app.instance_path, not the
# process's CWD — which silently pointed `flask db upgrade` at a different .db
# file than Gunicorn actually reads in production (deploy.sh's Part 7 migrated
# instance/monkeypuzzle.db while the app ran against monkeypuzzle.db at the repo
# root), causing "no such table" 500s despite a clean migration run. Do not
# reintroduce a relative DATABASE_URL here.
# Required for WeasyPrint (Phase 5 PDF export) to find Homebrew-installed pango on macOS
DYLD_LIBRARY_PATH=/opt/homebrew/lib
