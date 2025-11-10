"""
文件名: task_dao.py
功能: 任务管理相关的数据访问对象
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, and_, or_, desc, asc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.dao.base import BaseDAO
from app.models.task import Task
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskDAO(BaseDAO[Task]):
    """
    任务数据访问对象
    
    功能：
    - 任务的 CRUD 操作
    - 任务状态管理
    - 任务依赖关系处理
    - 任务查询和过滤
    """
    
    def __init__(self, db: Session):
        super().__init__(Task, db)
    
    def create_task(self, 
                   conversation_id: int,
                   task_type: str,
                   description: str,
                   parent_task_id: Optional[int] = None,
                   priority: int = 0,
                   dependencies: Optional[List[int]] = None,
                   task_metadata: Optional[Dict[str, Any]] = None) -> Task:
        """
        创建新任务
        
        参数:
            conversation_id: 会话ID
            task_type: 任务类型
            description: 任务描述
            parent_task_id: 父任务ID（可选）
            priority: 优先级
            dependencies: 依赖任务ID列表
            task_metadata: 元数据
        
        返回:
            Task: 创建的任务对象
        
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            task = Task(
                conversation_id=conversation_id,
                parent_task_id=parent_task_id,
                task_type=task_type,
                description=description,
                priority=priority,
                dependencies=dependencies,
                task_metadata=task_metadata
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"任务创建成功: {task.id} - {task.description}")
            return task
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"创建任务失败: {str(e)}")
            raise
    
    def get_tasks_by_conversation(self, conversation_id: int, 
                                status: Optional[str] = None,
                                task_type: Optional[str] = None) -> List[Task]:
        """
        获取会话的所有任务
        
        参数:
            conversation_id: 会话ID
            status: 任务状态过滤（可选）
            task_type: 任务类型过滤（可选）
        
        返回:
            List[Task]: 任务列表
        """
        try:
            query = select(Task).where(Task.conversation_id == conversation_id)
            
            if status:
                query = query.where(Task.status == status)
            
            if task_type:
                query = query.where(Task.task_type == task_type)
            
            query = query.order_by(desc(Task.priority), asc(Task.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取会话任务失败: {str(e)}")
            raise
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """
        根据ID获取任务
        
        参数:
            task_id: 任务ID
        
        返回:
            Optional[Task]: 任务对象，如果不存在则返回None
        """
        try:
            query = select(Task).where(Task.id == task_id)
            result = self.db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"获取任务失败: {str(e)}")
            raise
    
    def get_subtasks(self, parent_task_id: int) -> List[Task]:
        """
        获取子任务列表
        
        参数:
            parent_task_id: 父任务ID
        
        返回:
            List[Task]: 子任务列表
        """
        try:
            query = select(Task).where(Task.parent_task_id == parent_task_id)
            query = query.order_by(desc(Task.priority), asc(Task.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取子任务失败: {str(e)}")
            raise
    
    def update_task_status(self, task_id: int, status: str, 
                          result: Optional[str] = None,
                          error_message: Optional[str] = None) -> bool:
        """
        更新任务状态
        
        参数:
            task_id: 任务ID
            status: 新状态
            result: 执行结果（可选）
            error_message: 错误信息（可选）
        
        返回:
            bool: 更新是否成功
        """
        try:
            update_data = {"status": status}
            
            if result is not None:
                update_data["result"] = result
            
            if error_message is not None:
                update_data["error_message"] = error_message
                update_data["retry_count"] = Task.retry_count + 1
            
            if status == "running":
                from datetime import datetime
                update_data["started_at"] = datetime.utcnow()
            elif status in ["completed", "failed"]:
                from datetime import datetime
                update_data["completed_at"] = datetime.utcnow()
            
            query = update(Task).where(Task.id == task_id).values(**update_data)
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"任务状态更新成功: {task_id} -> {status}")
                return True
            else:
                logger.warning(f"任务不存在: {task_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"更新任务状态失败: {str(e)}")
            raise
    
    def get_pending_tasks(self, conversation_id: Optional[int] = None) -> List[Task]:
        """
        获取待执行的任务
        
        参数:
            conversation_id: 会话ID（可选，用于过滤特定会话）
        
        返回:
            List[Task]: 待执行任务列表
        """
        try:
            query = select(Task).where(Task.status == "pending")
            
            if conversation_id:
                query = query.where(Task.conversation_id == conversation_id)
            
            query = query.order_by(desc(Task.priority), asc(Task.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取待执行任务失败: {str(e)}")
            raise
    
    def get_running_tasks(self, conversation_id: Optional[int] = None) -> List[Task]:
        """
        获取正在运行的任务
        
        参数:
            conversation_id: 会话ID（可选，用于过滤特定会话）
        
        返回:
            List[Task]: 正在运行的任务列表
        """
        try:
            query = select(Task).where(Task.status == "running")
            
            if conversation_id:
                query = query.where(Task.conversation_id == conversation_id)
            
            query = query.order_by(desc(Task.priority), asc(Task.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取运行中任务失败: {str(e)}")
            raise
    
    def check_dependencies_completed(self, task_id: int) -> bool:
        """
        检查任务的依赖是否都已完成
        
        参数:
            task_id: 任务ID
        
        返回:
            bool: 依赖是否都已完成
        """
        try:
            task = self.get_task_by_id(task_id)
            if not task or not task.dependencies:
                return True
            
            # 检查所有依赖任务的状态
            query = select(Task).where(
                and_(
                    Task.id.in_(task.dependencies),
                    Task.status != "completed"
                )
            )
            
            result = self.db.execute(query)
            incomplete_deps = result.scalars().all()
            
            return len(incomplete_deps) == 0
            
        except SQLAlchemyError as e:
            logger.error(f"检查任务依赖失败: {str(e)}")
            raise
    
    def get_tasks_by_dependencies(self, dependency_ids: List[int]) -> List[Task]:
        """
        获取依赖指定任务的所有任务
        
        参数:
            dependency_ids: 依赖任务ID列表
        
        返回:
            List[Task]: 依赖这些任务的任务列表
        """
        try:
            # 使用 JSON_CONTAINS 查询依赖关系
            query = select(Task).where(
                or_(*[Task.dependencies.contains([dep_id]) for dep_id in dependency_ids])
            )
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取依赖任务失败: {str(e)}")
            raise
    
    def delete_task(self, task_id: int) -> bool:
        """
        删除任务（级联删除子任务）
        
        参数:
            task_id: 任务ID
        
        返回:
            bool: 删除是否成功
        """
        try:
            task = self.get_task_by_id(task_id)
            if not task:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            # 删除所有子任务
            subtasks = self.get_subtasks(task_id)
            for subtask in subtasks:
                self.delete_task(subtask.id)
            
            # 删除任务本身
            query = delete(Task).where(Task.id == task_id)
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"任务删除成功: {task_id}")
                return True
            else:
                logger.warning(f"任务删除失败: {task_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"删除任务失败: {str(e)}")
            raise
    
    def get_task_statistics(self, conversation_id: Optional[int] = None) -> Dict[str, int]:
        """
        获取任务统计信息
        
        参数:
            conversation_id: 会话ID（可选，用于过滤特定会话）
        
        返回:
            Dict[str, int]: 任务统计信息
        """
        try:
            query = select(Task)
            
            if conversation_id:
                query = query.where(Task.conversation_id == conversation_id)
            
            result = self.db.execute(query)
            tasks = result.scalars().all()
            
            stats = {
                "total": len(tasks),
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for task in tasks:
                if task.status in stats:
                    stats[task.status] += 1
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"获取任务统计失败: {str(e)}")
            raise
    
    def get_tasks_by_conversation_simple(self, conversation_id: int) -> List[Task]:
        """
        获取会话的所有任务（简化版本，用于兼容性）
        
        参数:
            conversation_id: 会话ID
        
        返回:
            List[Task]: 任务列表
        """
        return self.get_tasks_by_conversation(conversation_id)
