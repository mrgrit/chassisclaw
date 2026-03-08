from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.targets import router as targets_router
from app.api.answers import router as answers_router
from app.api.approvals import router as approvals_router
from app.api.llm import router as llm_router
from app.api.run_auto import router as run_auto_router

from app.services.audit_service import AuditService
from app.services.evidence_service import EvidenceService
from app.services.llm_registry import LLMRegistry
from app.services.probe_loop_service import ProbeLoopService
from app.services.subagent_client import SubAgentClient
from app.services.validation_service import ValidationService

from app.storage.project_store import ProjectStore
from app.storage.target_store import TargetStore

from app.api.skills import router as skills_router
from app.services.skill_registry import SkillRegistry
from app.services.skill_runner import SkillRunner

app = FastAPI(title="ChassisClaw Core")

project_store = ProjectStore()
target_store = TargetStore()
audit_service = AuditService()
evidence_service = EvidenceService()
llm_registry = LLMRegistry()
subagent_client = SubAgentClient()
validation_service = ValidationService()

skill_registry = SkillRegistry()
skills_router.skill_registry = skill_registry
skill_runner = SkillRunner(
    skill_registry=skill_registry,
    project_store=project_store,
    target_store=target_store,
)
skills_router.skill_runner = skill_runner

probe_loop_service = ProbeLoopService(
    llm_registry=llm_registry,
    subagent_client=subagent_client,
    audit_service=audit_service,
    evidence_service=evidence_service,
    validation_service=validation_service,
)

llm_registry.register_connection("master-default", {"id": "master-default", "provider": "stub", "model": "stub-master"})
llm_registry.bind_role("master", "master-default")

for r in [projects_router, targets_router, answers_router, approvals_router, run_auto_router]:
    r.project_store = project_store
    r.target_store = target_store
    r.audit_service = audit_service
    r.probe_loop_service = probe_loop_service

llm_router.llm_registry = llm_registry

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(targets_router)
app.include_router(answers_router)
app.include_router(approvals_router)
app.include_router(llm_router)
app.include_router(run_auto_router)
app.include_router(skills_router)