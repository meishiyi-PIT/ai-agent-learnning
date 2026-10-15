from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing_extensions import Annotated

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Form, Header, Request, Response, status
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from zbt.api.responses import success_response
from zbt.core.errors import AppError
from zbt.domains.identity.models import H5User
from zbt.domains.identity.service import H5AuthService
from zbt.domains.renewal.service import RenewalAdviceService
service_bearer = HTTPBearer(auto_error=False)

class RenewalAdviceRequest:
    policy_id:str=Field(min_length=16,max_length=64)
    question:str=Field(min_length=5,max_length=500)

class RenewalResponseBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RenewalPolicyResponse(RenewalResponseBase):
    policy_id: str
    policy_no: str
    product_name: str
    plan_name: str
    coverage_end: str


class RenewalRecommendationResponse(RenewalResponseBase):
    decision: Literal[
        "RENEW_ORIGINAL",
        "UPGRADE",
        "NEED_MORE_INFORMATION",
        "CANNOT_DETERMINE",
    ]
    selected_option_code: Literal["RENEW_ORIGINAL", "UPGRADE"] | None = None
    selected_option_name: str | None = None
    premium_cents: int | None = Field(default=None, ge=0)
    summary: str = Field(min_length=1, max_length=500)
    reasons: list[str] = Field(default_factory=list, max_length=3)


class RenewalEvidenceResponse(RenewalResponseBase):
    document_id: str
    document_version: int = Field(ge=1)
    title: str
    source_name: str
    excerpt: str


class RenewalAdviceData(RenewalResponseBase):
    run_id: str
    thread_id: str
    status: Literal["COMPLETED"] = "COMPLETED"
    policy: RenewalPolicyResponse
    recommendation: RenewalRecommendationResponse
    missing_information: list[str] = Field(default_factory=list, max_length=3)
    evidence: list[RenewalEvidenceResponse] = Field(default_factory=list, max_length=5)
    invoked_tools: list[str]
    trace_id: str | None = None
    trace_url: str | None = None


class RenewalResponseMeta(RenewalResponseBase):
    request_id: str
    server_time: str


class RenewalAdviceResponse(RenewalResponseBase):
    success: Literal[True] = True
    data: RenewalAdviceData
    meta: RenewalResponseMeta

def create_renewalAdvice_roueter(
        service:RenewalAdviceService,
        h5_auth_service:H5AuthService
) -> APIRouter:
    router = apiRouter(tags=["renewal_advice"])
    # **需要补充的逻辑**：
    # 1. 用 HTTPBearer 取 H5 Token，参考 backend/src/zbt/api/v1/agent.py
    #    里 current_h5_user 的写法
    # 2. POST 路径（比如 /h5/agent/renewal-advice），声明 response_model
    # 3. 调用 service.get_advice(user, policy_id=..., question=...)
    # 4. 用 success_response(request, data) 返回统一包络
    apiRouter=APIRouter(tags="renewAdivce")

    def current_H5_user(
            credentials:Annotated[
                HTTPAuthorizationCredentials |None,
                Depends(service_bearer),
            ],
    ) -> H5User:
        if credentials is None:
            raise AppError("AUTH_REQUIRED", "请先登录", 401)
        return h5_auth_service.authenticate_access(credentials.credentials)

    @router.post(
            "/h5/agent/renewal-advice",
    )
    async def renewal_advice(request:Request,
                             user:Annotated[H5User,Depends(current_H5_user)],
                             policy_id:Annotated[str,Form(min_length=26,max_length=26)],
                             quesion:str
                             ) -> dict[str,Any]:
        return success_response(
            request,
            service.get_advice(
                user=user,
                policy_id=policy_id,
                question=quesion,
                
            )
        )
        