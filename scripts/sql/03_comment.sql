-- WoniuNote 评论表
-- Comment Table

CREATE TABLE IF NOT EXISTS `comment` (
    `commentid` INT NOT NULL AUTO_INCREMENT,
    `userid` INT NOT NULL COMMENT '评论用户ID',
    `articleid` INT NOT NULL COMMENT '文章ID',
    `content` MEDIUMTEXT NOT NULL COMMENT '评论内容',
    `ipaddr` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址(支持IPv6)',
    `replyid` INT DEFAULT NULL COMMENT '回复的评论ID',
    `agreecount` INT DEFAULT 0 COMMENT '赞同数',
    `opposecount` INT DEFAULT 0 COMMENT '反对数',
    `hidden` INT DEFAULT 0 COMMENT '是否隐藏: 0-否, 1-是',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updatetime` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`commentid`),
    KEY `idx_userid` (`userid`),
    KEY `idx_articleid` (`articleid`),
    KEY `idx_replyid` (`replyid`),
    KEY `idx_createtime` (`createtime`),
    CONSTRAINT `fk_comment_user` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE,
    CONSTRAINT `fk_comment_article` FOREIGN KEY (`articleid`) REFERENCES `article` (`articleid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论表';

-- 评论投票表 (赞/踩)
CREATE TABLE IF NOT EXISTS `comment_votes` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `commentid` INT NOT NULL COMMENT '评论ID',
    `userid` INT NOT NULL COMMENT '用户ID',
    `vote_type` TINYINT NOT NULL COMMENT '投票类型: 1-赞, -1-踩',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_comment_user` (`commentid`, `userid`),
    KEY `idx_userid` (`userid`),
    CONSTRAINT `fk_vote_comment` FOREIGN KEY (`commentid`) REFERENCES `comment` (`commentid`) ON DELETE CASCADE,
    CONSTRAINT `fk_vote_user` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论投票表';
