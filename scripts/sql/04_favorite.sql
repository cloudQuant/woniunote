-- WoniuNote 收藏表
-- Favorite Table

CREATE TABLE IF NOT EXISTS `favorite` (
    `favoriteid` INT NOT NULL AUTO_INCREMENT,
    `userid` INT NOT NULL COMMENT '用户ID',
    `articleid` INT NOT NULL COMMENT '文章ID',
    `canceled` INT DEFAULT 0 COMMENT '是否取消: 0-否, 1-是',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updatetime` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`favoriteid`),
    UNIQUE KEY `uk_user_article` (`userid`, `articleid`),
    KEY `idx_userid` (`userid`),
    KEY `idx_articleid` (`articleid`),
    CONSTRAINT `fk_favorite_user` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE,
    CONSTRAINT `fk_favorite_article` FOREIGN KEY (`articleid`) REFERENCES `article` (`articleid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='收藏表';
