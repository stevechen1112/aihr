"""Unit tests for feature flag evaluation logic."""
import pytest

from app.config import settings
from app.services.feature_flags import is_flag_enabled


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeSession:
    def __init__(self, result):
        self._result = result

    def query(self, *args, **kwargs):
        return _FakeQuery(self._result)


class _Flag:
    def __init__(self, enabled=True, rollout=0, allowed_tenants=None, allowed_envs=None):
        self.enabled = enabled
        self.rollout_percentage = rollout
        self.allowed_tenant_ids = allowed_tenants or []
        self.allowed_environments = allowed_envs or []


def test_flag_disabled():
    db = _FakeSession(_Flag(enabled=False))
    assert is_flag_enabled(db, "flag", tenant_id="t1") is False


def test_flag_env_scope_blocks(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    db = _FakeSession(_Flag(enabled=True, rollout=100, allowed_envs=["staging"]))
    assert is_flag_enabled(db, "flag", tenant_id="t1") is False


def test_flag_allow_list_wins(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    db = _FakeSession(_Flag(enabled=True, rollout=0, allowed_tenants=["t1"], allowed_envs=["staging"]))
    assert is_flag_enabled(db, "flag", tenant_id="t1") is True


def test_flag_rollout_full(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    db = _FakeSession(_Flag(enabled=True, rollout=100))
    assert is_flag_enabled(db, "flag", tenant_id="t1") is True
