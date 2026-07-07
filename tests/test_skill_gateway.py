"""Unit tests for agent.skill_gateway.SkillGateway."""

import os
import time
from pathlib import Path

import pytest


@pytest.fixture
def skill_dirs(tmp_path, monkeypatch):
    """Set up isolated skill directories for testing."""
    hermes_skills = tmp_path / "hermes_skills"
    agents_skills = tmp_path / "agents_skills"
    claude_skills = tmp_path / "claude_skills"
    collision_log = tmp_path / "sync" / "skill_collisions.log"

    hermes_skills.mkdir()
    agents_skills.mkdir()
    claude_skills.mkdir()

    import agent.skill_gateway as sg
    monkeypatch.setattr(sg, "HERMES_SKILLS_DIR", hermes_skills)
    monkeypatch.setattr(sg, "AGENTS_SKILLS_DIR", agents_skills)
    monkeypatch.setattr(sg, "CLAUDE_SKILLS_DIR", claude_skills)
    monkeypatch.setattr(sg, "COLLISION_LOG", collision_log)

    return hermes_skills, agents_skills, claude_skills, collision_log


def _create_hermes_skill(hermes_skills: Path, category: str, name: str) -> Path:
    """Create a mock Hermes skill directory with a SKILL.md."""
    skill_dir = hermes_skills / category / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"# {name}\nA test skill.")
    return skill_dir


class TestSkillGatewayReconcile:
    def test_creates_symlinks(self, skill_dirs):
        hermes_skills, agents_skills, claude_skills, _ = skill_dirs
        _create_hermes_skill(hermes_skills, "tools", "my-skill")

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()

        agents_link = agents_skills / "my-skill"
        assert agents_link.is_symlink()
        assert agents_link.resolve() == (hermes_skills / "tools" / "my-skill").resolve()

        claude_link = claude_skills / "my-skill"
        assert claude_link.is_symlink()
        assert claude_link.resolve() == agents_link.resolve()

    def test_idempotent_on_rerun(self, skill_dirs):
        hermes_skills, agents_skills, claude_skills, _ = skill_dirs
        _create_hermes_skill(hermes_skills, "tools", "my-skill")

        from agent.skill_gateway import SkillGateway
        gw = SkillGateway()
        gw.reconcile()
        gw.reconcile()

        agents_link = agents_skills / "my-skill"
        assert agents_link.is_symlink()
        assert agents_link.resolve() == (hermes_skills / "tools" / "my-skill").resolve()

    def test_skips_and_logs_collision(self, skill_dirs):
        hermes_skills, agents_skills, claude_skills, collision_log = skill_dirs
        _create_hermes_skill(hermes_skills, "tools", "conflicting")

        # Pre-create a non-symlink entry in agents_skills
        existing = agents_skills / "conflicting"
        existing.mkdir()
        (existing / "SKILL.md").write_text("# Claude's version")

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()

        # Should not have been overwritten
        assert not (agents_skills / "conflicting").is_symlink()
        assert (agents_skills / "conflicting" / "SKILL.md").read_text() == "# Claude's version"

        # Collision logged
        assert collision_log.exists()
        log_content = collision_log.read_text()
        assert "conflicting" in log_content

    def test_multiple_skills_across_categories(self, skill_dirs):
        hermes_skills, agents_skills, claude_skills, _ = skill_dirs
        _create_hermes_skill(hermes_skills, "tools", "skill-a")
        _create_hermes_skill(hermes_skills, "research", "skill-b")

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()

        assert (agents_skills / "skill-a").is_symlink()
        assert (agents_skills / "skill-b").is_symlink()
        assert (claude_skills / "skill-a").is_symlink()
        assert (claude_skills / "skill-b").is_symlink()

    def test_no_hermes_skills_dir(self, tmp_path, monkeypatch):
        """Gracefully does nothing when ~/.hermes/skills/ doesn't exist."""
        import agent.skill_gateway as sg
        monkeypatch.setattr(sg, "HERMES_SKILLS_DIR", tmp_path / "nonexistent")

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()  # Should not raise

    def test_claude_to_hermes_reverse_sync(self, skill_dirs):
        """Claude-native skills get bridged back to Hermes visibility."""
        hermes_skills, agents_skills, claude_skills, _ = skill_dirs

        # Create a Claude-native skill (not a symlink to Hermes)
        claude_native = agents_skills / "claude-only"
        claude_native.mkdir()
        (claude_native / "SKILL.md").write_text("# claude-only skill")

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()

        bridge = hermes_skills / "_claude" / "claude-only"
        assert bridge.is_symlink()
        assert bridge.resolve() == claude_native.resolve()

    def test_dangling_symlinks_cleaned(self, skill_dirs):
        """Dangling symlinks are removed during reconcile."""
        hermes_skills, agents_skills, claude_skills, _ = skill_dirs

        # Create a dangling symlink
        dangling = agents_skills / "dead-skill"
        dangling.symlink_to(Path("/nonexistent/path/that/does/not/exist"))

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()

        assert not dangling.exists()
        assert not dangling.is_symlink()

    def test_watcher_lifecycle(self, skill_dirs):
        """Watcher starts and stops cleanly."""
        from agent.skill_gateway import SkillGateway
        gw = SkillGateway()

        gw.start_watcher()
        assert gw._watcher_thread is not None
        assert gw._watcher_thread.is_alive()

        gw.stop_watcher()
        assert gw._watcher_thread is None
