-- FraudLens 数据库初始化脚本
-- Docker 容器首次启动时自动执行（挂载到 /docker-entrypoint-initdb.d/）

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 用户表
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL UNIQUE,
  `password_hash` VARCHAR(256) NOT NULL,
  `display_name` VARCHAR(64) DEFAULT '',
  `role` VARCHAR(20) DEFAULT 'analyst',
  `department` VARCHAR(100) DEFAULT '',
  `phone` VARCHAR(20) DEFAULT '',
  `is_active` BOOLEAN DEFAULT TRUE,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `last_login` DATETIME DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 操作日志
CREATE TABLE IF NOT EXISTS `operation_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT DEFAULT NULL,
  `username` VARCHAR(64) DEFAULT '',
  `action` VARCHAR(64) NOT NULL,
  `target_type` VARCHAR(32) DEFAULT '',
  `target_id` VARCHAR(64) DEFAULT '',
  `detail` JSON DEFAULT NULL,
  `ip_address` VARCHAR(45) DEFAULT '',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 分析会话
CREATE TABLE IF NOT EXISTS `analysis_sessions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `session_id` VARCHAR(64) NOT NULL UNIQUE,
  `status` VARCHAR(20) DEFAULT 'pending',
  `total_cases` INT DEFAULT 0,
  `total_gangs` INT DEFAULT 0,
  `raw_input` JSON DEFAULT NULL,
  `processing_info` JSON DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 案件表
CREATE TABLE IF NOT EXISTS `cases` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `case_id` VARCHAR(32) NOT NULL UNIQUE,
  `number` INT DEFAULT 0,
  `session_id` VARCHAR(64) DEFAULT NULL,
  `title` VARCHAR(200) DEFAULT '',
  `scam_type` VARCHAR(100) DEFAULT '',
  `scam_subtype` VARCHAR(100) DEFAULT '',
  `risk_level` VARCHAR(10) DEFAULT 'LOW',
  `risk_label` VARCHAR(20) DEFAULT '低风险',
  `risk_type` VARCHAR(20) DEFAULT 'info',
  `risk_score` INT DEFAULT 0,
  `victim_name` VARCHAR(50) DEFAULT '',
  `victim_gender` VARCHAR(10) DEFAULT '',
  `victim_age` VARCHAR(10) DEFAULT '',
  `victim_phone` VARCHAR(30) DEFAULT '',
  `victim_job` VARCHAR(50) DEFAULT '',
  `victim_address` VARCHAR(200) DEFAULT '',
  `amount` VARCHAR(50) DEFAULT '',
  `amount_value` FLOAT DEFAULT 0.0,
  `description` TEXT DEFAULT NULL,
  `status` VARCHAR(20) DEFAULT '待分析',
  `source` VARCHAR(20) DEFAULT '文本',
  `ai_report` TEXT DEFAULT NULL,
  `keywords` JSON DEFAULT NULL,
  `steps` JSON DEFAULT NULL,
  `roles` JSON DEFAULT NULL,
  `extracted_entities` JSON DEFAULT NULL,
  `message_count` INT DEFAULT 0,
  `time_range` VARCHAR(50) DEFAULT '',
  `warning` TEXT DEFAULT NULL,
  `is_error` BOOLEAN DEFAULT FALSE,
  `embedding` LONGBLOB DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`session_id`) REFERENCES `analysis_sessions`(`session_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 团伙表
CREATE TABLE IF NOT EXISTS `gangs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `gang_id` VARCHAR(32) NOT NULL UNIQUE,
  `number` INT DEFAULT 0,
  `session_id` VARCHAR(64) DEFAULT NULL,
  `gang_name` VARCHAR(100) DEFAULT '未命名团伙',
  `risk_level` VARCHAR(10) DEFAULT 'C',
  `risk_label` VARCHAR(20) DEFAULT '低风险',
  `risk_type` VARCHAR(20) DEFAULT 'info',
  `threat_level` VARCHAR(5) DEFAULT 'C',
  `comprehensive_score` INT DEFAULT 0,
  `confidence` INT DEFAULT 0,
  `member_count_estimate` VARCHAR(50) DEFAULT '',
  `tech_level` VARCHAR(10) DEFAULT '中',
  `script_type` VARCHAR(100) DEFAULT '',
  `total_cases` INT DEFAULT 0,
  `total_amount` VARCHAR(50) DEFAULT '',
  `total_amount_value` FLOAT DEFAULT 0.0,
  `description` TEXT DEFAULT NULL,
  `fingerprint` JSON DEFAULT NULL,
  `enhanced_fingerprint` JSON DEFAULT NULL,
  `steps` JSON DEFAULT NULL,
  `radar_data` JSON DEFAULT NULL,
  `deep_characteristics` JSON DEFAULT NULL,
  `risk_assessment` JSON DEFAULT NULL,
  `modus_operandi` TEXT DEFAULT NULL,
  `prevention_advice` TEXT DEFAULT NULL,
  `network_nodes` JSON DEFAULT NULL,
  `centroid` LONGBLOB DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`session_id`) REFERENCES `analysis_sessions`(`session_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 团伙-案件关联
CREATE TABLE IF NOT EXISTS `gang_case_relations` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `gang_id` VARCHAR(32) NOT NULL,
  `case_id` VARCHAR(32) NOT NULL,
  `similarity` FLOAT DEFAULT 0.0,
  `added_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_gang_case` (`gang_id`, `case_id`),
  FOREIGN KEY (`gang_id`) REFERENCES `gangs`(`gang_id`) ON DELETE CASCADE,
  FOREIGN KEY (`case_id`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 人员表
CREATE TABLE IF NOT EXISTS `persons` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `case_id` VARCHAR(32) NOT NULL,
  `name` VARCHAR(50) DEFAULT '',
  `role` VARCHAR(20) DEFAULT '',
  `gender` VARCHAR(10) DEFAULT '',
  `age` VARCHAR(10) DEFAULT '',
  `phone` VARCHAR(30) DEFAULT '',
  `job` VARCHAR(50) DEFAULT '',
  `address` VARCHAR(200) DEFAULT '',
  FOREIGN KEY (`case_id`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 账户表
CREATE TABLE IF NOT EXISTS `accounts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `person_id` INT DEFAULT NULL,
  `account_number` VARCHAR(50) DEFAULT '',
  `bank_name` VARCHAR(100) DEFAULT '',
  `risk_level` VARCHAR(10) DEFAULT 'unknown',
  FOREIGN KEY (`person_id`) REFERENCES `persons`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 电话表
CREATE TABLE IF NOT EXISTS `phones` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `person_id` INT DEFAULT NULL,
  `phone_number` VARCHAR(30) DEFAULT '',
  `carrier` VARCHAR(50) DEFAULT '',
  `risk_level` VARCHAR(10) DEFAULT 'unknown',
  FOREIGN KEY (`person_id`) REFERENCES `persons`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 证据表
CREATE TABLE IF NOT EXISTS `evidence_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `case_id` VARCHAR(32) NOT NULL,
  `type` VARCHAR(50) DEFAULT '',
  `content` TEXT DEFAULT NULL,
  `status` VARCHAR(20) DEFAULT '待验证',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`case_id`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 预警记录
CREATE TABLE IF NOT EXISTS `alert_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `alert_type` VARCHAR(32) NOT NULL,
  `case_id` VARCHAR(32) NOT NULL,
  `matched_case_id` VARCHAR(32) NOT NULL,
  `matched_entities` JSON DEFAULT NULL,
  `confidence` FLOAT DEFAULT 0.0,
  `resolved` BOOLEAN DEFAULT FALSE,
  `resolved_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 合并建议
CREATE TABLE IF NOT EXISTS `merge_suggestions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `case_id_a` VARCHAR(32) NOT NULL,
  `case_id_b` VARCHAR(32) NOT NULL,
  `similarity` FLOAT DEFAULT 0.0,
  `reason` VARCHAR(200) DEFAULT '',
  `status` VARCHAR(20) DEFAULT 'pending',
  `reviewed_by` INT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `reviewed_at` DATETIME DEFAULT NULL,
  FOREIGN KEY (`case_id_a`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE,
  FOREIGN KEY (`case_id_b`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE,
  FOREIGN KEY (`reviewed_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 资金流向
CREATE TABLE IF NOT EXISTS `capital_flows` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `case_id` VARCHAR(32) NOT NULL,
  `source_account` VARCHAR(100) DEFAULT '',
  `target_account` VARCHAR(100) DEFAULT '',
  `bank_name` VARCHAR(100) DEFAULT '',
  `amount` FLOAT DEFAULT 0.0,
  `transaction_time` DATETIME DEFAULT NULL,
  `direction` VARCHAR(10) DEFAULT 'out',
  `level` INT DEFAULT 1,
  `annotation` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`case_id`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 派单记录
CREATE TABLE IF NOT EXISTS `dispatch_orders` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `alert_id` VARCHAR(64) DEFAULT '',
  `case_id` VARCHAR(32) NOT NULL,
  `assigned_dept` VARCHAR(100) DEFAULT '',
  `assigned_officer` VARCHAR(100) DEFAULT '',
  `status` VARCHAR(20) DEFAULT 'pending',
  `dispatch_time` DATETIME DEFAULT NULL,
  `sign_time` DATETIME DEFAULT NULL,
  `feedback` TEXT DEFAULT NULL,
  `deadline` DATETIME DEFAULT NULL,
  `created_by` INT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`case_id`) REFERENCES `cases`(`case_id`) ON DELETE CASCADE,
  FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 重点人员
CREATE TABLE IF NOT EXISTS `key_persons` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) DEFAULT '',
  `id_number` VARCHAR(18) NOT NULL UNIQUE,
  `gender` VARCHAR(10) DEFAULT '',
  `age` VARCHAR(10) DEFAULT '',
  `phone` VARCHAR(30) DEFAULT '',
  `bank_account` VARCHAR(50) DEFAULT '',
  `address` VARCHAR(200) DEFAULT '',
  `risk_level` VARCHAR(10) DEFAULT 'B',
  `risk_label` VARCHAR(20) DEFAULT '中风险',
  `person_type` VARCHAR(20) DEFAULT '前科人员',
  `tags` JSON DEFAULT NULL,
  `case_ids` JSON DEFAULT NULL,
  `source` VARCHAR(100) DEFAULT '',
  `notes` TEXT DEFAULT NULL,
  `is_active` BOOLEAN DEFAULT TRUE,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建索引
CREATE INDEX idx_cases_session ON `cases`(`session_id`);
CREATE INDEX idx_cases_scam_type ON `cases`(`scam_type`);
CREATE INDEX idx_cases_risk_level ON `cases`(`risk_level`);
CREATE INDEX idx_gangs_session ON `gangs`(`session_id`);
CREATE INDEX idx_capital_flows_case ON `capital_flows`(`case_id`);
CREATE INDEX idx_alert_records_case ON `alert_records`(`case_id`);

-- 插入默认管理员 (密码: admin123)
-- werkzeug generate_password_hash('admin123') 的结果
INSERT IGNORE INTO `users` (`username`, `password_hash`, `display_name`, `role`, `department`, `is_active`)
VALUES ('admin', 'pbkdf2:sha256:600000$salt$hash_placeholder', '系统管理员', 'admin', '系统管理部', TRUE);

-- 注意：上面的密码hash是占位符，首次启动后端时会自动创建正确的admin用户
