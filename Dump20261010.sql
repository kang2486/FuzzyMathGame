-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: fuzzy_math_game
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `parameter_rule`
--

DROP TABLE IF EXISTS `parameter_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `parameter_rule` (
  `parameter_id` int NOT NULL AUTO_INCREMENT,
  `type_id` varchar(10) NOT NULL,
  `parameter_name` varchar(50) NOT NULL,
  `default_value` decimal(10,2) NOT NULL,
  `min_value` decimal(10,2) NOT NULL,
  `max_value` decimal(10,2) NOT NULL,
  PRIMARY KEY (`parameter_id`),
  KEY `type_id` (`type_id`),
  CONSTRAINT `parameter_rule_ibfk_1` FOREIGN KEY (`type_id`) REFERENCES `question_type` (`question_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parameter_rule`
--

LOCK TABLES `parameter_rule` WRITE;
/*!40000 ALTER TABLE `parameter_rule` DISABLE KEYS */;
INSERT INTO `parameter_rule` VALUES (1,'T001','a',1.00,1.00,5.00),(2,'T001','b',2.00,-5.00,5.00),(3,'T001','c',-5.00,-5.00,5.00),(4,'T001','d',1.00,-5.00,5.00),(5,'T002','a',3.00,1.00,5.00),(6,'T002','b',4.00,-5.00,5.00),(7,'T002','c',-2.00,-5.00,5.00),(8,'T003','a',2.00,1.00,5.00),(9,'T003','b',1.00,-5.00,5.00),(10,'T004','a',2.00,1.00,5.00),(11,'T005','a',1.00,1.00,5.00),(12,'T005','b',1.00,-5.00,5.00),(13,'T005','c',2.00,1.00,5.00);
/*!40000 ALTER TABLE `parameter_rule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `question_bank`
--

DROP TABLE IF EXISTS `question_bank`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_bank` (
  `question_id` varchar(10) NOT NULL,
  `type_id` varchar(10) NOT NULL,
  `difficulty` int NOT NULL,
  `latex_expression` text NOT NULL,
  `parameters` json NOT NULL,
  PRIMARY KEY (`question_id`),
  KEY `type_id` (`type_id`),
  CONSTRAINT `question_bank_ibfk_1` FOREIGN KEY (`type_id`) REFERENCES `question_type` (`question_type_id`),
  CONSTRAINT `question_bank_chk_1` CHECK ((`difficulty` between 1 and 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `question_bank`
--

LOCK TABLES `question_bank` WRITE;
/*!40000 ALTER TABLE `question_bank` DISABLE KEYS */;
INSERT INTO `question_bank` VALUES ('Q001','T001',1,'f(x)=x^3+2x^2-5x+1','{\"a\": 1, \"b\": 2, \"c\": -5, \"d\": 1}'),('Q002','T002',2,'\\int (3x^2+4x-2)\\,dx','{\"a\": 3, \"b\": 4, \"c\": -2}'),('Q003','T003',2,'\\int_0^2 (x^2+1)\\,dx','{\"a\": 2, \"b\": 1}'),('Q004','T004',3,'\\lim_{x\\to 2}\\frac{x^2-4}{x-2}','{\"a\": 2}'),('Q005','T005',4,'f(x)=x^2+1,\\quad x=2','{\"a\": 1, \"b\": 1, \"c\": 2}');
/*!40000 ALTER TABLE `question_bank` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `question_type`
--

DROP TABLE IF EXISTS `question_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_type` (
  `question_type_id` varchar(10) NOT NULL,
  `chapter` int NOT NULL,
  `type_name` varchar(100) NOT NULL,
  `question_template` text NOT NULL,
  PRIMARY KEY (`question_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `question_type`
--

LOCK TABLES `question_type` WRITE;
/*!40000 ALTER TABLE `question_type` DISABLE KEYS */;
INSERT INTO `question_type` VALUES ('T001',1,'多項式微分','f(x)=ax^3+bx^2+cx+d'),('T002',2,'不定積分','\\int (ax^2+bx+c)\\,dx'),('T003',2,'定積分','\\int_0^a (x^2+b)\\,dx'),('T004',3,'極限','\\lim_{x\\to a}\\frac{x^2-a^2}{x-a}'),('T005',4,'切線方程式','f(x)=ax^2+b,\\quad x=c');
/*!40000 ALTER TABLE `question_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `solution_step`
--

DROP TABLE IF EXISTS `solution_step`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `solution_step` (
  `step_id` int NOT NULL AUTO_INCREMENT,
  `type_id` varchar(10) NOT NULL,
  `difficulty` int NOT NULL,
  `step_order` int NOT NULL,
  `step_description` varchar(255) NOT NULL,
  `step_template` text NOT NULL,
  `answer_template` text NOT NULL,
  PRIMARY KEY (`step_id`),
  UNIQUE KEY `uq_solution_step_order` (`type_id`,`difficulty`,`step_order`),
  CONSTRAINT `fk_solution_step_type` FOREIGN KEY (`type_id`) REFERENCES `question_type` (`question_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `solution_step`
--

LOCK TABLES `solution_step` WRITE;
/*!40000 ALTER TABLE `solution_step` DISABLE KEYS */;
INSERT INTO `solution_step` VALUES (1,'T001',1,1,'使用冪次微分法則','對每一項使用冪次微分法則','d/dx (a*x^3) = 3*a*x^2'),(2,'T001',1,2,'逐項計算微分','將各項係數與次方代入微分規則','3*a*x^2 + 2*b*x + c'),(3,'T001',1,3,'整理最終答案','合併並整理各項','f\'(x) = 3*a*x^2 + 2*b*x + c');
/*!40000 ALTER TABLE `solution_step` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-10  1:09:35
