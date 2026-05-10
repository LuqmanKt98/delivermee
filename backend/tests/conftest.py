"""Pytest fixtures: set Firebase mode before importing the app."""

import os

import pytest

# Must run before `app` import so routes register and settings match Firestore mode.
os.environ.setdefault("USE_FIREBASE_DB", "true")
os.environ.setdefault("GCP_PROJECT", "demo-project")


@pytest.fixture
def app():
    from app import create_app

    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()
