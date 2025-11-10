"""
文件名: knowledge_dao.py
功能: 知识图谱相关的数据访问对象
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, update, delete, and_, or_, desc, asc, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.dao.base import BaseDAO
from app.models.knowledge import KnowledgeGraph, KnowledgeRelation
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeDAO(BaseDAO[KnowledgeGraph]):
    """
    知识图谱数据访问对象
    
    功能：
    - 知识实体的 CRUD 操作
    - 知识关系的管理
    - 知识图谱查询和遍历
    - 知识实体搜索
    """
    
    def __init__(self, db: Session):
        super().__init__(KnowledgeGraph, db)
        self.db = db
    
    # ==================== 知识实体操作 ====================
    
    def create_entity(self,
                     user_id: int,
                     entity_type: str,
                     entity_name: str,
                     properties: Optional[Dict[str, Any]] = None) -> KnowledgeGraph:
        """
        创建知识实体
        
        参数:
            user_id: 用户ID
            entity_type: 实体类型
            entity_name: 实体名称
            properties: 实体属性
        
        返回:
            KnowledgeGraph: 创建的知识实体对象
        
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            entity = KnowledgeGraph(
                user_id=user_id,
                entity_type=entity_type,
                entity_name=entity_name,
                properties=properties
            )
            
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            
            logger.info(f"知识实体创建成功: {entity.id} - {entity.entity_name}")
            return entity
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"创建知识实体失败: {str(e)}")
            raise
    
    def get_entity_by_id(self, entity_id: int) -> Optional[KnowledgeGraph]:
        """
        根据ID获取知识实体
        
        参数:
            entity_id: 实体ID
        
        返回:
            Optional[KnowledgeGraph]: 知识实体对象，如果不存在则返回None
        """
        try:
            query = select(KnowledgeGraph).where(KnowledgeGraph.id == entity_id)
            result = self.db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"获取知识实体失败: {str(e)}")
            raise
    
    def get_entities_by_user(self, 
                           user_id: int,
                           entity_type: Optional[str] = None,
                           limit: Optional[int] = None) -> List[KnowledgeGraph]:
        """
        获取用户的所有知识实体
        
        参数:
            user_id: 用户ID
            entity_type: 实体类型过滤（可选）
            limit: 限制返回数量
        
        返回:
            List[KnowledgeGraph]: 知识实体列表
        """
        try:
            query = select(KnowledgeGraph).where(KnowledgeGraph.user_id == user_id)
            
            if entity_type:
                query = query.where(KnowledgeGraph.entity_type == entity_type)
            
            query = query.order_by(desc(KnowledgeGraph.created_at))
            
            if limit:
                query = query.limit(limit)
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取用户知识实体失败: {str(e)}")
            raise
    
    def search_entities(self, 
                       user_id: int,
                       search_text: str,
                       entity_type: Optional[str] = None,
                       limit: Optional[int] = None) -> List[KnowledgeGraph]:
        """
        搜索知识实体
        
        参数:
            user_id: 用户ID
            search_text: 搜索文本
            entity_type: 实体类型过滤（可选）
            limit: 限制返回数量
        
        返回:
            List[KnowledgeGraph]: 匹配的知识实体列表
        """
        try:
            query = select(KnowledgeGraph).where(
                and_(
                    KnowledgeGraph.user_id == user_id,
                    KnowledgeGraph.entity_name.contains(search_text)
                )
            )
            
            if entity_type:
                query = query.where(KnowledgeGraph.entity_type == entity_type)
            
            query = query.order_by(desc(KnowledgeGraph.created_at))
            
            if limit:
                query = query.limit(limit)
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"搜索知识实体失败: {str(e)}")
            raise
    
    def update_entity_properties(self, 
                               entity_id: int, 
                               properties: Dict[str, Any]) -> bool:
        """
        更新实体属性
        
        参数:
            entity_id: 实体ID
            properties: 新的属性字典
        
        返回:
            bool: 更新是否成功
        """
        try:
            query = update(KnowledgeGraph).where(KnowledgeGraph.id == entity_id).values(
                properties=properties
            )
            
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"实体属性更新成功: {entity_id}")
                return True
            else:
                logger.warning(f"实体不存在: {entity_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"更新实体属性失败: {str(e)}")
            raise
    
    def delete_entity(self, entity_id: int) -> bool:
        """
        删除知识实体（级联删除相关关系）
        
        参数:
            entity_id: 实体ID
        
        返回:
            bool: 删除是否成功
        """
        try:
            # 先删除相关关系
            self.delete_relations_by_entity(entity_id)
            
            # 删除实体
            query = delete(KnowledgeGraph).where(KnowledgeGraph.id == entity_id)
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"知识实体删除成功: {entity_id}")
                return True
            else:
                logger.warning(f"知识实体不存在: {entity_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"删除知识实体失败: {str(e)}")
            raise
    
    # ==================== 知识关系操作 ====================
    
    def create_relation(self,
                       from_entity_id: int,
                       to_entity_id: int,
                       relation_type: str,
                       weight: float = 1.0,
                       properties: Optional[Dict[str, Any]] = None) -> KnowledgeRelation:
        """
        创建知识关系
        
        参数:
            from_entity_id: 起始实体ID
            to_entity_id: 目标实体ID
            relation_type: 关系类型
            weight: 关系权重
            properties: 关系属性
        
        返回:
            KnowledgeRelation: 创建的知识关系对象
        
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            relation = KnowledgeRelation(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relation_type=relation_type,
                weight=weight,
                properties=properties
            )
            
            self.db.add(relation)
            self.db.commit()
            self.db.refresh(relation)
            
            logger.info(f"知识关系创建成功: {relation.id} - {relation_type}")
            return relation
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"创建知识关系失败: {str(e)}")
            raise
    
    def get_relations_by_entity(self, entity_id: int) -> List[KnowledgeRelation]:
        """
        获取实体的所有关系
        
        参数:
            entity_id: 实体ID
        
        返回:
            List[KnowledgeRelation]: 关系列表
        """
        try:
            query = select(KnowledgeRelation).where(
                or_(
                    KnowledgeRelation.from_entity_id == entity_id,
                    KnowledgeRelation.to_entity_id == entity_id
                )
            )
            
            query = query.order_by(desc(KnowledgeRelation.weight), desc(KnowledgeRelation.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取实体关系失败: {str(e)}")
            raise
    
    def get_relations_by_type(self, 
                            relation_type: str,
                            user_id: Optional[int] = None,
                            limit: Optional[int] = None) -> List[KnowledgeRelation]:
        """
        根据关系类型获取关系
        
        参数:
            relation_type: 关系类型
            user_id: 用户ID（可选，用于过滤特定用户）
            limit: 限制返回数量
        
        返回:
            List[KnowledgeRelation]: 关系列表
        """
        try:
            query = select(KnowledgeRelation).where(KnowledgeRelation.relation_type == relation_type)
            
            if user_id:
                # 通过 JOIN 过滤用户
                query = query.join(KnowledgeGraph, 
                                 KnowledgeRelation.from_entity_id == KnowledgeGraph.id)
                query = query.where(KnowledgeGraph.user_id == user_id)
            
            query = query.order_by(desc(KnowledgeRelation.weight), desc(KnowledgeRelation.created_at))
            
            if limit:
                query = query.limit(limit)
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取类型关系失败: {str(e)}")
            raise
    
    def get_related_entities(self, 
                           entity_id: int,
                           relation_type: Optional[str] = None,
                           direction: str = "both") -> List[KnowledgeGraph]:
        """
        获取相关实体
        
        参数:
            entity_id: 实体ID
            relation_type: 关系类型过滤（可选）
            direction: 关系方向 ("in", "out", "both")
        
        返回:
            List[KnowledgeGraph]: 相关实体列表
        """
        try:
            if direction == "out":
                # 只获取出边关系
                query = select(KnowledgeGraph).join(
                    KnowledgeRelation, 
                    KnowledgeRelation.to_entity_id == KnowledgeGraph.id
                ).where(KnowledgeRelation.from_entity_id == entity_id)
            elif direction == "in":
                # 只获取入边关系
                query = select(KnowledgeGraph).join(
                    KnowledgeRelation, 
                    KnowledgeRelation.from_entity_id == KnowledgeGraph.id
                ).where(KnowledgeRelation.to_entity_id == entity_id)
            else:
                # 获取双向关系
                query = select(KnowledgeGraph).join(
                    KnowledgeRelation, 
                    or_(
                        KnowledgeRelation.to_entity_id == KnowledgeGraph.id,
                        KnowledgeRelation.from_entity_id == KnowledgeGraph.id
                    )
                ).where(
                    or_(
                        KnowledgeRelation.from_entity_id == entity_id,
                        KnowledgeRelation.to_entity_id == entity_id
                    )
                )
            
            if relation_type:
                query = query.where(KnowledgeRelation.relation_type == relation_type)
            
            query = query.order_by(desc(KnowledgeRelation.weight), desc(KnowledgeGraph.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取相关实体失败: {str(e)}")
            raise
    
    def update_relation_weight(self, relation_id: int, weight: float) -> bool:
        """
        更新关系权重
        
        参数:
            relation_id: 关系ID
            weight: 新的权重
        
        返回:
            bool: 更新是否成功
        """
        try:
            if not 0.0 <= weight <= 1.0:
                raise ValueError("关系权重必须在 0.0 到 1.0 之间")
            
            query = update(KnowledgeRelation).where(KnowledgeRelation.id == relation_id).values(
                weight=weight
            )
            
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"关系权重更新成功: {relation_id} -> {weight}")
                return True
            else:
                logger.warning(f"关系不存在: {relation_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"更新关系权重失败: {str(e)}")
            raise
    
    def delete_relation(self, relation_id: int) -> bool:
        """
        删除知识关系
        
        参数:
            relation_id: 关系ID
        
        返回:
            bool: 删除是否成功
        """
        try:
            query = delete(KnowledgeRelation).where(KnowledgeRelation.id == relation_id)
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"知识关系删除成功: {relation_id}")
                return True
            else:
                logger.warning(f"知识关系不存在: {relation_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"删除知识关系失败: {str(e)}")
            raise
    
    def delete_relations_by_entity(self, entity_id: int) -> int:
        """
        删除实体的所有关系
        
        参数:
            entity_id: 实体ID
        
        返回:
            int: 删除的关系数量
        """
        try:
            query = delete(KnowledgeRelation).where(
                or_(
                    KnowledgeRelation.from_entity_id == entity_id,
                    KnowledgeRelation.to_entity_id == entity_id
                )
            )
            
            result = self.db.execute(query)
            self.db.commit()
            
            deleted_count = result.rowcount
            logger.info(f"实体关系删除完成: {entity_id} - {deleted_count} 条")
            return deleted_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"删除实体关系失败: {str(e)}")
            raise
    
    # ==================== 统计和查询 ====================
    
    def get_knowledge_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        获取知识图谱统计信息
        
        参数:
            user_id: 用户ID
        
        返回:
            Dict[str, Any]: 统计信息
        """
        try:
            # 实体统计
            entity_query = select(KnowledgeGraph).where(KnowledgeGraph.user_id == user_id)
            entity_result = self.db.execute(entity_query)
            entities = entity_result.scalars().all()
            
            # 关系统计
            relation_query = select(KnowledgeRelation).join(
                KnowledgeGraph, 
                KnowledgeRelation.from_entity_id == KnowledgeGraph.id
            ).where(KnowledgeGraph.user_id == user_id)
            relation_result = self.db.execute(relation_query)
            relations = relation_result.scalars().all()
            
            stats = {
                "total_entities": len(entities),
                "total_relations": len(relations),
                "entities_by_type": {},
                "relations_by_type": {},
                "avg_relation_weight": 0.0
            }
            
            # 按类型统计实体
            for entity in entities:
                if entity.entity_type not in stats["entities_by_type"]:
                    stats["entities_by_type"][entity.entity_type] = 0
                stats["entities_by_type"][entity.entity_type] += 1
            
            # 按类型统计关系
            total_weight = 0.0
            for relation in relations:
                if relation.relation_type not in stats["relations_by_type"]:
                    stats["relations_by_type"][relation.relation_type] = 0
                stats["relations_by_type"][relation.relation_type] += 1
                total_weight += relation.weight
            
            # 计算平均关系权重
            if len(relations) > 0:
                stats["avg_relation_weight"] = total_weight / len(relations)
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"获取知识图谱统计失败: {str(e)}")
            raise
    
    def find_entity_path(self, 
                        from_entity_id: int, 
                        to_entity_id: int,
                        max_depth: int = 3) -> List[List[int]]:
        """
        查找实体间的路径（简单实现，实际应用中可能需要更复杂的图算法）
        
        参数:
            from_entity_id: 起始实体ID
            to_entity_id: 目标实体ID
            max_depth: 最大搜索深度
        
        返回:
            List[List[int]]: 路径列表，每个路径是实体ID的列表
        """
        try:
            # 这是一个简化的实现，实际应用中可能需要使用图算法库
            # 这里只实现深度为1的直接关系查找
            
            if max_depth < 1:
                return []
            
            paths = []
            
            # 查找直接关系
            query = select(KnowledgeRelation).where(
                and_(
                    KnowledgeRelation.from_entity_id == from_entity_id,
                    KnowledgeRelation.to_entity_id == to_entity_id
                )
            )
            
            result = self.db.execute(query)
            direct_relations = result.scalars().all()
            
            if direct_relations:
                paths.append([from_entity_id, to_entity_id])
            
            # 查找反向关系
            query = select(KnowledgeRelation).where(
                and_(
                    KnowledgeRelation.from_entity_id == to_entity_id,
                    KnowledgeRelation.to_entity_id == from_entity_id
                )
            )
            
            result = self.db.execute(query)
            reverse_relations = result.scalars().all()
            
            if reverse_relations:
                paths.append([from_entity_id, to_entity_id])
            
            return paths
            
        except SQLAlchemyError as e:
            logger.error(f"查找实体路径失败: {str(e)}")
            raise
