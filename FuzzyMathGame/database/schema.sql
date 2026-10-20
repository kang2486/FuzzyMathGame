CREATE DATABASE IF NOT EXISTS fuzzy_math_game_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fuzzy_math_game_dev;
CREATE TABLE IF NOT EXISTS bank_meta (version INT PRIMARY KEY, description VARCHAR(200) NOT NULL);
CREATE TABLE IF NOT EXISTS chapter (chapter TINYINT PRIMARY KEY, name VARCHAR(100) NOT NULL);
CREATE TABLE IF NOT EXISTS question_type (
 type_id VARCHAR(16) PRIMARY KEY, chapter TINYINT NOT NULL, name VARCHAR(100) NOT NULL,
 FOREIGN KEY(chapter) REFERENCES chapter(chapter));
CREATE TABLE IF NOT EXISTS question_spec (
 spec_id VARCHAR(64) PRIMARY KEY, type_id VARCHAR(16) NOT NULL, difficulty TINYINT NOT NULL,
 question_template TEXT NOT NULL, question_latex_template TEXT NOT NULL,
 derived_values JSON NOT NULL, answer_rule VARCHAR(200) NOT NULL,
 status VARCHAR(16) NOT NULL DEFAULT 'draft', source_note TEXT NOT NULL,
 UNIQUE(type_id,difficulty), FOREIGN KEY(type_id) REFERENCES question_type(type_id),
 CHECK(difficulty BETWEEN 1 AND 5));
CREATE TABLE IF NOT EXISTS spec_parameter (
 spec_id VARCHAR(64) NOT NULL, parameter_name VARCHAR(32) NOT NULL,
 min_value INT NOT NULL, max_value INT NOT NULL,
 PRIMARY KEY(spec_id,parameter_name), FOREIGN KEY(spec_id) REFERENCES question_spec(spec_id),
 CHECK(min_value <= max_value));
CREATE TABLE IF NOT EXISTS solution_step (
 step_id VARCHAR(80) PRIMARY KEY, spec_id VARCHAR(64) NOT NULL,
 step_order SMALLINT NOT NULL, display_template TEXT NOT NULL,
 value_rule VARCHAR(200) NOT NULL, hint TEXT NOT NULL,
 UNIQUE(spec_id,step_order), FOREIGN KEY(spec_id) REFERENCES question_spec(spec_id), CHECK(step_order > 0));
CREATE TABLE IF NOT EXISTS solution_option (
 step_id VARCHAR(80) NOT NULL, option_order TINYINT NOT NULL,
 value_rule VARCHAR(200) NOT NULL, misconception_code VARCHAR(64) NOT NULL,
 explanation TEXT NOT NULL, PRIMARY KEY(step_id,option_order),
 FOREIGN KEY(step_id) REFERENCES solution_step(step_id));
