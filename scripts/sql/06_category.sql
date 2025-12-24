-- WoniuNote 分类表
-- Category Tables

-- 文章分类表
CREATE TABLE IF NOT EXISTS `category` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(64) DEFAULT NULL COMMENT '分类名称',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章分类表';

-- 卡片分类表
CREATE TABLE IF NOT EXISTS `cardcategory` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(64) DEFAULT NULL COMMENT '分类名称',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='卡片分类表';

-- 初始化默认分类数据
INSERT IGNORE INTO `category` (`id`, `name`) VALUES
(1, '收件箱'),
(2, '已完成'),
(4, '工作清单'),
(5, '学习清单'),
(6, '写作清单'),
(7, '生活清单'),
(9, '月计划清单'),
(10, '周计划清单'),
(11, '年计划清单'),
(12, '日计划清单');

INSERT IGNORE INTO `cardcategory` (`id`, `name`) VALUES
(1, '待完成'),
(2, '已完成'),
(3, '写作清单'),
(4, '学习清单'),
(5, '工作清单'),
(6, '日清单'),
(7, '周清单'),
(8, '月清单'),
(9, '年清单'),
(10, '十年清单'),
(11, '生活清单'),
(12, '锻炼清单'),
(13, '重要紧急'),
(14, '重要不紧急'),
(15, '紧急不重要'),
(17, '不重要不紧急'),
(18, '社交清单'),
(19, '常规清单'),
(20, '已开始清单');
