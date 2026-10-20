"""接口请求与响应的数据结构。"""

# 认证相关数据结构。
from app.schemas.auth import (
    LoginRequest, TokenResponse, UserCreate,
    SetupAdminRequest, UpdateProfileRequest,
    ChangePasswordRequest, UserResponse,
)

# 候选人与人才池相关数据结构。
from app.schemas.candidate import (
    CandidateCreate, CandidateOwnerUpdate, CandidateUpdate,
    CandidateResponse, CandidateListResponse,
    TalentPoolResponse, TalentPoolListResponse,
    ReactivateRequest, TalentPoolCreateRequest,
)

# 简历相关数据结构。
from app.schemas.resume import (
    ResumeUploadResponse, ResumeAnalysisResult, MatchAnalysis,
    ResumeAnalysisResponse, ResumeAnalysisRequest,
)

# 面试相关数据结构。
from app.schemas.interview import (
    TimeSlot, InterviewSlotRequest, InterviewSlotResponse,
    SlotConfirm, ManualScheduleRequest,
    InterviewResponse, InterviewFeedback,
)


__all__ = [
    # 认证。
    "LoginRequest", "TokenResponse", "UserCreate",
    "SetupAdminRequest", "UpdateProfileRequest",
    "ChangePasswordRequest", "UserResponse",

    # 候选人。
    "CandidateCreate", "CandidateOwnerUpdate", "CandidateUpdate",
    "CandidateResponse", "CandidateListResponse",

    # 人才池。
    "TalentPoolResponse", "TalentPoolListResponse",
    "ReactivateRequest", "TalentPoolCreateRequest",

    # 简历。
    "ResumeUploadResponse", "ResumeAnalysisResult", "MatchAnalysis",
    "ResumeAnalysisResponse", "ResumeAnalysisRequest",

    # 面试。
    "TimeSlot", "InterviewSlotRequest", "InterviewSlotResponse",
    "SlotConfirm", "ManualScheduleRequest",
    "InterviewResponse", "InterviewFeedback",
]