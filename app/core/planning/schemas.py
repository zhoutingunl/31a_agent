"""
Planning module data models and schemas.

This module defines the core data structures for task planning,
workflow execution, and dynamic plan modification.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Set
from enum import Enum
from pydantic import BaseModel, Field, validator


class TaskType(str, Enum):
    """任务类型枚举"""
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"
    TOOL_CALL = "tool_call"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    PARALLEL = "parallel"
    RETRY = "retry"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ConditionOperator(str, Enum):
    """条件操作符枚举"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class LoopType(str, Enum):
    """循环类型枚举"""
    FOR = "for"
    WHILE = "while"
    RETRY = "retry"


class Condition(BaseModel):
    """执行条件"""
    field: str = Field(..., description="检查的字段路径，支持点号分隔如 'result.status'")
    operator: ConditionOperator = Field(..., description="比较操作符")
    value: Any = Field(..., description="期望值")
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估条件是否满足"""
        try:
            # 支持嵌套字段访问
            field_value = self._get_nested_value(context, self.field)
            
            if self.operator == ConditionOperator.EQUALS:
                return field_value == self.value
            elif self.operator == ConditionOperator.NOT_EQUALS:
                return field_value != self.value
            elif self.operator == ConditionOperator.GREATER_THAN:
                return field_value > self.value
            elif self.operator == ConditionOperator.LESS_THAN:
                return field_value < self.value
            elif self.operator == ConditionOperator.GREATER_EQUAL:
                return field_value >= self.value
            elif self.operator == ConditionOperator.LESS_EQUAL:
                return field_value <= self.value
            elif self.operator == ConditionOperator.CONTAINS:
                return self.value in str(field_value)
            elif self.operator == ConditionOperator.NOT_CONTAINS:
                return self.value not in str(field_value)
            elif self.operator == ConditionOperator.IN:
                return field_value in self.value
            elif self.operator == ConditionOperator.NOT_IN:
                return field_value not in self.value
            elif self.operator == ConditionOperator.EXISTS:
                return field_value is not None
            elif self.operator == ConditionOperator.NOT_EXISTS:
                return field_value is None
            else:
                return False
                
        except (KeyError, TypeError, AttributeError):
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """获取嵌套字段值"""
        keys = field_path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class TaskDefinition(BaseModel):
    """任务定义"""
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")
    task_type: TaskType = Field(..., description="任务类型")
    priority: int = Field(default=0, ge=0, le=10, description="优先级（0-10）")
    conditions: Optional[List[Condition]] = Field(default=None, description="执行条件列表")
    tool_name: Optional[str] = Field(default=None, description="使用的工具名称")
    tool_params: Optional[Dict[str, Any]] = Field(default=None, description="工具参数")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    
    @validator('conditions')
    def validate_conditions(cls, v):
        if v is not None and len(v) == 0:
            return None
        return v


class TaskPlan(BaseModel):
    """任务计划"""
    name: str = Field(..., description="计划名称")
    description: str = Field(..., description="计划描述")
    tasks: List[TaskDefinition] = Field(..., description="任务列表")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="任务依赖关系")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="计划元数据")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    @validator('dependencies')
    def validate_dependencies(cls, v, values):
        """验证依赖关系"""
        if 'tasks' not in values:
            return v
        
        task_names = {task.name for task in values['tasks']}
        
        for task_name, deps in v.items():
            if task_name not in task_names:
                raise ValueError(f"任务 '{task_name}' 不存在")
            for dep in deps:
                if dep not in task_names:
                    raise ValueError(f"依赖任务 '{dep}' 不存在")
        
        return v


class ExecutionResult(BaseModel):
    """执行结果"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    task_results: Dict[str, Any] = Field(default_factory=dict, description="各任务执行结果")
    execution_time: float = Field(..., description="执行时间（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="执行元数据")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")


class LoopConfig(BaseModel):
    """循环配置"""
    type: LoopType = Field(..., description="循环类型")
    items: Optional[List[Any]] = Field(default=None, description="for循环的项目列表")
    condition: Optional[Condition] = Field(default=None, description="while循环的条件")
    max_iterations: int = Field(default=10, ge=1, le=100, description="最大迭代次数")
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="重试延迟（秒）")
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0, description="退避因子")
    
    @validator('condition')
    def validate_condition(cls, v, values):
        if values.get('type') == LoopType.WHILE and v is None:
            raise ValueError("while循环必须指定条件")
        return v


class ParallelGroup(BaseModel):
    """并行执行组"""
    task_names: List[str] = Field(..., description="并行执行的任务名称列表")
    wait_all: bool = Field(default=True, description="是否等待所有任务完成")
    timeout: Optional[float] = Field(default=None, ge=1.0, description="超时时间（秒）")
    
    @validator('task_names')
    def validate_task_names(cls, v):
        if len(v) < 2:
            raise ValueError("并行组至少需要2个任务")
        return v


class DAG:
    """有向无环图"""
    
    def __init__(self):
        self.nodes: Set[int] = set()
        self.edges: Dict[int, Set[int]] = {}
        self.reverse_edges: Dict[int, Set[int]] = {}
        self.node_data: Dict[int, Any] = {}
    
    def add_node(self, node_id: int, data: Any = None) -> None:
        """添加节点"""
        self.nodes.add(node_id)
        self.edges[node_id] = set()
        self.reverse_edges[node_id] = set()
        if data is not None:
            self.node_data[node_id] = data
    
    def add_edge(self, from_id: int, to_id: int) -> None:
        """添加边"""
        if from_id not in self.nodes:
            raise ValueError(f"节点 {from_id} 不存在")
        if to_id not in self.nodes:
            raise ValueError(f"节点 {to_id} 不存在")
        
        self.edges[from_id].add(to_id)
        self.reverse_edges[to_id].add(from_id)
    
    def remove_edge(self, from_id: int, to_id: int) -> None:
        """删除边"""
        if from_id in self.edges:
            self.edges[from_id].discard(to_id)
        if to_id in self.reverse_edges:
            self.reverse_edges[to_id].discard(from_id)
    
    def get_children(self, node_id: int) -> Set[int]:
        """获取子节点"""
        return self.edges.get(node_id, set())
    
    def get_parents(self, node_id: int) -> Set[int]:
        """获取父节点"""
        return self.reverse_edges.get(node_id, set())
    
    def get_roots(self) -> Set[int]:
        """获取根节点（没有父节点的节点）"""
        return {node for node in self.nodes if not self.reverse_edges.get(node, set())}
    
    def get_leaves(self) -> Set[int]:
        """获取叶子节点（没有子节点的节点）"""
        return {node for node in self.nodes if not self.edges.get(node, set())}
    
    def detect_cycle(self) -> bool:
        """检测是否存在环"""
        # 使用DFS检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.nodes}
        
        def dfs(node):
            if color[node] == GRAY:
                return True  # 发现环
            if color[node] == BLACK:
                return False
            
            color[node] = GRAY
            for child in self.get_children(node):
                if dfs(child):
                    return True
            color[node] = BLACK
            return False
        
        for node in self.nodes:
            if color[node] == WHITE:
                if dfs(node):
                    return True
        return False
    
    def topological_sort(self) -> List[int]:
        """拓扑排序"""
        if self.detect_cycle():
            raise ValueError("图中存在环，无法进行拓扑排序")
        
        # Kahn算法
        in_degree = {node: len(self.reverse_edges.get(node, set())) for node in self.nodes}
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for child in self.get_children(node):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        
        return result
    
    def get_execution_levels(self) -> List[List[int]]:
        """获取执行层级（可用于并行执行）"""
        levels = []
        remaining = self.nodes.copy()
        
        while remaining:
            # 找到当前层级：没有未处理父节点的节点
            current_level = []
            for node in list(remaining):
                parents = self.get_parents(node)
                if not parents or all(parent not in remaining for parent in parents):
                    current_level.append(node)
            
            if not current_level:
                # 如果找不到可执行的节点，说明存在环
                raise ValueError("图中存在环")
            
            levels.append(current_level)
            remaining -= set(current_level)
        
        return levels
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "nodes": list(self.nodes),
            "edges": {str(k): list(v) for k, v in self.edges.items()},
            "node_data": {str(k): v for k, v in self.node_data.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DAG":
        """从字典创建DAG"""
        dag = cls()
        
        # 添加节点
        for node_id in data.get("nodes", []):
            node_data = data.get("node_data", {}).get(str(node_id))
            dag.add_node(node_id, node_data)
        
        # 添加边
        for from_id, to_ids in data.get("edges", {}).items():
            for to_id in to_ids:
                dag.add_edge(int(from_id), int(to_id))
        
        return dag


class WorkflowContext(BaseModel):
    """工作流执行上下文"""
    conversation_id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    variables: Dict[str, Any] = Field(default_factory=dict, description="工作流变量")
    task_results: Dict[str, Any] = Field(default_factory=dict, description="任务执行结果")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="上下文元数据")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量值"""
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any) -> None:
        """设置变量值"""
        self.variables[name] = value
        self.updated_at = datetime.utcnow()
    
    def get_task_result(self, task_name: str) -> Any:
        """获取任务结果"""
        return self.task_results.get(task_name)
    
    def set_task_result(self, task_name: str, result: Any) -> None:
        """设置任务结果"""
        self.task_results[task_name] = result
        self.updated_at = datetime.utcnow()
