-- WoniuNote 积分记录表
-- Credit Table

CREATE TABLE IF NOT EXISTS `credit` (
    `creditid` INT NOT NULL AUTO_INCREMENT,
    `userid` INT NOT NULL COMMENT '用户ID',
    `category` VARCHAR(20) DEFAULT NULL COMMENT '积分类型: 正常登录/用户注册/添加评论等',
    `target` INT DEFAULT 0 COMMENT '目标ID(如文章ID)',
    `credit` INT DEFAULT 0 COMMENT '积分变化值',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updatetime` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`creditid`),
    KEY `idx_userid` (`userid`),
    KEY `idx_category` (`category`),
    KEY `idx_createtime` (`createtime`),
    CONSTRAINT `fk_credit_user` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分记录表';
