-- MAHLE Checklist System Database Schema
-- MySQL

-- Create database
CREATE DATABASE IF NOT EXISTS mahle_db;
USE mahle_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    machine_id VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'Operator',
    assigned_checklists TEXT DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    operator_name VARCHAR(100) NOT NULL,
    operator_id VARCHAR(50) NOT NULL,
    machine_id VARCHAR(50) NOT NULL,
    batch_no VARCHAR(20) NOT NULL,
    checklist_no INT NOT NULL,
    shift VARCHAR(20) DEFAULT 'no_shift',
    payload TEXT NOT NULL,
    verify_status VARCHAR(20) DEFAULT 'Pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sample users (password is 'pass123' hashed)
INSERT INTO users (name, employee_id, machine_id, password_hash, role, assigned_checklists) VALUES
('Admin User', 'ADM001', 'MACH001', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS6aLW9.W', 'Admin', '[]'),
('Supervisor User', 'SUP001', 'MACH001', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS6aLW9.W', 'Supervisor', '[]'),
('Operator User', 'OP001', 'MACH001', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS6aLW9.W', 'Operator', '["1_ep6_crimping_startup","fms","leak_testing"]');