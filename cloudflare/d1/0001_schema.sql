DROP TABLE IF EXISTS branches;

CREATE TABLE branches (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	region VARCHAR(50) NOT NULL, 
	address VARCHAR(200), 
	is_headquarters BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

DROP TABLE IF EXISTS dealers;

CREATE TABLE dealers (
	id VARCHAR(36) NOT NULL, 
	branch_id VARCHAR(36) NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	dealership_name VARCHAR(100) NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	partnership_status VARCHAR(30) NOT NULL, 
	contract_date VARCHAR(20), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(branch_id) REFERENCES branches (id)
);

DROP TABLE IF EXISTS users;

CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	hashed_password VARCHAR(100) NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	branch_id VARCHAR(36), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	FOREIGN KEY(branch_id) REFERENCES branches (id)
);

DROP TABLE IF EXISTS vehicles;

CREATE TABLE vehicles (
	id VARCHAR(36) NOT NULL, 
	branch_id VARCHAR(36) NOT NULL, 
	plate_number VARCHAR(20) NOT NULL, 
	model_name VARCHAR(100) NOT NULL, 
	year INTEGER NOT NULL, 
	mileage INTEGER NOT NULL, 
	fuel_type VARCHAR(20) NOT NULL, 
	transmission VARCHAR(20) NOT NULL, 
	color VARCHAR(30) NOT NULL, 
	purchase_price INTEGER NOT NULL, 
	target_price INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	timeline_json TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, ownership_type VARCHAR(30) DEFAULT 'CHAMART_OWNED', dealer_id VARCHAR(36), vin VARCHAR(30), displacement_cc INTEGER, first_registration_date VARCHAR(20), drive_type VARCHAR(20) DEFAULT '2WD', interior_color VARCHAR(30) DEFAULT '블랙', options_json TEXT DEFAULT '[]', accident_history_json TEXT DEFAULT '{}', inspection_summary_json TEXT DEFAULT '{}', marketing_auth_json TEXT DEFAULT '{}', primary_photo_url VARCHAR(255), video_status VARCHAR(30) DEFAULT 'NONE', manufacturer VARCHAR(50), trim VARCHAR(100), body_type VARCHAR(30) DEFAULT '세단', recon_cost INTEGER DEFAULT 0, sales_conditions VARCHAR(255), ad_description TEXT, ad_highlights TEXT, ad_notices TEXT, platform_ad_copies_json TEXT DEFAULT '{}', options_structured_json TEXT DEFAULT '[]', condition_detail_json TEXT DEFAULT '{}', publishing_status VARCHAR(30) DEFAULT 'DRAFT', platform_readiness_json TEXT DEFAULT '{}', is_public BOOLEAN DEFAULT 1, listing_ownership_type VARCHAR(30) DEFAULT "OWNED", is_priority_exposure BOOLEAN DEFAULT 0, priority_rank INTEGER DEFAULT 0, priority_start_date DATETIME, priority_end_date DATETIME, priority_reason VARCHAR(255), priority_history_json TEXT DEFAULT "[]", 
	PRIMARY KEY (id), 
	FOREIGN KEY(branch_id) REFERENCES branches (id)
);

DROP TABLE IF EXISTS vehicle_photos;

CREATE TABLE vehicle_photos (
	id VARCHAR(36) NOT NULL, 
	vehicle_id VARCHAR(36) NOT NULL, 
	photo_url VARCHAR(255) NOT NULL, 
	thumb_url VARCHAR(255), 
	category VARCHAR(30) NOT NULL, 
	sort_order INTEGER NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	allow_video_use BOOLEAN NOT NULL, 
	caption VARCHAR(100), 
	created_at DATETIME NOT NULL, verification_status VARCHAR(30) DEFAULT "UNVERIFIED", photo_source VARCHAR(50) DEFAULT "UNKNOWN", original_file_hash VARCHAR(64), usage_rights_status VARCHAR(30) DEFAULT "PENDING", verified_by VARCHAR(50), verified_at DATETIME, view_code VARCHAR(50), category_code VARCHAR(50) DEFAULT "EXTERIOR_FULL", display_label VARCHAR(100) DEFAULT "외관", original_path VARCHAR(255), thumbnail_path VARCHAR(255), uploaded_by VARCHAR(50), public_visibility VARCHAR(30) DEFAULT "PUBLIC", approval_status VARCHAR(30) DEFAULT "APPROVED", photo_note TEXT, damage_evidence BOOLEAN DEFAULT 0, mime_type VARCHAR(50) DEFAULT "image/jpeg", file_size_bytes INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
);

DROP TABLE IF EXISTS vehicle_defects;

CREATE TABLE vehicle_defects (
	id VARCHAR(36) NOT NULL, 
	vehicle_id VARCHAR(36) NOT NULL, 
	part_name VARCHAR(100) NOT NULL, 
	defect_type VARCHAR(100) NOT NULL, 
	severity VARCHAR(30) NOT NULL, 
	action_status VARCHAR(30) NOT NULL, 
	estimated_repair_cost INTEGER NOT NULL, 
	photo_url VARCHAR(255), 
	notes TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
);

DROP TABLE IF EXISTS vehicle_listings;

CREATE TABLE vehicle_listings (
	id VARCHAR(36) NOT NULL, 
	vehicle_id VARCHAR(36) NOT NULL, 
	platform VARCHAR(30) NOT NULL, 
	listing_id VARCHAR(50) NOT NULL, 
	listing_url VARCHAR(255), 
	advertised_price INTEGER NOT NULL, 
	listing_status VARCHAR(30) NOT NULL, 
	first_observed_at DATETIME NOT NULL, 
	last_observed_at DATETIME NOT NULL, region VARCHAR(50) DEFAULT '장한평', is_janghanpyeong BOOLEAN DEFAULT 1, data_confidence FLOAT DEFAULT 0.95, price_drop_amount INTEGER DEFAULT 0, market_avg_price INTEGER DEFAULT 0, opportunity_score FLOAT DEFAULT 0.0, observation_notes VARCHAR(255), initial_price INTEGER DEFAULT 0, price_history_json TEXT DEFAULT '[]', location_category VARCHAR(50) DEFAULT 'LOCATION_UNKNOWN', identification_reason VARCHAR(255), raw_seller_location VARCHAR(255), raw_seller_name VARCHAR(100), source_confidence FLOAT DEFAULT 0.90, ingested_at DATETIME, is_demo BOOLEAN DEFAULT 0, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
);

DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
	id VARCHAR(36) NOT NULL, 
	branch_id VARCHAR(36) NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	target_vehicle_model VARCHAR(100), 
	budget_max INTEGER, 
	assigned_staff VARCHAR(50) NOT NULL, 
	contact_consent BOOLEAN NOT NULL, 
	notes TEXT, 
	is_demo BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, job_title VARCHAR(50), company_name VARCHAR(100), company_address VARCHAR(255), company_phone VARCHAR(30), email VARCHAR(100), source VARCHAR(50) DEFAULT 'DIRECT', source_image_url VARCHAR(500), ai_confidence FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(branch_id) REFERENCES branches (id)
);

DROP TABLE IF EXISTS consultations;

CREATE TABLE consultations (
	id VARCHAR(36) NOT NULL, 
	customer_id VARCHAR(36) NOT NULL, 
	channel VARCHAR(30) NOT NULL, 
	content TEXT NOT NULL, 
	staff_name VARCHAR(50) NOT NULL, 
	next_action_date VARCHAR(20), 
	created_at DATETIME NOT NULL, inquiry_source VARCHAR(50) DEFAULT 'DIRECT_CALL', media_project_id VARCHAR(36), is_duplicate BOOLEAN DEFAULT 0, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);

DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
	id VARCHAR(36) NOT NULL, 
	vehicle_id VARCHAR(36) NOT NULL, 
	transaction_type VARCHAR(20) NOT NULL, 
	amount INTEGER NOT NULL, 
	party_name VARCHAR(50) NOT NULL, 
	party_contact VARCHAR(30), 
	transaction_date VARCHAR(20) NOT NULL, 
	settlement_status VARCHAR(20) NOT NULL, 
	document_id VARCHAR(36), 
	notes TEXT, 
	is_demo BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, dealer_commission_amount INTEGER DEFAULT 0, chamart_net_profit INTEGER DEFAULT 0, operating_cost INTEGER DEFAULT 0, attribution_type VARCHAR(30) DEFAULT 'ORGANIC_WALKIN', media_project_id VARCHAR(36), is_verified_sale BOOLEAN DEFAULT 1, is_test_record BOOLEAN DEFAULT 0, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
);

DROP TABLE IF EXISTS dealer_rights_ledgers;

CREATE TABLE dealer_rights_ledgers (
	id VARCHAR(36) NOT NULL, 
	vehicle_id VARCHAR(36) NOT NULL, 
	dealer_id VARCHAR(36), 
	sale_allowed BOOLEAN NOT NULL, 
	photo_allowed BOOLEAN NOT NULL, 
	video_allowed BOOLEAN NOT NULL, 
	allowed_channels_json TEXT NOT NULL, 
	valid_until VARCHAR(20), 
	is_revoked BOOLEAN NOT NULL, 
	revoked_at DATETIME, 
	revoked_reason VARCHAR(255), 
	approved_by VARCHAR(50) NOT NULL, 
	dealer_commission_pct FLOAT NOT NULL, 
	chamart_share_pct FLOAT NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (id), 
	FOREIGN KEY(dealer_id) REFERENCES dealers (id)
);

DROP TABLE IF EXISTS platform_publishing_records;

CREATE TABLE platform_publishing_records (
                id VARCHAR(36) PRIMARY KEY,
                vehicle_id VARCHAR(36) NOT NULL,
                platform VARCHAR(30) NOT NULL,
                publishing_status VARCHAR(30) DEFAULT 'DRAFT',
                is_ready BOOLEAN DEFAULT 0,
                missing_fields_json TEXT DEFAULT '[]',
                warnings_json TEXT DEFAULT '[]',
                mapped_payload_json TEXT DEFAULT '{}',
                external_listing_id VARCHAR(50),
                last_validated_at DATETIME,
                last_exported_at DATETIME,
                error_message TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            );


CREATE TABLE IF NOT EXISTS admin_sessions (
    token VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    username VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL
);



CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(36),
    details_json TEXT DEFAULT '{}',
    ip_address VARCHAR(50),
    created_at DATETIME NOT NULL
);
