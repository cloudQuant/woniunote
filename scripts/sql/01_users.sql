-- WoniuNote 用户表
-- Users Table

CREATE TABLE IF NOT EXISTS `users` (
    `userid` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL COMMENT '用户名/邮箱',
    `password` VARCHAR(100) NOT NULL COMMENT '密码哈希(MD5或bcrypt)',
    `nickname` VARCHAR(30) DEFAULT NULL COMMENT '昵称',
    `avatar` VARCHAR(20) DEFAULT NULL COMMENT '头像文件名',
    `qq` VARCHAR(15) DEFAULT NULL COMMENT 'QQ号',
    `role` VARCHAR(10) NOT NULL DEFAULT 'user' COMMENT '角色: admin/editor/user',
    `credit` INT DEFAULT 0 COMMENT '积分',
    `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updatetime` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`userid`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
