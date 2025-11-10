"""
文件名: task.py
功能: 任务管理相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


# ==================== 基础模型 ====================

class TaskBase(BaseModel):
    """任务基础模型"""
    task_type: str = Field(..., description="任务类型：plan/execute/reflect/tool_call")
    description: str = Field(..., description="任务描述")
    priority: int = Field(default=0, ge=0, le=10, description="优先级（0-10，数值越大优先级越高）")
    dependencies: Optional[List[int]] = Field(default=None, description="依赖任务ID列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class TaskCreate(TaskBase):
    """创建任务模型"""
    conversation_id: int = Field(..., description="会话ID")
    parent_task_id: Optional[int] = Field(default=None, description="父任务ID")


class TaskUpdate(BaseModel):
    """更新任务模型"""
    task_type: Optional[str] = Field(default=None, description="任务类型")
    description: Optional[str] = Field(default=None, description="任务描述")
    status: Optional[str] = Field(default=None, description="任务状态")
    priority: Optional[int] = Field(default=None, ge=0, le=10, description="优先级")
    dependencies: Optional[List[int]] = Field(default=None, description="依赖任务ID列表")
    result: Optional[str] = Field(default=None, description="执行结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class TaskStatusUpdate(BaseModel):
    """任务状态更新模型"""
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = Field(
        ..., description="任务状态"
    )
    result: Optional[str] = Field(default=None, description="执行结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class TaskResponse(TaskBase):
    """任务响应模型"""
    id: int = Field(..., description="任务ID")
    conversation_id: int = Field(..., description="会话ID")
    parent_task_id: Optional[int] = Field(default=None, description="父任务ID")
    status: str = Field(..., description="任务状态")
    result: Optional[str] = Field(default=None, description="执行结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    retry_count: int = Field(default=0, description="重试次数")
    started_at: Optional[datetime] = Field(default=None, description="开始执行时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


# ==================== 查询模型 ====================

class TaskQuery(BaseModel):
    """任务查询模型"""
    conversation_id: Optional[int] = Field(default=None, description="会话ID")
    status: Optional[str] = Field(default=None, description="任务状态")
    task_type: Optional[str] = Field(default=None, description="任务类型")
    parent_task_id: Optional[int] = Field(default=None, description="父任务ID")
    priority_min: Optional[int] = Field(default=None, ge=0, le=10, description="最小优先级")
    priority_max: Optional[int] = Field(default=None, ge=0, le=10, description="最大优先级")
    created_after: Optional[datetime] = Field(default=None, description="创建时间之后")
    created_before: Optional[datetime] = Field(default=None, description="创建时间之前")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="created_at", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序排列")
    
    @validator('priority_max')
    def validate_priority_range(cls, v, values):
        if v is not None and 'priority_min' in values and values['priority_min'] is not None:
            if v < values['priority_min']:
                raise ValueError('最大优先级不能小于最小优先级')
        return v


# ==================== 统计模型 ====================

class TaskStatistics(BaseModel):
    """任务统计模型"""
    total: int = Field(..., description="总任务数")
    pending: int = Field(..., description="待执行任务数")
    running: int = Field(..., description="正在运行任务数")
    completed: int = Field(..., description="已完成任务数")
    failed: int = Field(..., description="失败任务数")
    cancelled: int = Field(..., description="已取消任务数")


class TaskTypeStatistics(BaseModel):
    """任务类型统计模型"""
    task_type: str = Field(..., description="任务类型")
    count: int = Field(..., description="数量")
    completed: int = Field(..., description="已完成数量")
    failed: int = Field(..., description="失败数量")
    success_rate: float = Field(..., description="成功率")


# ==================== 任务树模型 ====================

class TaskTreeNode(TaskResponse):
    """任务树节点模型"""
    subtasks: List['TaskTreeNode'] = Field(default_factory=list, description="子任务列表")
    can_start: bool = Field(default=False, description="是否可以开始执行")
    dependency_status: Dict[str, Any] = Field(default_factory=dict, description="依赖状态")


class TaskTreeResponse(BaseModel):
    """任务树响应模型"""
    root_tasks: List[TaskTreeNode] = Field(..., description="根任务列表")
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    progress: float = Field(..., description="完成进度（0-1）")


# ==================== 批量操作模型 ====================

class TaskBatchCreate(BaseModel):
    """批量创建任务模型"""
    tasks: List[TaskCreate] = Field(..., description="任务列表")
    parent_task_id: Optional[int] = Field(default=None, description="父任务ID")


class TaskBatchUpdate(BaseModel):
    """批量更新任务模型"""
    task_ids: List[int] = Field(..., description="任务ID列表")
    updates: TaskUpdate = Field(..., description="更新内容")


class TaskBatchDelete(BaseModel):
    """批量删除任务模型"""
    task_ids: List[int] = Field(..., description="任务ID列表")
    cascade: bool = Field(default=True, description="是否级联删除子任务")


# ==================== 工作流模型 ====================

class TaskWorkflow(BaseModel):
    """任务工作流模型"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    tasks: List[TaskCreate] = Field(..., description="任务列表")
    dependencies: List[Dict[str, int]] = Field(..., description="依赖关系列表")


class TaskWorkflowResponse(BaseModel):
    """任务工作流响应模型"""
    workflow_id: int = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    tasks: List[TaskResponse] = Field(..., description="任务列表")
    status: str = Field(..., description="工作流状态")
    progress: float = Field(..., description="完成进度")
    created_at: datetime = Field(..., description="创建时间")


# ==================== 依赖关系模型 ====================

class TaskDependency(BaseModel):
    """任务依赖关系模型"""
    task_id: int = Field(..., description="任务ID")
    depends_on: List[int] = Field(..., description="依赖的任务ID列表")
    dependency_type: str = Field(default="blocking", description="依赖类型：blocking/soft")


class TaskDependencyGraph(BaseModel):
    """任务依赖图模型"""
    nodes: List[TaskResponse] = Field(..., description="任务节点列表")
    edges: List[Dict[str, int]] = Field(..., description="依赖边列表")
    cycles: List[List[int]] = Field(default_factory=list, description="循环依赖列表")
    topological_order: List[int] = Field(default_factory=list, description="拓扑排序结果")


# 更新前向引用
TaskTreeNode.model_rebuild()
