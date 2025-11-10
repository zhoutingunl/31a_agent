"""
文件名: memory.py
功能: 记忆管理相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


# ==================== 基础模型 ====================

class MemoryBase(BaseModel):
    """记忆基础模型"""
    memory_type: Literal["short_term", "long_term", "episodic", "semantic"] = Field(
        ..., description="记忆类型"
    )
    content: str = Field(..., description="记忆内容")
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="重要性评分（0-1）")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class MemoryCreate(MemoryBase):
    """创建记忆模型"""
    conversation_id: int = Field(..., description="会话ID")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class MemoryUpdate(BaseModel):
    """更新记忆模型"""
    content: Optional[str] = Field(default=None, description="记忆内容")
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="重要性评分")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class MemoryResponse(MemoryBase):
    """记忆响应模型"""
    id: int = Field(..., description="记忆ID")
    conversation_id: int = Field(..., description="会话ID")
    access_count: int = Field(default=0, description="访问次数")
    last_accessed_at: Optional[datetime] = Field(default=None, description="最后访问时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """记忆列表响应模型"""
    memories: List[MemoryResponse] = Field(..., description="记忆列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


# ==================== 查询模型 ====================

class MemoryQuery(BaseModel):
    """记忆查询模型"""
    conversation_id: Optional[int] = Field(default=None, description="会话ID")
    memory_type: Optional[str] = Field(default=None, description="记忆类型")
    importance_min: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="最小重要性评分")
    importance_max: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="最大重要性评分")
    include_expired: bool = Field(default=False, description="是否包含过期记忆")
    search_text: Optional[str] = Field(default=None, description="搜索文本")
    created_after: Optional[datetime] = Field(default=None, description="创建时间之后")
    created_before: Optional[datetime] = Field(default=None, description="创建时间之前")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="importance_score", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序排列")
    
    @validator('importance_max')
    def validate_importance_range(cls, v, values):
        if v is not None and 'importance_min' in values and values['importance_min'] is not None:
            if v < values['importance_min']:
                raise ValueError('最大重要性评分不能小于最小重要性评分')
        return v


# ==================== 统计模型 ====================

class MemoryStatistics(BaseModel):
    """记忆统计模型"""
    total: int = Field(..., description="总记忆数")
    by_type: Dict[str, int] = Field(..., description="按类型统计")
    by_importance: Dict[str, int] = Field(..., description="按重要性统计")
    expired: int = Field(..., description="过期记忆数")
    total_access_count: int = Field(..., description="总访问次数")
    avg_importance: float = Field(..., description="平均重要性评分")


class MemoryTypeStatistics(BaseModel):
    """记忆类型统计模型"""
    memory_type: str = Field(..., description="记忆类型")
    count: int = Field(..., description="数量")
    avg_importance: float = Field(..., description="平均重要性评分")
    total_access_count: int = Field(..., description="总访问次数")
    expired_count: int = Field(..., description="过期数量")


# ==================== 记忆检索模型 ====================

class MemoryRetrieval(BaseModel):
    """记忆检索模型"""
    query: str = Field(..., description="检索查询")
    memory_types: Optional[List[str]] = Field(default=None, description="记忆类型过滤")
    importance_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="重要性阈值")
    max_results: int = Field(default=10, ge=1, le=100, description="最大结果数")
    include_metadata: bool = Field(default=True, description="是否包含元数据")


class MemoryRetrievalResult(BaseModel):
    """记忆检索结果模型"""
    memory: MemoryResponse = Field(..., description="记忆对象")
    relevance_score: float = Field(..., description="相关性评分")
    match_type: str = Field(..., description="匹配类型：exact/partial/semantic")


class MemoryRetrievalResponse(BaseModel):
    """记忆检索响应模型"""
    results: List[MemoryRetrievalResult] = Field(..., description="检索结果列表")
    total_found: int = Field(..., description="找到的总数")
    query: str = Field(..., description="检索查询")
    search_time: float = Field(..., description="搜索耗时（秒）")


# ==================== 记忆压缩模型 ====================

class MemoryCompression(BaseModel):
    """记忆压缩模型"""
    target_size: int = Field(..., description="目标记忆数量")
    compression_strategy: Literal["importance", "recency", "access_frequency", "hybrid"] = Field(
        default="hybrid", description="压缩策略"
    )
    preserve_important: bool = Field(default=True, description="是否保留重要记忆")
    preserve_recent: bool = Field(default=True, description="是否保留最近记忆")
    min_importance_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="最小重要性阈值")


class MemoryCompressionResult(BaseModel):
    """记忆压缩结果模型"""
    original_count: int = Field(..., description="原始记忆数量")
    compressed_count: int = Field(..., description="压缩后记忆数量")
    removed_count: int = Field(..., description="删除的记忆数量")
    removed_memories: List[MemoryResponse] = Field(..., description="被删除的记忆列表")
    compression_ratio: float = Field(..., description="压缩比例")


# ==================== 记忆同步模型 ====================

class MemorySync(BaseModel):
    """记忆同步模型"""
    source_conversation_id: int = Field(..., description="源会话ID")
    target_conversation_id: int = Field(..., description="目标会话ID")
    memory_types: Optional[List[str]] = Field(default=None, description="要同步的记忆类型")
    importance_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="重要性阈值")
    sync_metadata: bool = Field(default=True, description="是否同步元数据")


class MemorySyncResult(BaseModel):
    """记忆同步结果模型"""
    synced_count: int = Field(..., description="同步的记忆数量")
    skipped_count: int = Field(..., description="跳过的记忆数量")
    synced_memories: List[MemoryResponse] = Field(..., description="同步的记忆列表")
    sync_time: datetime = Field(..., description="同步时间")


# ==================== 记忆分析模型 ====================

class MemoryAnalysis(BaseModel):
    """记忆分析模型"""
    conversation_id: int = Field(..., description="会话ID")
    analysis_type: Literal["content", "temporal", "importance", "access_pattern"] = Field(
        ..., description="分析类型"
    )
    time_range: Optional[Dict[str, datetime]] = Field(default=None, description="时间范围")


class MemoryContentAnalysis(BaseModel):
    """记忆内容分析模型"""
    total_memories: int = Field(..., description="总记忆数")
    content_length_stats: Dict[str, float] = Field(..., description="内容长度统计")
    common_keywords: List[Dict[str, Any]] = Field(..., description="常见关键词")
    content_categories: Dict[str, int] = Field(..., description="内容分类统计")


class MemoryTemporalAnalysis(BaseModel):
    """记忆时间分析模型"""
    total_memories: int = Field(..., description="总记忆数")
    creation_timeline: List[Dict[str, Any]] = Field(..., description="创建时间线")
    access_timeline: List[Dict[str, Any]] = Field(..., description="访问时间线")
    peak_activity_periods: List[Dict[str, Any]] = Field(..., description="活跃高峰期")


class MemoryImportanceAnalysis(BaseModel):
    """记忆重要性分析模型"""
    total_memories: int = Field(..., description="总记忆数")
    importance_distribution: Dict[str, int] = Field(..., description="重要性分布")
    high_importance_memories: List[MemoryResponse] = Field(..., description="高重要性记忆")
    importance_trends: List[Dict[str, Any]] = Field(..., description="重要性趋势")


class MemoryAccessAnalysis(BaseModel):
    """记忆访问分析模型"""
    total_memories: int = Field(..., description="总记忆数")
    total_access_count: int = Field(..., description="总访问次数")
    most_accessed_memories: List[MemoryResponse] = Field(..., description="最常访问的记忆")
    access_patterns: Dict[str, Any] = Field(..., description="访问模式")
    access_frequency_stats: Dict[str, float] = Field(..., description="访问频率统计")


# ==================== 批量操作模型 ====================

class MemoryBatchCreate(BaseModel):
    """批量创建记忆模型"""
    memories: List[MemoryCreate] = Field(..., description="记忆列表")


class MemoryBatchUpdate(BaseModel):
    """批量更新记忆模型"""
    memory_ids: List[int] = Field(..., description="记忆ID列表")
    updates: MemoryUpdate = Field(..., description="更新内容")


class MemoryBatchDelete(BaseModel):
    """批量删除记忆模型"""
    memory_ids: List[int] = Field(..., description="记忆ID列表")
    force_delete: bool = Field(default=False, description="是否强制删除重要记忆")


# ==================== 记忆导出导入模型 ====================

class MemoryExport(BaseModel):
    """记忆导出模型"""
    conversation_id: int = Field(..., description="会话ID")
    memory_types: Optional[List[str]] = Field(default=None, description="要导出的记忆类型")
    include_metadata: bool = Field(default=True, description="是否包含元数据")
    format: Literal["json", "csv", "txt"] = Field(default="json", description="导出格式")


class MemoryImport(BaseModel):
    """记忆导入模型"""
    conversation_id: int = Field(..., description="目标会话ID")
    data: str = Field(..., description="导入数据")
    format: Literal["json", "csv", "txt"] = Field(default="json", description="数据格式")
    overwrite_existing: bool = Field(default=False, description="是否覆盖现有记忆")


class MemoryExportResult(BaseModel):
    """记忆导出结果模型"""
    exported_count: int = Field(..., description="导出的记忆数量")
    export_data: str = Field(..., description="导出数据")
    export_time: datetime = Field(..., description="导出时间")
    file_size: int = Field(..., description="文件大小（字节）")


class MemoryImportResult(BaseModel):
    """记忆导入结果模型"""
    imported_count: int = Field(..., description="导入的记忆数量")
    skipped_count: int = Field(..., description="跳过的记忆数量")
    error_count: int = Field(..., description="错误的记忆数量")
    import_time: datetime = Field(..., description="导入时间")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误列表")
