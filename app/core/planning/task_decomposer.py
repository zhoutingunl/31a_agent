"""
Task decomposer for intelligent task planning.

This module provides functionality to decompose complex user requests
into structured task plans with dependencies and execution conditions.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.planning.schemas import (
    TaskPlan, TaskDefinition, TaskType, Condition, ConditionOperator
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskDecomposer:
    """
    任务分解器
    
    功能：
    - 将复杂用户请求分解为结构化任务计划
    - 识别任务间的依赖关系
    - 生成执行条件和优先级
    - 支持多种任务类型和工具调用
    """
    
    def __init__(self, llm_model: str = "deepseek-chat"):
        """
        初始化任务分解器
        
        参数:
            llm_model: 使用的LLM模型名称
        """
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=0.1,  # 低温度确保分解结果稳定
            max_tokens=4000
        )
        
        # 任务分解提示词模板
        self.decomposition_prompt = """
你是一个专业的任务规划专家。请将用户的复杂请求分解为结构化的任务计划。

## 任务类型说明：
- plan: 规划类任务（分析、设计、制定方案）
- execute: 执行类任务（具体操作、代码编写、文件操作）
- reflect: 反思类任务（检查、验证、评估）
- tool_call: 工具调用任务（使用特定工具完成操作）

## 依赖关系规则：
- 分析类任务通常在其他任务之前
- 执行类任务依赖规划类任务
- 验证类任务依赖执行类任务
- 工具调用任务可以并行执行（如果独立）

## 输出格式要求：
请严格按照以下JSON格式输出：

```json
{
    "name": "任务计划名称",
    "description": "任务计划描述",
    "tasks": [
        {
            "name": "任务名称",
            "description": "详细任务描述",
            "task_type": "plan|execute|reflect|tool_call",
            "priority": 1-10,
            "conditions": [
                {
                    "field": "检查的字段",
                    "operator": "eq|gt|lt|contains|exists",
                    "value": "期望值"
                }
            ],
            "tool_name": "工具名称（如果是tool_call类型）",
            "tool_params": {
                "参数名": "参数值"
            },
            "metadata": {
                "estimated_time": "预估时间",
                "complexity": "复杂度"
            }
        }
    ],
    "dependencies": {
        "任务名称": ["依赖的任务名称列表"]
    },
    "metadata": {
        "total_tasks": "总任务数",
        "estimated_duration": "预估总时长",
        "complexity": "整体复杂度"
    }
}
```

## 分解原则：
1. 每个任务应该是原子性的，可以独立执行
2. 任务描述要具体明确，避免模糊表述
3. 合理设置优先级，重要任务优先级高
4. 识别必要的依赖关系，避免循环依赖
5. 为可能失败的任务设置重试条件
6. 考虑并行执行的可能性

用户请求：{user_request}

请开始分解：
"""
    
    def decompose(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """
        分解用户请求为任务计划
        
        参数:
            user_request: 用户请求
            context: 上下文信息（可选）
        
        返回:
            TaskPlan: 结构化的任务计划
        
        异常:
            ValueError: 分解失败时抛出
        """
        try:
            logger.info(f"开始分解任务: {user_request[:100]}...")
            
            # 构建完整的提示词
            full_prompt = self.decomposition_prompt.format(user_request=user_request)
            
            # 添加上下文信息
            if context:
                context_info = f"\n## 上下文信息：\n{json.dumps(context, ensure_ascii=False, indent=2)}\n"
                full_prompt += context_info
            
            # 调用LLM进行分解
            messages = [
                SystemMessage(content="你是一个专业的任务规划专家，擅长将复杂请求分解为可执行的任务计划。"),
                HumanMessage(content=full_prompt)
            ]
            
            response = self.llm.invoke(messages)
            plan_data = self._parse_llm_response(response.content)
            
            # 验证和优化任务计划
            validated_plan = self._validate_and_optimize_plan(plan_data)
            
            logger.info(f"任务分解完成，共生成 {len(validated_plan.tasks)} 个任务")
            return validated_plan
            
        except Exception as e:
            logger.error(f"任务分解失败: {str(e)}")
            raise ValueError(f"任务分解失败: {str(e)}")
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应，提取JSON数据
        
        参数:
            response: LLM响应文本
        
        返回:
            Dict[str, Any]: 解析后的任务计划数据
        """
        try:
            # 尝试提取JSON代码块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有代码块，尝试直接解析
                json_str = response.strip()
            
            # 解析JSON
            plan_data = json.loads(json_str)
            
            # 验证必要字段
            required_fields = ['name', 'description', 'tasks']
            for field in required_fields:
                if field not in plan_data:
                    raise ValueError(f"缺少必要字段: {field}")
            
            return plan_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.error(f"响应内容: {response[:500]}...")
            raise ValueError(f"LLM响应格式错误: {str(e)}")
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            raise ValueError(f"解析响应失败: {str(e)}")
    
    def _validate_and_optimize_plan(self, plan_data: Dict[str, Any]) -> TaskPlan:
        """
        验证和优化任务计划
        
        参数:
            plan_data: 原始计划数据
        
        返回:
            TaskPlan: 验证后的任务计划
        """
        try:
            # 解析任务定义
            tasks = []
            for task_data in plan_data['tasks']:
                task_def = self._parse_task_definition(task_data)
                tasks.append(task_def)
            
            # 解析依赖关系
            dependencies = plan_data.get('dependencies', {})
            
            # 验证依赖关系
            self._validate_dependencies(tasks, dependencies)
            
            # 优化任务计划
            optimized_tasks = self._optimize_task_priorities(tasks, dependencies)
            
            # 创建任务计划
            plan = TaskPlan(
                name=plan_data['name'],
                description=plan_data['description'],
                tasks=optimized_tasks,
                dependencies=dependencies,
                metadata=plan_data.get('metadata', {})
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"验证任务计划失败: {str(e)}")
            raise ValueError(f"任务计划验证失败: {str(e)}")
    
    def _parse_task_definition(self, task_data: Dict[str, Any]) -> TaskDefinition:
        """
        解析任务定义
        
        参数:
            task_data: 任务数据
        
        返回:
            TaskDefinition: 任务定义对象
        """
        # 解析条件
        conditions = []
        for cond_data in task_data.get('conditions', []):
            condition = Condition(
                field=cond_data['field'],
                operator=ConditionOperator(cond_data['operator']),
                value=cond_data['value']
            )
            conditions.append(condition)
        
        # 创建任务定义
        task_def = TaskDefinition(
            name=task_data['name'],
            description=task_data['description'],
            task_type=TaskType(task_data['task_type']),
            priority=task_data.get('priority', 5),
            conditions=conditions if conditions else None,
            tool_name=task_data.get('tool_name'),
            tool_params=task_data.get('tool_params'),
            metadata=task_data.get('metadata', {})
        )
        
        return task_def
    
    def _validate_dependencies(self, tasks: List[TaskDefinition], dependencies: Dict[str, List[str]]) -> None:
        """
        验证依赖关系
        
        参数:
            tasks: 任务列表
            dependencies: 依赖关系字典
        
        异常:
            ValueError: 依赖关系无效时抛出
        """
        task_names = {task.name for task in tasks}
        
        # 检查依赖的任务是否存在
        for task_name, deps in dependencies.items():
            if task_name not in task_names:
                raise ValueError(f"任务 '{task_name}' 不存在")
            
            for dep in deps:
                if dep not in task_names:
                    raise ValueError(f"依赖任务 '{dep}' 不存在")
        
        # 检查循环依赖
        if self._has_cycle(dependencies):
            raise ValueError("存在循环依赖")
    
    def _has_cycle(self, dependencies: Dict[str, List[str]]) -> bool:
        """
        检查是否存在循环依赖
        
        参数:
            dependencies: 依赖关系字典
        
        返回:
            bool: 是否存在循环依赖
        """
        # 使用DFS检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {}
        
        def dfs(node):
            if color.get(node) == GRAY:
                return True  # 发现环
            if color.get(node) == BLACK:
                return False
            
            color[node] = GRAY
            for neighbor in dependencies.get(node, []):
                if dfs(neighbor):
                    return True
            color[node] = BLACK
            return False
        
        for node in dependencies:
            if color.get(node, WHITE) == WHITE:
                if dfs(node):
                    return True
        
        return False
    
    def _optimize_task_priorities(self, tasks: List[TaskDefinition], dependencies: Dict[str, List[str]]) -> List[TaskDefinition]:
        """
        优化任务优先级
        
        参数:
            tasks: 任务列表
            dependencies: 依赖关系字典
        
        返回:
            List[TaskDefinition]: 优化后的任务列表
        """
        # 根据依赖关系调整优先级
        # 没有依赖的任务优先级更高
        for task in tasks:
            if task.name not in dependencies or not dependencies[task.name]:
                # 根任务优先级提高
                task.priority = min(10, task.priority + 2)
            else:
                # 有依赖的任务优先级适当降低
                task.priority = max(1, task.priority - 1)
        
        return tasks
    
    def analyze_dependencies(self, tasks: List[TaskDefinition]) -> Dict[str, List[str]]:
        """
        分析任务间的依赖关系
        
        参数:
            tasks: 任务列表
        
        返回:
            Dict[str, List[str]]: 依赖关系字典
        """
        dependencies = {}
        
        # 基于任务类型推断依赖关系
        plan_tasks = [t for t in tasks if t.task_type == TaskType.PLAN]
        execute_tasks = [t for t in tasks if t.task_type == TaskType.EXECUTE]
        reflect_tasks = [t for t in tasks if t.task_type == TaskType.REFLECT]
        
        # 执行任务依赖规划任务
        for execute_task in execute_tasks:
            if execute_task.name not in dependencies:
                dependencies[execute_task.name] = []
            
            # 找到相关的规划任务
            for plan_task in plan_tasks:
                if self._is_related(execute_task, plan_task):
                    dependencies[execute_task.name].append(plan_task.name)
        
        # 反思任务依赖执行任务
        for reflect_task in reflect_tasks:
            if reflect_task.name not in dependencies:
                dependencies[reflect_task.name] = []
            
            # 找到相关的执行任务
            for execute_task in execute_tasks:
                if self._is_related(reflect_task, execute_task):
                    dependencies[reflect_task.name].append(execute_task.name)
        
        return dependencies
    
    def _is_related(self, task1: TaskDefinition, task2: TaskDefinition) -> bool:
        """
        判断两个任务是否相关
        
        参数:
            task1: 任务1
            task2: 任务2
        
        返回:
            bool: 是否相关
        """
        # 简单的关键词匹配
        keywords1 = set(task1.description.lower().split())
        keywords2 = set(task2.description.lower().split())
        
        # 计算关键词重叠度
        overlap = len(keywords1.intersection(keywords2))
        total = len(keywords1.union(keywords2))
        
        return overlap / total > 0.3 if total > 0 else False
    
    def suggest_parallel_tasks(self, tasks: List[TaskDefinition], dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """
        建议可并行执行的任务组
        
        参数:
            tasks: 任务列表
            dependencies: 依赖关系字典
        
        返回:
            List[List[str]]: 可并行执行的任务组列表
        """
        # 构建DAG
        from app.core.planning.schemas import DAG
        
        dag = DAG()
        task_name_to_id = {task.name: i for i, task in enumerate(tasks)}
        
        # 添加节点
        for task in tasks:
            dag.add_node(task_name_to_id[task.name], task.name)
        
        # 添加边
        for task_name, deps in dependencies.items():
            task_id = task_name_to_id[task_name]
            for dep in deps:
                dep_id = task_name_to_id[dep]
                dag.add_edge(dep_id, task_id)
        
        # 获取执行层级
        try:
            levels = dag.get_execution_levels()
            parallel_groups = []
            
            for level in levels:
                if len(level) > 1:  # 只有多个任务才能并行
                    task_names = [dag.node_data[task_id] for task_id in level]
                    parallel_groups.append(task_names)
            
            return parallel_groups
            
        except ValueError:
            # 如果存在环，返回空列表
            return []
