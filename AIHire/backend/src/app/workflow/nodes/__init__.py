"""招聘工作流节点。"""

from app.workflow.nodes.classify import classify_node  # 导出岗位分类节点。

from app.workflow.nodes.talent_pool import move_to_talent_pool_node  # 导出人才池节点。

__all__ = ["classify_node", "move_to_talent_pool_node"]
