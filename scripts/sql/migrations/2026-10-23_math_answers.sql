-- Preserve existing INT values while allowing skipped and decimal answers.
-- Re-runs are safe only for the known legacy INT NOT NULL or current DOUBLE NULL
-- contracts. Missing or unexpected schemas fail at PREPARE rather than being
-- silently treated as a fresh table.

SET @woniunote_math_answers_migration_sql = (
    SELECT CASE
        WHEN COUNT(*) = 1
             AND SUM(data_type = 'int' AND is_nullable = 'NO'
                     AND column_type NOT LIKE '%unsigned%') = 1
            THEN 'ALTER TABLE `math_training_wrong_answers` MODIFY COLUMN `user_answer` DOUBLE NULL COMMENT ''用户答案；NULL 表示跳过'''
        WHEN COUNT(*) = 1
             AND SUM(data_type = 'double' AND is_nullable = 'YES'
                     AND column_type NOT LIKE '%unsigned%') = 1
            THEN 'SELECT 1'
        ELSE 'UNSUPPORTED math_training_wrong_answers.user_answer schema'
    END
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'math_training_wrong_answers'
      AND column_name = 'user_answer'
);

PREPARE woniunote_math_answers_migration FROM @woniunote_math_answers_migration_sql;
EXECUTE woniunote_math_answers_migration;
DEALLOCATE PREPARE woniunote_math_answers_migration;
