-- =============================================
-- 智能体系统数据库表创建脚本
-- 版本: 001
-- 创建时间: 2025-10-19
-- 功能: 创建任务管理、记忆存储、知识图谱相关表
-- =============================================

-- 1. 任务表 (task)
-- 功能: 存储智能体的任务分解与执行信息
CREATE TABLE IF NOT EXISTS `task` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID',
    `conversation_id` BIGINT NOT NULL COMMENT '会话ID',
    `parent_task_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '父任务ID（自引用）',
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型：plan/execute/reflect/tool_call',
    `description` TEXT NOT NULL COMMENT '任务描述',
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态：pending/running/completed/failed/cancelled',
    `priority` INT DEFAULT 0 COMMENT '优先级（数值越大优先级越高）',
    `dependencies` JSON DEFAULT NULL COMMENT '依赖任务ID列表 [1, 2, 3]',
    `result` TEXT DEFAULT NULL COMMENT '执行结果',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息（失败时）',
    `retry_count` INT DEFAULT 0 COMMENT '重试次数',
    `metadata` JSON DEFAULT NULL COMMENT '元数据（工具参数、执行上下文等）',
    `started_at` DATETIME DEFAULT NULL COMMENT '开始执行时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_conversation_id` (`conversation_id`),
    KEY `idx_parent_task_id` (`parent_task_id`),
    KEY `idx_status` (`status`),
    KEY `idx_priority` (`priority`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_task_conversation` FOREIGN KEY (`conversation_id`) 
        REFERENCES `conversation` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_parent` FOREIGN KEY (`parent_task_id`) 
        REFERENCES `task` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';

-- 2. 记忆存储表 (memory_store)
-- 功能: 存储智能体的短期、长期记忆和知识
CREATE TABLE IF NOT EXISTS `memory_store` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记忆ID',
    `conversation_id` BIGINT NOT NULL COMMENT '会话ID',
    `memory_type` VARCHAR(20) NOT NULL COMMENT '记忆类型：short_term/long_term/episodic/semantic',
    `content` TEXT NOT NULL COMMENT '记忆内容',
    `embedding` BLOB DEFAULT NULL COMMENT '向量嵌入（用于语义检索）',
    `importance_score` FLOAT DEFAULT 0 COMMENT '重要性评分（0-1）',
    `access_count` INT DEFAULT 0 COMMENT '访问次数',
    `last_accessed_at` DATETIME DEFAULT NULL COMMENT '最后访问时间',
    `expires_at` DATETIME DEFAULT NULL COMMENT '过期时间（短期记忆）',
    `metadata` JSON DEFAULT NULL COMMENT '元数据（来源、关联实体等）',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_conversation_memory` (`conversation_id`, `memory_type`),
    KEY `idx_importance` (`importance_score` DESC),
    KEY `idx_expires_at` (`expires_at`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_memory_conversation` FOREIGN KEY (`conversation_id`) 
        REFERENCES `conversation` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='记忆存储表';

-- 3. 知识图谱实体表 (knowledge_graph)
-- 功能: 存储知识图谱中的实体信息
CREATE TABLE IF NOT EXISTS `knowledge_graph` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '实体ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `entity_type` VARCHAR(50) NOT NULL COMMENT '实体类型：person/product/order/concept',
    `entity_name` VARCHAR(200) NOT NULL COMMENT '实体名称',
    `properties` JSON DEFAULT NULL COMMENT '实体属性（键值对）',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_entity` (`user_id`, `entity_type`),
    KEY `idx_entity_name` (`entity_name`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_kg_user` FOREIGN KEY (`user_id`) 
        REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识图谱实体表';

-- 4. 知识图谱关系表 (knowledge_relation)
-- 功能: 存储知识图谱中实体间的关系
CREATE TABLE IF NOT EXISTS `knowledge_relation` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '关系ID',
    `from_entity_id` BIGINT NOT NULL COMMENT '起始实体ID',
    `to_entity_id` BIGINT NOT NULL COMMENT '目标实体ID',
    `relation_type` VARCHAR(50) NOT NULL COMMENT '关系类型：owns/likes/related_to/depends_on',
    `weight` FLOAT DEFAULT 1.0 COMMENT '关系权重（0-1）',
    `properties` JSON DEFAULT NULL COMMENT '关系属性',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_from_entity` (`from_entity_id`),
    KEY `idx_to_entity` (`to_entity_id`),
    KEY `idx_relation_type` (`relation_type`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_kr_from` FOREIGN KEY (`from_entity_id`) 
        REFERENCES `knowledge_graph` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_kr_to` FOREIGN KEY (`to_entity_id`) 
        REFERENCES `knowledge_graph` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识图谱关系表';

-- =============================================
-- 创建完成提示
-- =============================================
SELECT 'Agent 系统数据库表创建完成！' AS message;
SELECT '已创建表: task, memory_store, knowledge_graph, knowledge_relation' AS tables_created;
