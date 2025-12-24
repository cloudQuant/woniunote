-- WoniuNote 文章表
-- Article Table

CREATE TABLE IF NOT EXISTS `article` (
    `articleid` INT NOT NULL AUTO_INCREMENT,
    `userid` INT NOT NULL COMMENT '作者用户ID',
    `type` INT NOT NULL COMMENT '文章分类ID',
    `headline` VARCHAR(100) NOT NULL COMMENT '标题',
    `content` LONGTEXT COMMENT '文章内容(HTML)',
    `thumbnail` VARCHAR(30) DEFAULT NULL COMMENT '缩略图文件名',
    `credit` INT DEFAULT 0 COMMENT '阅读所需积分',
    `readcount` INT DEFAULT 0 COMMENT '阅读次数',
    `replycount` INT DEFAULT 0 COMMENT '评论数',
    `recommended` INT DEFAULT 0 COMMENT '是否推荐: 0-否, 1-是',
    `hidden` INT DEFAULT 0 COMMENT '是否隐藏: 0-否, 1-是',
    `drafted` INT DEFAULT 0 COMMENT '是否草稿: 0-否, 1-是',
    `checked` INT DEFAULT 1 COMMENT '是否审核通过: 0-否, 1-是',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updatetime` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`articleid`),
    KEY `idx_userid` (`userid`),
    KEY `idx_type` (`type`),
    KEY `idx_createtime` (`createtime`),
    KEY `idx_recommended` (`recommended`),
    KEY `idx_hidden_drafted` (`hidden`, `drafted`),
    CONSTRAINT `fk_article_user` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章表';
