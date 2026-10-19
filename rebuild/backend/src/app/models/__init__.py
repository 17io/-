# 导入用户模型和角色枚举，供其他模块通过 app.models 使用。
from app.models.user import User, UserRole

# 导入候选人模型和状态枚举，供其他模块通过 app.models 使用。
from app.models.candidate import Candidate, CandidateStatus

# 导入简历模型，供其他模块通过 app.models 使用。
from app.models.resume import Resume

# 可重复使用的问卷模板。
from app.models.questionnaire_template import QuestionnaireTemplate

# 面向候选人的问卷实例与答卷记录。
from app.models.questionnaire import Questionnaire, QuestionnaireResponse

# 面试模型、面试状态和轮次枚举。
from app.models.interview import Interview, InterviewStatus, InterviewRound

# 人才池模型与人才池状态枚举。
from app.models.talent_pool import TalentPool, TalentPoolStatus

# 通知记录模型。
from app.models.notification import Notification