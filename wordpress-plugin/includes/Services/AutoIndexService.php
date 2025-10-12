<?php
/**
 * Auto-Index Service
 * 
 * Automatically indexes content when posts are saved/updated/deleted
 * 
 * @package HybridSearch\Services
 * @since 2.5.0
 */

namespace HybridSearch\Services;

use HybridSearch\API\SearchAPI;
use HybridSearch\Core\Logger;

class AutoIndexService {
    
    /**
     * Search API instance
     * 
     * @var SearchAPI
     */
    private $search_api;
    
    /**
     * Logger instance
     * 
     * @var Logger
     */
    private $logger;
    
    /**
     * Constructor
     * 
     * @param SearchAPI $search_api
     * @param Logger $logger
     */
    public function __construct(SearchAPI $search_api, Logger $logger) {
        $this->search_api = $search_api;
        $this->logger = $logger;
    }
    
    /**
     * Register WordPress hooks
     * 
     * @since 2.5.0
     */
    public function registerHooks() {
        // Index on post save/update
        add_action('save_post', [$this, 'onPostSave'], 10, 3);
        
        // Remove from index on post delete
        add_action('delete_post', [$this, 'onPostDelete'], 10, 1);
        
        // Handle post status transitions
        add_action('transition_post_status', [$this, 'onPostStatusChange'], 10, 3);
    }
    
    /**
     * Handle post save/update
     * 
     * @param int $post_id Post ID
     * @param \WP_Post $post Post object
     * @param bool $update Whether this is an update
     * @since 2.5.0
     */
    public function onPostSave($post_id, $post, $update) {
        // Skip autosaves and revisions
        if (wp_is_post_autosave($post_id) || wp_is_post_revision($post_id)) {
            return;
        }
        
        // Check if auto-indexing is enabled
        if (!get_option('hybrid_search_auto_index_enabled', true)) {
            return;
        }
        
        // Check if this post type should be indexed
        $selected_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
        if (!in_array($post->post_type, $selected_types)) {
            return;
        }
        
        // Only index published posts
        if ($post->post_status !== 'publish') {
            // If it was published before, remove it from index
            if ($update) {
                $this->removeFromIndex($post_id);
            }
            return;
        }
        
        $this->logger->info("Auto-indexing post: {$post->post_title} (ID: {$post_id})");
        
        // Index asynchronously (don't block post save)
        $this->indexPostAsync($post);
    }
    
    /**
     * Handle post deletion
     * 
     * @param int $post_id Post ID
     * @since 2.5.0
     */
    public function onPostDelete($post_id) {
        // Check if auto-indexing is enabled
        if (!get_option('hybrid_search_auto_index_enabled', true)) {
            return;
        }
        
        $this->logger->info("Removing post from index (ID: {$post_id})");
        $this->removeFromIndex($post_id);
    }
    
    /**
     * Handle post status changes
     * 
     * @param string $new_status New post status
     * @param string $old_status Old post status
     * @param \WP_Post $post Post object
     * @since 2.5.0
     */
    public function onPostStatusChange($new_status, $old_status, $post) {
        // Skip if auto-indexing disabled
        if (!get_option('hybrid_search_auto_index_enabled', true)) {
            return;
        }
        
        // Check if this post type should be indexed
        $selected_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
        if (!in_array($post->post_type, $selected_types)) {
            return;
        }
        
        // If changing from publish to something else, remove from index
        if ($old_status === 'publish' && $new_status !== 'publish') {
            $this->removeFromIndex($post->ID);
        }
        
        // If changing to publish, add to index
        if ($new_status === 'publish' && $old_status !== 'publish') {
            $this->indexPostAsync($post);
        }
    }
    
    /**
     * Index a single post asynchronously
     * 
     * @param \WP_Post $post Post object
     * @since 2.5.0
     */
    private function indexPostAsync($post) {
        // Schedule background task
        wp_schedule_single_event(time(), 'hybrid_search_index_single_post', [$post->ID]);
    }
    
    /**
     * Actually index a single post (called by WP-Cron)
     * 
     * @param int $post_id Post ID
     * @since 2.5.0
     */
    public function indexSinglePost($post_id) {
        $post = get_post($post_id);
        if (!$post) {
            return;
        }
        
        try {
            // Prepare post data for indexing
            $post_data = [
                'id' => (string) $post->ID,
                'title' => $post->post_title,
                'slug' => $post->post_name,
                'type' => $post->post_type,
                'url' => get_permalink($post->ID),
                'date' => $post->post_date,
                'modified' => $post->post_modified,
                'author' => get_the_author_meta('display_name', $post->post_author),
                'categories' => wp_get_post_categories($post->ID, ['fields' => 'names']),
                'tags' => wp_get_post_tags($post->ID, ['fields' => 'names']),
                'excerpt' => get_the_excerpt($post),
                'content' => wp_strip_all_tags($post->post_content),
                'word_count' => str_word_count(wp_strip_all_tags($post->post_content)),
            ];
            
            // Call Railway API to index this single document
            $api_url = get_option('hybrid_search_api_url', '');
            if (empty($api_url)) {
                $this->logger->error('API URL not configured for auto-indexing');
                return;
            }
            
            $response = wp_remote_post($api_url . '/index-single', [
                'method' => 'POST',
                'timeout' => 30,
                'headers' => ['Content-Type' => 'application/json'],
                'body' => json_encode(['document' => $post_data])
            ]);
            
            if (is_wp_error($response)) {
                $this->logger->error('Auto-index failed for post ' . $post_id . ': ' . $response->get_error_message());
            } else {
                $this->logger->info('Auto-indexed post: ' . $post->post_title);
                
                // Clear search cache since index changed
                $this->clearSearchCache();
            }
            
        } catch (\Exception $e) {
            $this->logger->error('Auto-index exception: ' . $e->getMessage());
        }
    }
    
    /**
     * Remove post from index
     * 
     * @param int $post_id Post ID
     * @since 2.5.0
     */
    private function removeFromIndex($post_id) {
        try {
            $api_url = get_option('hybrid_search_api_url', '');
            if (empty($api_url)) {
                return;
            }
            
            $response = wp_remote_request($api_url . '/delete-document/' . $post_id, [
                'method' => 'DELETE',
                'timeout' => 30,
            ]);
            
            if (!is_wp_error($response)) {
                $this->logger->info('Removed post from index (ID: ' . $post_id . ')');
                
                // Clear search cache
                $this->clearSearchCache();
            }
            
        } catch (\Exception $e) {
            $this->logger->error('Remove from index failed: ' . $e->getMessage());
        }
    }
    
    /**
     * Clear all search caches
     * 
     * @since 2.5.0
     */
    private function clearSearchCache() {
        global $wpdb;
        
        // Delete all hybrid search transients
        $wpdb->query("
            DELETE FROM {$wpdb->options}
            WHERE option_name LIKE '_transient_hybrid_search_%'
               OR option_name LIKE '_transient_timeout_hybrid_search_%'
        ");
        
        $this->logger->info('Cleared all search caches');
    }
}

