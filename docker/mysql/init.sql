-- Zaslon-QDS Database Initialization Script
-- SIH 26141: Quantum-Teleportation-Based Cyber Threat Detection for QDS

CREATE DATABASE IF NOT EXISTS zaslon_qds CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE zaslon_qds;

-- 1. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY,
    session_name VARCHAR(128) NOT NULL,
    status ENUM(
        'CREATED',
        'HASHING',
        'HASHED',
        'STATE_PREPARATION',
        'TELEPORTING',
        'TELEPORTED',
        'DECLARATION_READY',
        'SAMPLING',
        'VERIFYING',
        'VERIFIED',
        'REJECTED',
        'FAILED'
    ) NOT NULL DEFAULT 'CREATED',
    created_by VARCHAR(64) NOT NULL,
    verifier_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_created_at (created_at)
) ENGINE=InnoDB;

-- 2. Participants Table
CREATE TABLE IF NOT EXISTS participants (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    name VARCHAR(64) NOT NULL,
    role ENUM('Signer', 'Verifier', 'Administrator') NOT NULL,
    public_key_fingerprint VARCHAR(128) NOT NULL,
    auth_token_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE KEY uq_session_participant (session_id, name)
) ENGINE=InnoDB;

-- 3. Hash Records Table
CREATE TABLE IF NOT EXISTS hash_records (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE,
    raw_message LONGTEXT NOT NULL,
    message_bytes_len BIGINT NOT NULL,
    sha512_digest VARCHAR(128) NOT NULL,
    hash_encoding_format VARCHAR(32) NOT NULL DEFAULT 'hex',
    file_name VARCHAR(255) NULL,
    file_mime_type VARCHAR(128) NULL,
    file_size_bytes BIGINT NULL,
    storage_path VARCHAR(512) NULL,
    is_binary_file BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_hash_digest (sha512_digest)
) ENGINE=InnoDB;

-- 4. Quantum Runs Table
CREATE TABLE IF NOT EXISTS quantum_runs (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    target_backend VARCHAR(64) NOT NULL DEFAULT 'cudaq-default',
    teleportation_count INT NOT NULL DEFAULT 4096,
    batch_size INT NOT NULL DEFAULT 512,
    completed_operations INT NOT NULL DEFAULT 0,
    failed_operations INT NOT NULL DEFAULT 0,
    current_batch INT NOT NULL DEFAULT 0,
    total_batches INT NOT NULL DEFAULT 0,
    execution_duration_ms DOUBLE NULL,
    status ENUM('PENDING', 'PREPARING', 'RUNNING', 'PROCESSING_RESULTS', 'COMPLETED', 'FAILED', 'CANCELLED') NOT NULL DEFAULT 'PENDING',
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_quantum_runs_session (session_id)
) ENGINE=InnoDB;

-- 5. Quantum Measurements Table
CREATE TABLE IF NOT EXISTS measurements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    quantum_run_id VARCHAR(36) NOT NULL,
    operation_index INT NOT NULL,
    prep_theta DOUBLE NOT NULL,
    prep_phi DOUBLE NOT NULL,
    expected_bit TINYINT NOT NULL,
    alice_m0 TINYINT NOT NULL,
    alice_m1 TINYINT NOT NULL,
    bob_correction_x TINYINT NOT NULL,
    bob_correction_z TINYINT NOT NULL,
    bob_observed_bit TINYINT NOT NULL,
    is_match BOOLEAN NOT NULL,
    FOREIGN KEY (quantum_run_id) REFERENCES quantum_runs(id) ON DELETE CASCADE,
    INDEX idx_meas_run_op (quantum_run_id, operation_index),
    INDEX idx_meas_is_match (is_match),
    UNIQUE KEY uq_run_op_idx (quantum_run_id, operation_index)
) ENGINE=InnoDB;

-- 6. Public Declarations Table
CREATE TABLE IF NOT EXISTS public_declarations (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE,
    signer_id VARCHAR(64) NOT NULL,
    signature_token VARCHAR(256) NOT NULL,
    declaration_payload_hash VARCHAR(128) NOT NULL,
    declared_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('ACTIVE', 'TAMPERED', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    is_consumed BOOLEAN NOT NULL DEFAULT FALSE,
    consumed_at TIMESTAMP NULL,
    consumed_in_verification_id VARCHAR(36) NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_declaration_signer (signer_id)
) ENGINE=InnoDB;

-- 7. Verification Samples Table
CREATE TABLE IF NOT EXISTS verification_samples (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    sample_ratio DOUBLE NOT NULL DEFAULT 0.05,
    sample_size INT NOT NULL,
    sample_seed BIGINT NOT NULL,
    sampled_indices JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_verif_sample_session (session_id)
) ENGINE=InnoDB;

-- 8. Verification Results Table
CREATE TABLE IF NOT EXISTS verification_results (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    transmission_id VARCHAR(36) NULL UNIQUE,
    sample_id VARCHAR(36) NULL,
    sample_size INT NOT NULL DEFAULT 0,
    match_count INT NOT NULL DEFAULT 0,
    mismatch_count INT NOT NULL DEFAULT 0,
    mismatch_ratio DOUBLE NOT NULL DEFAULT 0.0,
    fisher_p_value DOUBLE NULL,
    fisher_odds_ratio DOUBLE NULL,
    statistical_verdict ENUM('ACCEPTABLE', 'SUSPICIOUS', 'REJECTED', 'EVIDENCE_MISSING') NOT NULL,
    security_decision ENUM('VERIFIED', 'REJECTED', 'UNAUTHORIZED', 'INTEGRITY_FAILURE', 'INCONCLUSIVE') NOT NULL,
    attack_detected BOOLEAN NOT NULL DEFAULT FALSE,
    attack_category VARCHAR(64) NULL,
    decision_reason TEXT NOT NULL,
    certificate_serial VARCHAR(64) NULL,
    verification_source VARCHAR(32) NOT NULL DEFAULT 'IN_FLIGHT',
    certificate_receipt JSON NULL,
    verified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sample_id) REFERENCES verification_samples(id) ON DELETE SET NULL,
    INDEX idx_verif_result_session (session_id),
    INDEX idx_verif_decision (security_decision),
    INDEX idx_certificate_serial (certificate_serial)
) ENGINE=InnoDB;

-- 9. Attack Events Table
CREATE TABLE IF NOT EXISTS attack_events (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    attack_type VARCHAR(64) NOT NULL,
    simulated BOOLEAN NOT NULL DEFAULT FALSE,
    detected BOOLEAN NOT NULL DEFAULT TRUE,
    payload_manipulation JSON NULL,
    detection_evidence JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_attack_session (session_id),
    INDEX idx_attack_type (attack_type)
) ENGINE=InnoDB;

-- 10. Audit Events Table
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NULL,
    event_type VARCHAR(64) NOT NULL,
    actor VARCHAR(64) NOT NULL,
    ip_address VARCHAR(45) NULL,
    details JSON NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_session (session_id),
    INDEX idx_audit_event_type (event_type),
    INDEX idx_audit_timestamp (timestamp)
) ENGINE=InnoDB;

-- 11. Users Table (Authentication & RBAC)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role ENUM('ALICE', 'BOB', 'EVE', 'ADMIN') NOT NULL DEFAULT 'ALICE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_username (username),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- 12. Transmission Packages Table (Alice -> Eve -> Bob Dual-Channel Lifecycle)
CREATE TABLE IF NOT EXISTS transmission_packages (
    id VARCHAR(36) PRIMARY KEY,
    package_tracking_no VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    sender_id VARCHAR(64) NOT NULL,
    recipient_id VARCHAR(64) NOT NULL,
    status ENUM(
        'DRAFT',
        'SIGNED',
        'IN_TRANSIT',
        'INTERCEPTED',
        'PASSTHROUGH',
        'MODIFIED',
        'FORWARDED',
        'RECEIVED',
        'VERIFIED',
        'REJECTED'
    ) NOT NULL DEFAULT 'DRAFT',
    message_payload LONGTEXT NOT NULL,
    committed_digest VARCHAR(128) NOT NULL,
    declaration_id VARCHAR(36) NULL,
    signature_token VARCHAR(256) NOT NULL,
    declaration_payload_hash VARCHAR(128) NULL,
    quantum_run_id VARCHAR(36) NULL,
    intercepted_by VARCHAR(64) NULL,
    intercepted_at TIMESTAMP NULL,
    is_tampered BOOLEAN NOT NULL DEFAULT FALSE,
    attack_type VARCHAR(64) NULL,
    tamper_details JSON NULL,
    forwarded_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    file_name VARCHAR(255) NULL,
    file_mime_type VARCHAR(128) NULL,
    file_size_bytes BIGINT NULL,
    storage_path VARCHAR(512) NULL,
    qds_manifest_json JSON NULL,
    classical_channel_status VARCHAR(64) NOT NULL DEFAULT 'NORMAL',
    quantum_channel_status VARCHAR(64) NOT NULL DEFAULT 'COHERENT',
    tampered_channel VARCHAR(32) NULL,
    active_attack_vector VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (declaration_id) REFERENCES public_declarations(id) ON DELETE SET NULL,
    FOREIGN KEY (quantum_run_id) REFERENCES quantum_runs(id) ON DELETE SET NULL,
    INDEX idx_transmission_tracking (package_tracking_no),
    INDEX idx_transmission_status (status),
    INDEX idx_transmission_recipient (recipient_id),
    INDEX idx_transmission_session (session_id)
) ENGINE=InnoDB;
