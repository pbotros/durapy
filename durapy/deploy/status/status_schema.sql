CREATE TABLE `process_statuses` (
                                    `id` bigint NOT NULL AUTO_INCREMENT,
                                    `process_name` VARCHAR(255) NOT NULL,
                                    `last_started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    `last_heartbeat_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    `git_sha` VARCHAR(255) NOT NULL,
                                    PRIMARY KEY (`id`),
                                    UNIQUE KEY `unq_proces_name` (`process_name`)
) ENGINE=InnoDB DEFAULT CHARSET=UTF8MB4;

