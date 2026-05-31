-- Migration: widen users.password to hold portable PBKDF2-SHA256 hashes.
--
-- Why: on non-Linux hosts the backend hashes passwords with
--   $pbkdf2-sha256$<iter>$<salt-hex>$<dk-hex>   (119 chars)
-- which overflows the original VARCHAR(100), causing registration/password
-- changes to fail with "Data too long for column 'password'". bcrypt (60) and
-- MD5 (32) still fit. VARCHAR(255) covers all current and future schemes.
--
-- Safe to run multiple times: MODIFY is idempotent for the target type.

ALTER TABLE `users`
    MODIFY COLUMN `password` VARCHAR(255) NOT NULL
    COMMENT '密码哈希(MD5/bcrypt/pbkdf2-sha256)';
