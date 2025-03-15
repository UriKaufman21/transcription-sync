-- db/init-scripts/mysql/01-create-tables.sql

-- Create the transcriptions table
CREATE TABLE IF NOT EXISTS transcriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    audio_id VARCHAR(255) NOT NULL,
    transcript TEXT,
    is_valid BOOLEAN DEFAULT FALSE,
    update_date DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    input_source VARCHAR(50) NOT NULL,
    UNIQUE KEY unique_audio_id (audio_id)
);

-- Create indexes for better performance
CREATE INDEX idx_audio_id ON transcriptions(audio_id);
CREATE INDEX idx_update_date ON transcriptions(update_date);
CREATE INDEX idx_input_source ON transcriptions(input_source);
CREATE INDEX idx_is_valid ON transcriptions(is_valid);

-- Create view for recent transcriptions
CREATE OR REPLACE VIEW recent_transcriptions AS
SELECT * FROM transcriptions
ORDER BY update_date DESC
LIMIT 100;

-- Create function to count transcriptions by source
DELIMITER //
CREATE FUNCTION count_by_source(source VARCHAR(50))
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE count INT;
    SELECT COUNT(*) INTO count FROM transcriptions WHERE input_source = source;
    RETURN count;
END //
DELIMITER ;