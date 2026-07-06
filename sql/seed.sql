USE campus_servicedesk;

INSERT INTO roles (role_name) VALUES
('STUDENT'),
('STAFF'),
('TECHNICIAN'),
('ADMIN');

INSERT INTO departments (department_name) VALUES
('CSE'),
('ECE'),
('EEE'),
('Mechanical'),
('IT Services'),
('Administration');

INSERT INTO users (full_name, email, password_hash, role_id, department_id) VALUES
('Rohan Upadhyay', 'rohan@example.com', 'dummy_hash', 1, 2),
('Admin User', 'admin@example.com', 'dummy_hash', 4, 5),
('Tech One', 'tech1@example.com', 'dummy_hash', 3, 5),
('Staff User', 'staff@example.com', 'dummy_hash', 2, 6);

INSERT INTO technicians (user_id, specialization) VALUES
(3, 'Hardware and Network Support');

INSERT INTO assets (asset_tag, asset_name, asset_type, department_id, assigned_to_user_id) VALUES
('ECE-LAB-PC-001', 'Lab Computer 1', 'Computer', 2, NULL),
('ADM-PRN-001', 'Admin Printer', 'Printer', 6, 4);

INSERT INTO tickets (
    title,
    description,
    category,
    priority,
    status,
    requester_id,
    department_id,
    asset_id
) VALUES
(
    'Lab computer not starting',
    'The computer in ECE lab is not powering on.',
    'Hardware',
    'HIGH',
    'OPEN',
    1,
    2,
    1
),
(
    'Printer paper jam',
    'Admin office printer has frequent paper jam issue.',
    'Hardware',
    'MEDIUM',
    'OPEN',
    4,
    6,
    2
),
(
    'Wi-Fi not working in classroom',
    'The classroom Wi-Fi is not connecting for students.',
    'Network',
    'HIGH',
    'OPEN',
    1,
    2,
    NULL
);