-- Create creators table with all required fields
CREATE TABLE IF NOT EXISTS creators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    profile_url TEXT NOT NULL UNIQUE,
    handle TEXT,
    display_name TEXT,
    bio TEXT,
    niche TEXT,                          -- Auto-detected category
    public_contact_email TEXT,
    location TEXT,
    follower_count BIGINT,
    following_count BIGINT,
    post_count BIGINT,
    engagement_rate FLOAT,               -- Avg engagement across posts
    top_posts JSONB,                     -- [{url, timestamp, views, likes, comments, caption, engagement_rate}]
    recent_posts_sample JSONB,           -- 5 most recent posts
    avatar_url TEXT,
    raw JSONB,                           -- Optional full data dump
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    inserted_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_creators_source ON creators (source);
CREATE INDEX IF NOT EXISTS idx_creators_handle ON creators (handle);
CREATE INDEX IF NOT EXISTS idx_creators_niche ON creators (niche);
CREATE UNIQUE INDEX IF NOT EXISTS idx_creators_profile_url ON creators (profile_url);
CREATE INDEX IF NOT EXISTS idx_creators_scraped_at ON creators (scraped_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_creators_updated_at 
    BEFORE UPDATE ON creators 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
