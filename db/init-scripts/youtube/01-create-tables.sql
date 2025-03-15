-- db/init-scripts/youtube/01-create-tables.sql

-- Create the transcripts table to match the YouTube DB schema
CREATE TABLE IF NOT EXISTS transcripts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_url VARCHAR(255) NOT NULL,
    channel VARCHAR(100),
    start_time FLOAT,
    end_time FLOAT,
    transcript TEXT,
    is_valid BOOLEAN DEFAULT FALSE,
    update_date DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Add some sample data
INSERT INTO transcripts 
    (video_url, channel, start_time, end_time, transcript, is_valid)
VALUES
    ('https://youtube.com/watch?v=abc123', 'TechChannel', 0.0, 15.5, 'Welcome to our tutorial on machine learning basics.', TRUE),
    ('https://youtube.com/watch?v=abc123', 'TechChannel', 15.5, 30.2, 'We will cover supervised and unsupervised learning.', TRUE),
    ('https://youtube.com/watch?v=def456', 'CookingWithAI', 0.0, 12.8, 'Today we are making a delicious AI-generated recipe.', TRUE),
    ('https://youtube.com/watch?v=def456', 'CookingWithAI', 12.8, 25.0, 'First, gather all the ingredients listed below.', TRUE),
    ('https://youtube.com/watch?v=ghi789', 'HistoryNow', 0.0, 20.0, 'The history of computing begins with early mechanical calculators.', TRUE);