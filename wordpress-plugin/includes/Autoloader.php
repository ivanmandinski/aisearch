<?php
/**
 * Autoloader
 * 
 * PSR-4 compliant autoloader for the Hybrid Search plugin.
 * Automatically loads classes based on namespace and file structure.
 * 
 * @package HybridSearch
 * @since 2.0.0
 */

namespace HybridSearch;

class Autoloader {
    
    /**
     * Namespace prefix
     * 
     * @var string
     */
    private $prefix;
    
    /**
     * Base directory
     * 
     * @var string
     */
    private $base_dir;
    
    /**
     * Constructor
     * 
     * @param string $prefix Namespace prefix
     * @param string $base_dir Base directory for the prefix
     */
    public function __construct($prefix, $base_dir) {
        $this->prefix = $prefix;
        $this->base_dir = rtrim($base_dir, '\\/') . DIRECTORY_SEPARATOR;
    }
    
    /**
     * Register the autoloader
     * 
     * @since 2.0.0
     */
    public function register() {
        spl_autoload_register([$this, 'loadClass']);
    }
    
    /**
     * Load class
     * 
     * @param string $class Class name
     * @since 2.0.0
     */
    public function loadClass($class) {
        // Check if the class uses the namespace prefix
        $len = strlen($this->prefix);
        if (strncmp($this->prefix, $class, $len) !== 0) {
            return;
        }
        
        // Get the relative class name
        $relative_class = substr($class, $len);
        
        // Replace the namespace prefix with the base directory, replace namespace
        // separators with directory separators in the relative class name, append
        // with .php
        $file = $this->base_dir . str_replace('\\', DIRECTORY_SEPARATOR, $relative_class) . '.php';
        
        // If the file exists, require it
        if (file_exists($file)) {
            require $file;
        }
    }
}

// Register the autoloader
$autoloader = new Autoloader(
    'HybridSearch\\',
    HYBRID_SEARCH_PLUGIN_PATH . 'includes'
);
$autoloader->register();

