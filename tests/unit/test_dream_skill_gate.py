"""Unit tests for dream engine skill-genesis approval gate."""
import sys
import types
import pytest

# Stub heavy ML deps that dream_engine imports at module level
for _mod in ["sentence_transformers", "numpy", "sklearn", "sklearn.cluster"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

# Provide SentenceTransformer stub
_st = sys.modules["sentence_transformers"]
if not hasattr(_st, "SentenceTransformer"):

    class _FakeST:
        def __init__(self, *args, **kwargs):
            pass
        def encode(self, x, **kw):
            return [0.0]

    _st.SentenceTransformer = _FakeST

# Also stub numpy since dream_engine uses np.dot etc
if not hasattr(sys.modules["numpy"], "dot"):
    import unittest.mock as _mock
    sys.modules["numpy"] = _mock.MagicMock()


def test_generated_skill_written_as_pending(tmp_path, monkeypatch):
    """Skills from dream engine must land as .pending files, not importable .py."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    from dream_engine import DreamEngine
    engine = DreamEngine.__new__(DreamEngine)
    engine._write_pending_skill("my_auto_skill", "def run(data): return 'ok'")

    pending = skills_dir / "my_auto_skill.pending"
    importable = skills_dir / "my_auto_skill.py"
    assert pending.exists(), "pending file must be created"
    assert not importable.exists(), "must NOT be importable without approval"


def test_pending_skill_content(tmp_path, monkeypatch):
    """The .pending file must contain the generated code verbatim."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skills").mkdir()

    from dream_engine import DreamEngine
    engine = DreamEngine.__new__(DreamEngine)
    engine._write_pending_skill("check_disk", "def run(data): return 'ok'")
    content = (tmp_path / "skills" / "check_disk.pending").read_text()
    assert "def run" in content


def test_pending_skill_overwrites_existing(tmp_path, monkeypatch):
    """Calling _write_pending_skill twice overwrites the previous pending file."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skills").mkdir()

    from dream_engine import DreamEngine
    engine = DreamEngine.__new__(DreamEngine)
    engine._write_pending_skill("my_skill", "def run(data): return 'v1'")
    engine._write_pending_skill("my_skill", "def run(data): return 'v2'")
    content = (tmp_path / "skills" / "my_skill.pending").read_text()
    assert "v2" in content
