CREATE DATABASE IF NOT EXISTS zaslon_qds
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'zaslon'@'localhost' IDENTIFIED BY 'zaslon_dev';
CREATE USER IF NOT EXISTS 'zaslon'@'127.0.0.1' IDENTIFIED BY 'zaslon_dev';
CREATE USER IF NOT EXISTS 'zaslon'@'172.16.0.0/255.240.0.0' IDENTIFIED BY 'zaslon_dev';

GRANT ALL PRIVILEGES ON zaslon_qds.* TO 'zaslon'@'localhost';
GRANT ALL PRIVILEGES ON zaslon_qds.* TO 'zaslon'@'127.0.0.1';
GRANT ALL PRIVILEGES ON zaslon_qds.* TO 'zaslon'@'172.16.0.0/255.240.0.0';
FLUSH PRIVILEGES;
