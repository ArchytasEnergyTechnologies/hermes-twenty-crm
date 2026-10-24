import importlib.util
from pathlib import Path
import sys

import pytest

from agent.secret_scope import reset_secret_scope, set_secret_scope
from hermes_constants import reset_hermes_home_override, set_hermes_home_override


_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "twenty_crm_home_scope_plugin",
    _ROOT / "__init__.py",
    submodule_search_locations=[str(_ROOT)],
)
assert _SPEC and _SPEC.loader
plugin = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = plugin
_SPEC.loader.exec_module(plugin)


@pytest.mark.parametrize("module", [plugin.runtime, plugin.tools])
def test_api_key_uses_profile_secret_scope(module, monkeypatch, tmp_path):
    monkeypatch.setenv("TWENTY_API_KEY", "process-value")
    token = set_secret_scope(
        {"TWENTY_API_KEY": "home-value"}, profile_home=str(tmp_path)
    )
    try:
        assert module._env("TWENTY_API_KEY") == "home-value"
        assert plugin.tools._auth("api_key")[0] == {
            "Authorization": "Bearer home-value"
        }
    finally:
        reset_secret_scope(token)


def test_oauth_cache_uses_home_override(monkeypatch, tmp_path):
    process_home = tmp_path / "process-home"
    profile_home = tmp_path / "profile-home"
    monkeypatch.setenv("HERMES_HOME", str(process_home))
    token = set_hermes_home_override(profile_home)
    try:
        assert plugin.tools._token_cache_path() == (
            profile_home / "cache" / "twenty-crm-oauth.json"
        )
        assert (profile_home / "cache").is_dir()
        assert not process_home.exists()
    finally:
        reset_hermes_home_override(token)


def test_managed_project_uses_home_override(monkeypatch, tmp_path):
    process_home = tmp_path / "process-home"
    profile_home = tmp_path / "profile-home"
    monkeypatch.setenv("HERMES_HOME", str(process_home))
    token = set_hermes_home_override(profile_home)
    scope_token = set_secret_scope({}, profile_home=str(profile_home))
    try:
        assert plugin.runtime.hermes_home() == profile_home
        assert plugin.runtime.managed_project_dir() == (
            profile_home / "projects" / "twenty-crm"
        )
    finally:
        reset_secret_scope(scope_token)
        reset_hermes_home_override(token)
