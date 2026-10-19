# 导入用户模型和角色枚举，供其他模块通过 app.models 使用。
from app.models.user import User, UserRole

# 导入候选人模型和状态枚举，供其他模块通过 app.models 使用。
from app.models.candidate import Candidate, CandidateStatus