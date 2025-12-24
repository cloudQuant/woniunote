-- WoniuNote 卡片和待办事项表
-- Card and Item Tables

-- 卡片表 (任务卡片)
CREATE TABLE IF NOT EXISTS `card` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `type` INT DEFAULT NULL COMMENT '卡片类型',
    `headline` TEXT NOT NULL COMMENT '标题',
    `content` LONGTEXT COMMENT '内容',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updatetime` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `donetime` DATETIME DEFAULT NULL COMMENT '完成时间',
    `usedtime` INT DEFAULT 0 COMMENT '已用时间(秒)',
    `begintime` DATETIME DEFAULT NULL COMMENT '开始时间',
    `endtime` DATETIME DEFAULT NULL COMMENT '结束时间',
    `cardcategory_id` INT DEFAULT NULL COMMENT '分类ID',
    PRIMARY KEY (`id`),
    KEY `idx_cardcategory_id` (`cardcategory_id`),
    KEY `idx_type` (`type`),
    KEY `idx_createtime` (`createtime`),
    CONSTRAINT `fk_card_category` FOREIGN KEY (`cardcategory_id`) REFERENCES `cardcategory` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务卡片表';

-- 待办事项表
CREATE TABLE IF NOT EXISTS `item` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `body` TEXT COMMENT '事项内容',
    `category_id` INT DEFAULT NULL COMMENT '分类ID',
    PRIMARY KEY (`id`),
    KEY `idx_category_id` (`category_id`),
    CONSTRAINT `fk_item_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='待办事项表';
