-- 数学训练功能数据库表
-- Math Training Database Tables

-- 训练记录表
CREATE TABLE IF NOT EXISTS math_training_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    difficulty INT NOT NULL DEFAULT 1 COMMENT '难度等级: 1-简单, 2-中等, 3-困难',
    total_questions INT NOT NULL DEFAULT 0 COMMENT '总题目数',
    correct_count INT NOT NULL DEFAULT 0 COMMENT '正确数',
    wrong_count INT NOT NULL DEFAULT 0 COMMENT '错误数',
    accuracy DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '正确率百分比',
    start_time DATETIME NULL COMMENT '开始时间',
    end_time DATETIME NULL COMMENT '结束时间',
    duration_seconds INT NOT NULL DEFAULT 0 COMMENT '持续时间(秒)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_difficulty (difficulty),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(userid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数学训练记录表';

-- 错题记录表
CREATE TABLE IF NOT EXISTS math_training_wrong_answers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    record_id BIGINT NOT NULL COMMENT '关联的训练记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    question VARCHAR(100) NOT NULL COMMENT '题目内容',
    correct_answer INT NOT NULL COMMENT '正确答案',
    user_answer INT NOT NULL COMMENT '用户答案',
    operation VARCHAR(10) NOT NULL COMMENT '运算类型: +, -, *, /',
    difficulty INT NOT NULL DEFAULT 1 COMMENT '难度等级',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_record_id (record_id),
    INDEX idx_user_id (user_id),
    INDEX idx_difficulty (difficulty),
    INDEX idx_operation (operation),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (record_id) REFERENCES math_training_records(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(userid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数学训练错题记录表';
