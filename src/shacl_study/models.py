from typing import Literal

from pydantic import BaseModel, Field

Endpoint = Literal["code", "repository"]


class PlannedQuery(BaseModel):
    query_id: str
    base_id: str
    query_family: str
    endpoint: Endpoint
    query_text: str
    partition: str
    fork_stream: str = ""
    allow_date_partition: bool = False
    created_start: str | None = None
    created_end: str | None = None


class SearchPage(BaseModel):
    total_count: int
    incomplete_results: bool
    items: list[dict]


class QueryExecution(BaseModel):
    query_id: str
    query_family: str
    endpoint: str
    query_text: str
    partition: str
    executed_at: str
    result_count_reported: int | None = None
    pages_retrieved: int = 0
    incomplete_results: bool | None = None
    potentially_truncated: bool = False
    truncation_reason: str = ""
    api_status: str


class Candidate(BaseModel):
    repository_id: int
    repository_full_name: str
    repository_url: str
    default_branch: str = ""
    discovered_by: list[str] = Field(default_factory=list)
    discovery_queries: list[str] = Field(default_factory=list)
    first_seen_at: str
    last_seen_at: str
    is_fork: bool | None = None
    parent_repository_id: int | None = None
    parent_repository_full_name: str = ""
    archived: bool | None = None
    stars: int | None = None
    license: str = ""
    created_at: str = ""
    updated_at: str = ""
    pushed_at: str = ""
    hydration_status: str = "pending"


class NonPublicHit(BaseModel):
    repository_id: int
    repository_full_name: str
    repository_url: str
    discovery_queries: list[str] = Field(default_factory=list)
    reason: str


class DiscoveryState(BaseModel):
    config_sha256: str
    partition_window_start: str
    partition_window_end: str
    candidates: dict[str, Candidate] = Field(default_factory=dict)
    nonpublic: dict[str, NonPublicHit] = Field(default_factory=dict)
    executions: dict[str, QueryExecution] = Field(default_factory=dict)
