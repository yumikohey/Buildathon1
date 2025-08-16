-- Initial Django schema migration for Visual Memory Search App
-- This creates all the necessary tables for Django and the screenshots app

-- Django built-in tables
CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE(app_label, model)
);

CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id),
    codename VARCHAR(100) NOT NULL,
    UNIQUE(content_type_id, codename)
);

CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id),
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
    UNIQUE(group_id, permission_id)
);

CREATE TABLE IF NOT EXISTS auth_user (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_user_groups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    group_id INTEGER NOT NULL REFERENCES auth_group(id),
    UNIQUE(user_id, group_id)
);

CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
    UNIQUE(user_id, permission_id)
);

CREATE TABLE IF NOT EXISTS django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMP WITH TIME ZONE NOT NULL,
    object_id TEXT,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL CHECK (action_flag >= 0),
    change_message TEXT NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id),
    user_id INTEGER NOT NULL REFERENCES auth_user(id)
);

CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session(expire_date);

-- Screenshots app tables
CREATE TABLE IF NOT EXISTS screenshots_screenshot (
    id SERIAL PRIMARY KEY,
    image VARCHAR(100) NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    extracted_text TEXT,
    ui_elements TEXT,
    visual_patterns TEXT,
    color_context TEXT,
    error_states TEXT,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    file_created_at TIMESTAMP WITH TIME ZONE,
    folder_path VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS screenshots_searchresult (
    id SERIAL PRIMARY KEY,
    screenshot_id INTEGER NOT NULL REFERENCES screenshots_screenshot(id),
    query TEXT NOT NULL,
    relevance_score DECIMAL(5,4) NOT NULL,
    text_score DECIMAL(5,4) NOT NULL,
    visual_score DECIMAL(5,4) NOT NULL,
    ui_score DECIMAL(5,4) NOT NULL,
    color_score DECIMAL(5,4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS screenshots_batchjob (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    total_screenshots INTEGER NOT NULL,
    processed_screenshots INTEGER NOT NULL DEFAULT 0,
    user_id INTEGER NOT NULL REFERENCES auth_user(id)
);

CREATE TABLE IF NOT EXISTS screenshots_batchrequest (
    id SERIAL PRIMARY KEY,
    batch_job_id INTEGER NOT NULL REFERENCES screenshots_batchjob(id),
    screenshot_id INTEGER NOT NULL REFERENCES screenshots_screenshot(id),
    request_data TEXT NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS screenshots_screenshot_user_id_idx ON screenshots_screenshot(user_id);
CREATE INDEX IF NOT EXISTS screenshots_screenshot_processed_idx ON screenshots_screenshot(processed);
CREATE INDEX IF NOT EXISTS screenshots_searchresult_screenshot_id_idx ON screenshots_searchresult(screenshot_id);
CREATE INDEX IF NOT EXISTS screenshots_searchresult_relevance_score_idx ON screenshots_searchresult(relevance_score);
CREATE INDEX IF NOT EXISTS screenshots_batchjob_user_id_idx ON screenshots_batchjob(user_id);
CREATE INDEX IF NOT EXISTS screenshots_batchjob_status_idx ON screenshots_batchjob(status);

-- Grant permissions to authenticated users
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO authenticated;

-- Grant basic read access to anonymous users (for public features if needed)
GRANT SELECT ON screenshots_screenshot TO anon;
GRANT SELECT ON screenshots_searchresult TO anon;
