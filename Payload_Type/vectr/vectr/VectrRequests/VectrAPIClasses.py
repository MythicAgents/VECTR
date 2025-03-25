# import re
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator, root_validator


class VectrGQLConnParams(BaseModel):
    api_key: str
    vectr_gql_url: str

class VectrRESTConnParams(BaseModel):
    api_key: str
    vectr_rest_url: str

"""
VECTR Connection Class Object
"""
class vectr_connection():
    def __init__(self, org_name, connection_params, target_db, campaign_name, campaign_id, assessment_id):
        self.org_name = org_name
        self.connection_params = connection_params
        self.target_db = target_db
        self.campaign_name = campaign_name
        self.campaign_id = campaign_id
        self.assessment_id = assessment_id


class TestCase(BaseModel):
    name: str = Field(alias="Variant")
    description: Optional[str] = Field(alias="Objective")
    phase: Optional[str] = Field(alias="Phase")
    technique: Optional[str] = Field(alias="MitreID")
    tags: Optional[List[str]] = Field(alias="Tags")
    organization: Optional[str] = Field(alias="Organizations")
    status: Optional[str] = Field(alias="Status")
    targets: Optional[List[str]] = Field(alias="TargetAssets")
    sources: Optional[List[str]] = Field(alias="SourceIps")
    defenses: Optional[List[str]] = Field(alias="ExpectedDetectionLayers")
    detectionSteps: Optional[List[str]] = Field(alias="DetectionRecommendations")
    alertTriggered: Optional[str] = Field(alias="AlertTriggered")
    activityLogged: Optional[str] = Field(alias="ActivityLogged")
    outcome: Optional[str] = Field(alias="Outcome")
    outcomePath: Optional[str] = Field(alias="Outcome Path")
    outcomeNotes: Optional[str] = Field(alias="OutcomeNotes")
    alertSeverity: Optional[str] = Field(alias="Alert Severity")
    detectionTime: Optional[float] = Field(alias="Detection Time Epoch")
    detectingDefenseTools: Optional[List[Dict[str, str]]] = Field(alias="DetectingTools")
    references: Optional[List[str]] = Field(alias="References")
    redTools: Optional[List[Dict[str, str]]] = Field(alias="Attacker Tools")
    operatorGuidance: Optional[str] = Field(alias="Command")
    attackStart: Optional[float] = Field(alias="StartTimeEpoch")
    attackStop: Optional[float] = Field(alias="StopTimeEpoch")

    @root_validator(pre=True)
    def check_technique(cls, values):
        if 'MitreID' in values and values['MitreID']:
            # everything is fine, MitreID exists, continue
            return values

        if 'Method' in values and values['Method']:
            values['MitreID'] = values['Method']
            return values

        raise ValueError("Non-empty Method (Attack Technique) or MitreID required for Test Case creation")

    # @TODO - combine for reuse, getting weird behavior with multiple annotations
    @validator('sources', pre=True, allow_reuse=True)
    def validate_sources(cls, v: str) -> Optional[List[str]]:
        sources = v.split(',')
        if not sources:
            return None
        return list(filter(None, sources))

    @validator('references', pre=True, allow_reuse=True)
    def validate_references(cls, v: str) -> Optional[List[str]]:
        refs = v.split(',')
        if not refs:
            return None
        return list(filter(None, refs))

    @validator('tags', pre=True, allow_reuse=True)
    def validate_tags(cls, v: str) -> Optional[List[str]]:
        tags = v.split(',')
        if not tags:
            return None
        return list(filter(None, tags))

    @validator('organization', pre=True, allow_reuse=True)
    def validate_organization(cls, v: str) -> Optional[str]:
        orgs = v.split(',')
        if orgs:
            return orgs[0]
        else:
            return None

    @validator('defenses', pre=True, allow_reuse=True)
    def validate_defenses(cls, v: str) -> Optional[List[str]]:
        defenses = v.split(',')
        if not defenses:
            return None
        return list(filter(None, defenses))

    @validator('detectionSteps', pre=True, allow_reuse=True)
    def validate_detection_steps(cls, v: str) -> Optional[List[str]]:
        if not v:
            return None
        return [v]

    @validator('detectingDefenseTools', pre=True, allow_reuse=True)
    def validate_detecting_tools(cls, v: str) -> List[Dict[str, str]]:
        tools = []
        tool_names = v.split(',')
        tool_names = list(filter(None, tool_names))

        for tool_name in tool_names:
            tools.append({"name": tool_name})

        return tools

    @validator('redTools', pre=True, allow_reuse=True)
    def validate_attack_tools(cls, v: str) -> List[Dict[str, str]]:
        tools = []
        tool_names = v.split(',')
        tool_names = list(filter(None, tool_names))

        for tool_name in tool_names:
            tools.append({"name": tool_name})

        return tools

    @validator('targets', pre=True, allow_reuse=True)
    def validate_targets(cls, v: str) -> Optional[List[str]]:
        targets = v.split(',')
        if not targets:
            return None
        return list(filter(None, targets))

    @validator('status', pre=True, allow_reuse=True)
    def validate_upper_enum1(cls, v: str) -> str:
        return v

    @validator('outcome', pre=True, allow_reuse=True)
    def validate_upper_enum2(cls, v: str) -> str:
        return v

    @validator('outcomeNotes', pre=True, allow_reuse=True)
    def validate_outcomeNotes(cls, v: str) -> Optional[str]:
        return v

    @validator('alertSeverity', pre=True, allow_reuse=True)
    def validate_upper_enum3(cls, v: str) -> str:
        return v

    @validator('alertTriggered', pre=True, allow_reuse=True)
    def validate_upper_enum4(cls, v: str) -> str:
        return v

    @validator('activityLogged', pre=True, allow_reuse=True)
    def validate_upper_enum5(cls, v: str) -> str:
        return v

    @validator('attackStart', pre=True, allow_reuse=True)
    def validate_attack_start(cls, v: str) -> Optional[float]:
        if not v:
            return None
        return float(v)

    @validator('attackStop', pre=True, allow_reuse=True)
    def validate_attack_stop(cls, v: str) -> Optional[float]:
        if not v:
            return None
        return float(v)

    @validator('detectionTime', pre=True, allow_reuse=True)
    def validate_detection_time(cls, v: str) -> Optional[float]:
        if not v:
            return None
        return float(v)


class TestCaseGQLInput(BaseModel):
    testCaseData: TestCase


class Campaign(BaseModel):
    name: str
    test_cases: Optional[List[TestCase]]


class Assessment(BaseModel):
    name: str
    campaigns: Optional[Dict[str, Campaign]]
