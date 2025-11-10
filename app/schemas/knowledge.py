"""
文件名: knowledge.py
功能: 知识图谱相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


# ==================== 知识实体模型 ====================

class KnowledgeEntityBase(BaseModel):
    """知识实体基础模型"""
    entity_type: str = Field(..., description="实体类型：person/product/order/concept")
    entity_name: str = Field(..., description="实体名称")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="实体属性")


class KnowledgeEntityCreate(KnowledgeEntityBase):
    """创建知识实体模型"""
    user_id: int = Field(..., description="用户ID")


class KnowledgeEntityUpdate(BaseModel):
    """更新知识实体模型"""
    entity_type: Optional[str] = Field(default=None, description="实体类型")
    entity_name: Optional[str] = Field(default=None, description="实体名称")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="实体属性")


class KnowledgeEntityResponse(KnowledgeEntityBase):
    """知识实体响应模型"""
    id: int = Field(..., description="实体ID")
    user_id: int = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class KnowledgeEntityListResponse(BaseModel):
    """知识实体列表响应模型"""
    entities: List[KnowledgeEntityResponse] = Field(..., description="实体列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


# ==================== 知识关系模型 ====================

class KnowledgeRelationBase(BaseModel):
    """知识关系基础模型"""
    relation_type: str = Field(..., description="关系类型：owns/likes/related_to/depends_on")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="关系权重（0-1）")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="关系属性")


class KnowledgeRelationCreate(KnowledgeRelationBase):
    """创建知识关系模型"""
    from_entity_id: int = Field(..., description="起始实体ID")
    to_entity_id: int = Field(..., description="目标实体ID")


class KnowledgeRelationUpdate(BaseModel):
    """更新知识关系模型"""
    relation_type: Optional[str] = Field(default=None, description="关系类型")
    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="关系权重")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="关系属性")


class KnowledgeRelationResponse(KnowledgeRelationBase):
    """知识关系响应模型"""
    id: int = Field(..., description="关系ID")
    from_entity_id: int = Field(..., description="起始实体ID")
    to_entity_id: int = Field(..., description="目标实体ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class KnowledgeRelationListResponse(BaseModel):
    """知识关系列表响应模型"""
    relations: List[KnowledgeRelationResponse] = Field(..., description="关系列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


# ==================== 查询模型 ====================

class KnowledgeEntityQuery(BaseModel):
    """知识实体查询模型"""
    user_id: int = Field(..., description="用户ID")
    entity_type: Optional[str] = Field(default=None, description="实体类型")
    search_text: Optional[str] = Field(default=None, description="搜索文本")
    created_after: Optional[datetime] = Field(default=None, description="创建时间之后")
    created_before: Optional[datetime] = Field(default=None, description="创建时间之前")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="created_at", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序排列")


class KnowledgeRelationQuery(BaseModel):
    """知识关系查询模型"""
    user_id: int = Field(..., description="用户ID")
    relation_type: Optional[str] = Field(default=None, description="关系类型")
    from_entity_id: Optional[int] = Field(default=None, description="起始实体ID")
    to_entity_id: Optional[int] = Field(default=None, description="目标实体ID")
    weight_min: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="最小权重")
    weight_max: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="最大权重")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="weight", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序排列")
    
    @validator('weight_max')
    def validate_weight_range(cls, v, values):
        if v is not None and 'weight_min' in values and values['weight_min'] is not None:
            if v < values['weight_min']:
                raise ValueError('最大权重不能小于最小权重')
        return v


# ==================== 统计模型 ====================

class KnowledgeStatistics(BaseModel):
    """知识图谱统计模型"""
    total_entities: int = Field(..., description="总实体数")
    total_relations: int = Field(..., description="总关系数")
    entities_by_type: Dict[str, int] = Field(..., description="按类型统计实体")
    relations_by_type: Dict[str, int] = Field(..., description="按类型统计关系")
    avg_relation_weight: float = Field(..., description="平均关系权重")


class KnowledgeTypeStatistics(BaseModel):
    """知识类型统计模型"""
    entity_type: str = Field(..., description="实体类型")
    entity_count: int = Field(..., description="实体数量")
    relation_count: int = Field(..., description="关系数量")
    avg_weight: float = Field(..., description="平均权重")


# ==================== 知识图谱结构模型 ====================

class KnowledgeGraphNode(KnowledgeEntityResponse):
    """知识图谱节点模型"""
    relations: List[KnowledgeRelationResponse] = Field(default_factory=list, description="关系列表")
    degree: int = Field(default=0, description="节点度数")
    centrality_score: float = Field(default=0.0, description="中心性评分")


class KnowledgeGraphEdge(KnowledgeRelationResponse):
    """知识图谱边模型"""
    from_entity: KnowledgeEntityResponse = Field(..., description="起始实体")
    to_entity: KnowledgeEntityResponse = Field(..., description="目标实体")


class KnowledgeGraphStructure(BaseModel):
    """知识图谱结构模型"""
    nodes: List[KnowledgeGraphNode] = Field(..., description="节点列表")
    edges: List[KnowledgeGraphEdge] = Field(..., description="边列表")
    total_nodes: int = Field(..., description="总节点数")
    total_edges: int = Field(..., description="总边数")
    density: float = Field(..., description="图密度")
    components: int = Field(..., description="连通分量数")


# ==================== 知识检索模型 ====================

class KnowledgeSearch(BaseModel):
    """知识搜索模型"""
    query: str = Field(..., description="搜索查询")
    entity_types: Optional[List[str]] = Field(default=None, description="实体类型过滤")
    relation_types: Optional[List[str]] = Field(default=None, description="关系类型过滤")
    weight_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="权重阈值")
    max_results: int = Field(default=20, ge=1, le=100, description="最大结果数")
    include_relations: bool = Field(default=True, description="是否包含关系")


class KnowledgeSearchResult(BaseModel):
    """知识搜索结果模型"""
    entity: KnowledgeEntityResponse = Field(..., description="实体对象")
    relevance_score: float = Field(..., description="相关性评分")
    matched_relations: List[KnowledgeRelationResponse] = Field(
        default_factory=list, description="匹配的关系列表"
    )


class KnowledgeSearchResponse(BaseModel):
    """知识搜索响应模型"""
    results: List[KnowledgeSearchResult] = Field(..., description="搜索结果列表")
    total_found: int = Field(..., description="找到的总数")
    query: str = Field(..., description="搜索查询")
    search_time: float = Field(..., description="搜索耗时（秒）")


# ==================== 知识路径模型 ====================

class KnowledgePath(BaseModel):
    """知识路径模型"""
    path: List[int] = Field(..., description="路径中的实体ID列表")
    relations: List[KnowledgeRelationResponse] = Field(..., description="路径中的关系列表")
    total_weight: float = Field(..., description="路径总权重")
    path_length: int = Field(..., description="路径长度")


class KnowledgePathSearch(BaseModel):
    """知识路径搜索模型"""
    from_entity_id: int = Field(..., description="起始实体ID")
    to_entity_id: int = Field(..., description="目标实体ID")
    max_depth: int = Field(default=3, ge=1, le=10, description="最大搜索深度")
    relation_types: Optional[List[str]] = Field(default=None, description="关系类型过滤")
    weight_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="权重阈值")


class KnowledgePathResponse(BaseModel):
    """知识路径响应模型"""
    paths: List[KnowledgePath] = Field(..., description="路径列表")
    shortest_path: Optional[KnowledgePath] = Field(default=None, description="最短路径")
    total_paths: int = Field(..., description="总路径数")
    search_time: float = Field(..., description="搜索耗时（秒）")


# ==================== 知识推荐模型 ====================

class KnowledgeRecommendation(BaseModel):
    """知识推荐模型"""
    target_entity_id: int = Field(..., description="目标实体ID")
    recommendation_type: Literal["similar", "related", "popular"] = Field(
        ..., description="推荐类型"
    )
    max_results: int = Field(default=10, ge=1, le=50, description="最大推荐数")
    weight_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="权重阈值")


class KnowledgeRecommendationResult(BaseModel):
    """知识推荐结果模型"""
    entity: KnowledgeEntityResponse = Field(..., description="推荐实体")
    recommendation_score: float = Field(..., description="推荐评分")
    reason: str = Field(..., description="推荐理由")
    common_relations: List[KnowledgeRelationResponse] = Field(
        default_factory=list, description="共同关系列表"
    )


class KnowledgeRecommendationResponse(BaseModel):
    """知识推荐响应模型"""
    recommendations: List[KnowledgeRecommendationResult] = Field(..., description="推荐列表")
    target_entity: KnowledgeEntityResponse = Field(..., description="目标实体")
    recommendation_type: str = Field(..., description="推荐类型")
    total_recommendations: int = Field(..., description="总推荐数")


# ==================== 批量操作模型 ====================

class KnowledgeBatchCreate(BaseModel):
    """批量创建知识模型"""
    entities: List[KnowledgeEntityCreate] = Field(..., description="实体列表")
    relations: List[KnowledgeRelationCreate] = Field(default_factory=list, description="关系列表")


class KnowledgeBatchUpdate(BaseModel):
    """批量更新知识模型"""
    entity_updates: List[Dict[str, Any]] = Field(default_factory=list, description="实体更新列表")
    relation_updates: List[Dict[str, Any]] = Field(default_factory=list, description="关系更新列表")


class KnowledgeBatchDelete(BaseModel):
    """批量删除知识模型"""
    entity_ids: List[int] = Field(default_factory=list, description="实体ID列表")
    relation_ids: List[int] = Field(default_factory=list, description="关系ID列表")
    cascade: bool = Field(default=True, description="是否级联删除")


# ==================== 知识导入导出模型 ====================

class KnowledgeExport(BaseModel):
    """知识导出模型"""
    user_id: int = Field(..., description="用户ID")
    entity_types: Optional[List[str]] = Field(default=None, description="要导出的实体类型")
    relation_types: Optional[List[str]] = Field(default=None, description="要导出的关系类型")
    include_properties: bool = Field(default=True, description="是否包含属性")
    format: Literal["json", "csv", "graphml", "gexf"] = Field(default="json", description="导出格式")


class KnowledgeImport(BaseModel):
    """知识导入模型"""
    user_id: int = Field(..., description="目标用户ID")
    data: str = Field(..., description="导入数据")
    format: Literal["json", "csv", "graphml", "gexf"] = Field(default="json", description="数据格式")
    overwrite_existing: bool = Field(default=False, description="是否覆盖现有知识")
    validate_relations: bool = Field(default=True, description="是否验证关系")


class KnowledgeExportResult(BaseModel):
    """知识导出结果模型"""
    exported_entities: int = Field(..., description="导出的实体数量")
    exported_relations: int = Field(..., description="导出的关系数量")
    export_data: str = Field(..., description="导出数据")
    export_time: datetime = Field(..., description="导出时间")
    file_size: int = Field(..., description="文件大小（字节）")


class KnowledgeImportResult(BaseModel):
    """知识导入结果模型"""
    imported_entities: int = Field(..., description="导入的实体数量")
    imported_relations: int = Field(..., description="导入的关系数量")
    skipped_entities: int = Field(..., description="跳过的实体数量")
    skipped_relations: int = Field(..., description="跳过的关系数量")
    error_entities: int = Field(..., description="错误的实体数量")
    error_relations: int = Field(..., description="错误的关系数量")
    import_time: datetime = Field(..., description="导入时间")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误列表")


# ==================== 知识分析模型 ====================

class KnowledgeAnalysis(BaseModel):
    """知识分析模型"""
    user_id: int = Field(..., description="用户ID")
    analysis_type: Literal["structure", "centrality", "community", "evolution"] = Field(
        ..., description="分析类型"
    )


class KnowledgeStructureAnalysis(BaseModel):
    """知识结构分析模型"""
    total_entities: int = Field(..., description="总实体数")
    total_relations: int = Field(..., description="总关系数")
    density: float = Field(..., description="图密度")
    components: int = Field(..., description="连通分量数")
    diameter: Optional[float] = Field(default=None, description="图直径")
    clustering_coefficient: float = Field(..., description="聚类系数")


class KnowledgeCentralityAnalysis(BaseModel):
    """知识中心性分析模型"""
    degree_centrality: Dict[int, float] = Field(..., description="度中心性")
    betweenness_centrality: Dict[int, float] = Field(..., description="介数中心性")
    closeness_centrality: Dict[int, float] = Field(..., description="接近中心性")
    most_central_entities: List[KnowledgeEntityResponse] = Field(..., description="最中心实体")


class KnowledgeCommunityAnalysis(BaseModel):
    """知识社区分析模型"""
    communities: List[List[int]] = Field(..., description="社区列表")
    modularity: float = Field(..., description="模块度")
    community_count: int = Field(..., description="社区数量")
    largest_community_size: int = Field(..., description="最大社区大小")


class KnowledgeEvolutionAnalysis(BaseModel):
    """知识演化分析模型"""
    entity_growth: List[Dict[str, Any]] = Field(..., description="实体增长趋势")
    relation_growth: List[Dict[str, Any]] = Field(..., description="关系增长趋势")
    type_distribution_evolution: Dict[str, List[Dict[str, Any]]] = Field(
        ..., description="类型分布演化"
    )
    activity_periods: List[Dict[str, Any]] = Field(..., description="活跃期分析")
