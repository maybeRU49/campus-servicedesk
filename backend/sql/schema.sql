CREATE DATABASE IF NOT EXISTS campus_servicedesk;
USE campus_servicedesk;

CREATE TABLE IF NOT EXISTS roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    department_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_users_role
        FOREIGN KEY (role_id) REFERENCES roles(role_id),

    CONSTRAINT fk_users_department
        FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id INT AUTO_INCREMENT PRIMARY KEY,
    asset_tag VARCHAR(100) NOT NULL UNIQUE,
    asset_name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    department_id INT,
    assigned_to_user_id INT,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_assets_department
        FOREIGN KEY (department_id) REFERENCES departments(department_id),

    CONSTRAINT fk_assets_user
        FOREIGN KEY (assigned_to_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    requester_id INT NOT NULL,
    department_id INT,
    asset_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,

    CONSTRAINT fk_tickets_requester
        FOREIGN KEY (requester_id) REFERENCES users(user_id),

    CONSTRAINT fk_tickets_department
        FOREIGN KEY (department_id) REFERENCES departments(department_id),

    CONSTRAINT fk_tickets_asset
        FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS technicians (
    technician_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(100),
    is_available BOOLEAN DEFAULT TRUE,

    CONSTRAINT fk_technicians_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS ticket_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    technician_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_assignments_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),

    CONSTRAINT fk_assignments_technician
        FOREIGN KEY (technician_id) REFERENCES technicians(technician_id)
);

CREATE TABLE IF NOT EXISTS ticket_comments (
    comment_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    user_id INT NOT NULL,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_comments_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),

    CONSTRAINT fk_comments_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS ticket_status_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_by_user_id INT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_history_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),

    CONSTRAINT fk_history_user
        FOREIGN KEY (changed_by_user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_category ON tickets(category);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_department ON tickets(department_id);
CREATE INDEX idx_assignments_technician ON ticket_assignments(technician_id);

CREATE OR REPLACE VIEW vw_ticket_details AS
SELECT 
    t.ticket_id,
    t.title,
    t.category,
    t.priority,
    t.status,
    requester.full_name AS requester,
    d.department_name,
    a.asset_name,
    tech_user.full_name AS assigned_technician,
    t.created_at,
    t.updated_at,
    t.resolved_at
FROM tickets t
JOIN users requester ON t.requester_id = requester.user_id
LEFT JOIN departments d ON t.department_id = d.department_id
LEFT JOIN assets a ON t.asset_id = a.asset_id
LEFT JOIN ticket_assignments ta ON t.ticket_id = ta.ticket_id
LEFT JOIN technicians tech ON ta.technician_id = tech.technician_id
LEFT JOIN users tech_user ON tech.user_id = tech_user.user_id;