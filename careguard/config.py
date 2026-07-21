from __future__ import annotations

from pathlib import Path

import yaml

from careguard.models.schemas import PolicyPack, ScenarioPack

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "careguard.example.yaml"
DEFAULT_POLICIES = ROOT / "configs" / "healthcare-policy-pack.yaml"
DEFAULT_SCENARIOS = ROOT / "scenarios" / "healthcare" / "scenarios.yaml"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_policy_pack(path: Path = DEFAULT_POLICIES) -> PolicyPack:
    return PolicyPack.model_validate(load_yaml(path))


def load_scenario_pack(path: Path = DEFAULT_SCENARIOS) -> ScenarioPack:
    return ScenarioPack.model_validate(load_yaml(path))


def validate_configuration() -> tuple[PolicyPack, ScenarioPack]:
    policies = load_policy_pack()
    scenarios = load_scenario_pack()
    policy_ids = {policy.policy_id for policy in policies.policies}
    unknown = {
        policy_id
        for scenario in scenarios.scenarios
        for policy_id in scenario.applicable_policy_ids
        if policy_id not in policy_ids
    }
    if unknown:
        raise ValueError(f"scenarios reference unknown policies: {sorted(unknown)}")
    return policies, scenarios

