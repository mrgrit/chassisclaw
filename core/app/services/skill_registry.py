import json
from pathlib import Path


class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)

    def list_skills(self) -> list[dict]:
        results = []
        if not self.skills_dir.exists():
            return results

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "skill.json"
            if not skill_file.exists():
                continue
            try:
                data = json.loads(skill_file.read_text(encoding="utf-8"))
                results.append(data)
            except Exception:
                continue
        return results

    def get_skill(self, skill_id: str) -> dict | None:
        for skill in self.list_skills():
            if skill.get("id") == skill_id:
                return skill
        return None

    def get_plan_template(self, skill_id: str) -> dict | None:
        skill = self.get_skill(skill_id)
        if not skill:
            return None

        skill_dir = self.skills_dir / skill_id
        plan_file = skill_dir / "plan.template.json"
        if not plan_file.exists():
            return None

        return json.loads(plan_file.read_text(encoding="utf-8"))