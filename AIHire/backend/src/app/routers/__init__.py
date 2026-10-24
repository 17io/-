"""API 路由包。"""

from app.routers import auth  # 导出认证路由模块，供应用注册接口。

from app.routers import candidates  # 导出候选人管理路由模块。

from app.routers import dashboard  # 导出招聘统计和评分权重管理路由。

__all__ = ["auth", "candidates", "dashboard"]
