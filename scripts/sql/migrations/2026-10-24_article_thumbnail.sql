-- Preserve existing thumbnail values and NULLs while allowing upload paths.
-- Safe to re-run for either known nullable VARCHAR(30) or VARCHAR(512).
-- Missing columns and unknown definitions intentionally fail during PREPARE.

SET @woniunote_article_thumbnail_migration_sql = (
    SELECT CASE
        WHEN COUNT(*) = 1
             AND SUM(data_type = 'varchar'
                     AND column_type = 'varchar(30)'
                     AND character_maximum_length = 30
                     AND is_nullable = 'YES'
                     AND column_default IS NULL
                     AND character_set_name IS NOT NULL
                     AND collation_name IS NOT NULL
                     AND extra = ''
                     AND generation_expression = '') = 1
            THEN CONCAT(
                'ALTER TABLE `', REPLACE(DATABASE(), '`', '``'),
                '`.`article` MODIFY COLUMN `thumbnail` VARCHAR(512) CHARACTER SET `',
                REPLACE(MAX(character_set_name), '`', '``'),
                '` COLLATE `', REPLACE(MAX(collation_name), '`', '``'),
                '` NULL DEFAULT NULL COMMENT ',
                IF(
                    FIND_IN_SET('NO_BACKSLASH_ESCAPES', @@SESSION.sql_mode) > 0,
                    CONCAT(
                        '''',
                        REPLACE(MAX(column_comment), '''', ''''''),
                        ''''
                    ),
                    QUOTE(MAX(column_comment))
                )
            )
        WHEN COUNT(*) = 1
             AND SUM(data_type = 'varchar'
                     AND column_type = 'varchar(512)'
                     AND character_maximum_length = 512
                     AND is_nullable = 'YES'
                     AND column_default IS NULL
                     AND character_set_name IS NOT NULL
                     AND collation_name IS NOT NULL
                     AND extra = ''
                     AND generation_expression = '') = 1
            THEN 'SELECT 1'
        ELSE 'UNSUPPORTED article.thumbnail schema: expected nullable VARCHAR(30) or VARCHAR(512)'
    END
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'article'
      AND column_name = 'thumbnail'
);

PREPARE woniunote_article_thumbnail_migration FROM @woniunote_article_thumbnail_migration_sql;
EXECUTE woniunote_article_thumbnail_migration;
DEALLOCATE PREPARE woniunote_article_thumbnail_migration;
