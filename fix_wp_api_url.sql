-- Fix WordPress Hybrid Search API URL Configuration
-- Run this in your WordPress database

-- Set the Railway API URL
INSERT INTO wp_options (option_name, option_value, autoload) 
VALUES ('hybrid_search_api_url', 'https://aisearch-production-fab7.up.railway.app', 'yes')
ON DUPLICATE KEY UPDATE 
    option_value = 'https://aisearch-production-fab7.up.railway.app';

-- Verify the setting was saved
SELECT option_name, option_value 
FROM wp_options 
WHERE option_name = 'hybrid_search_api_url';

-- Optional: Check all hybrid search settings
SELECT option_name, option_value 
FROM wp_options 
WHERE option_name LIKE 'hybrid_search%' 
ORDER BY option_name;

