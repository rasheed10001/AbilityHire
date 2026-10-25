-- AbilityHire database schema (structure only, no data)
CREATE DATABASE IF NOT EXISTS abilityhire;
USE abilityhire;
SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `jobpublisher`;
CREATE TABLE `jobpublisher` (
  `PublisherID` int NOT NULL AUTO_INCREMENT,
  `FName` varchar(50) NOT NULL,
  `LName` varchar(50) NOT NULL,
  `Email` varchar(255) NOT NULL,
  `Password` varchar(255) NOT NULL,
  `PhoneNumber` varchar(15) NOT NULL,
  `City` varchar(255) NOT NULL,
  `country` varchar(100) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `gender` enum('Male','Female') DEFAULT NULL,
  PRIMARY KEY (`PublisherID`),
  UNIQUE KEY `PublisherID_UNIQUE` (`PublisherID`),
  UNIQUE KEY `Email_UNIQUE` (`Email`),
  UNIQUE KEY `PhoneNumber_UNIQUE` (`PhoneNumber`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `jobseeker`;
CREATE TABLE `jobseeker` (
  `seekerID` int NOT NULL AUTO_INCREMENT,
  `fname` varchar(50) NOT NULL,
  `Email` varchar(255) NOT NULL,
  `Password` varchar(255) NOT NULL,
  `PhoneNumber` varchar(15) DEFAULT NULL,
  `Gender` enum('Male','Female') DEFAULT NULL,
  `DisabilityDocument` longblob,
  `UserStatus` enum('Active','Inactive','Banned') DEFAULT NULL,
  `City` varchar(255) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `lname` varchar(50) NOT NULL,
  PRIMARY KEY (`seekerID`),
  UNIQUE KEY `seekerID_UNIQUE` (`seekerID`),
  UNIQUE KEY `Email_UNIQUE` (`Email`),
  UNIQUE KEY `PhoneNumber_UNIQUE` (`PhoneNumber`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `job`;
CREATE TABLE `job` (
  `JobID` int NOT NULL AUTO_INCREMENT,
  `PostingDate` date NOT NULL,
  `Salary` decimal(10,2) NOT NULL,
  `City` varchar(255) NOT NULL,
  `Status` enum('Open','Closed','In Progress') NOT NULL DEFAULT 'Open',
  `JobTitle` varchar(255) NOT NULL,
  `JobDescription` longtext,
  `PublisherID` int NOT NULL,
  PRIMARY KEY (`JobID`),
  UNIQUE KEY `JobID_UNIQUE` (`JobID`),
  KEY `fk_job_publisher` (`PublisherID`),
  CONSTRAINT `fk_job_publisher` FOREIGN KEY (`PublisherID`) REFERENCES `jobpublisher` (`PublisherID`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `applyto`;
CREATE TABLE `applyto` (
  `applytoDate` date NOT NULL,
  `seekerid` int NOT NULL,
  `jobid` int NOT NULL,
  KEY `fk_applyto_seeker_idx` (`seekerid`),
  KEY `fk_applyto_job` (`jobid`),
  CONSTRAINT `fk_applyto_job` FOREIGN KEY (`jobid`) REFERENCES `job` (`JobID`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_applyto_seeker` FOREIGN KEY (`seekerid`) REFERENCES `jobseeker` (`seekerID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `user_settings`;
CREATE TABLE `user_settings` (
  `setting_id` int NOT NULL AUTO_INCREMENT,
  `seeker_id` int DEFAULT NULL,
  `publisher_id` int DEFAULT NULL,
  `font_size` varchar(10) NOT NULL DEFAULT '16px',
  `notifications` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`setting_id`),
  UNIQUE KEY `idx_seeker_settings` (`seeker_id`),
  UNIQUE KEY `idx_publisher_settings` (`publisher_id`),
  CONSTRAINT `user_settings_ibfk_1` FOREIGN KEY (`seeker_id`) REFERENCES `jobseeker` (`seekerID`) ON DELETE CASCADE,
  CONSTRAINT `user_settings_ibfk_2` FOREIGN KEY (`publisher_id`) REFERENCES `jobpublisher` (`PublisherID`) ON DELETE CASCADE,
  CONSTRAINT `chk_user_type` CHECK ((((`seeker_id` is not null) and (`publisher_id` is null)) or ((`seeker_id` is null) and (`publisher_id` is not null))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS=1;
