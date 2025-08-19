/**
 * Image Optimizer and Lazy Loading Utility
 * Significantly improves image loading performance
 */

class ImageOptimizer {
    constructor() {
        this.observer = null;
        this.loadingImages = new Set();
        this.imageCache = new Map();
        this.init();
    }

    init() {
        // Initialize intersection observer for lazy loading
        this.initIntersectionObserver();
        
        // Preload critical images
        this.preloadCriticalImages();
        
        // Setup periodic cache cleanup
        setInterval(() => this.cleanupCache(), 300000); // Every 5 minutes
    }

    initIntersectionObserver() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.loadImage(entry.target);
                        this.observer.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px 0px', // Start loading 50px before image comes into view
                threshold: 0.01
            });
        }
    }

    /**
     * Optimize an image element for better performance
     */
    optimizeImage(img, options = {}) {
        const defaults = {
            lazy: true,
            thumbnail: true,
            thumbnailSize: '150x150',
            progressive: true,
            placeholder: true
        };
        
        const settings = { ...defaults, ...options };
        
        // Add loading attribute for native lazy loading
        if (settings.lazy && 'loading' in HTMLImageElement.prototype) {
            img.loading = 'lazy';
        }
        
        // Set thumbnail size if requested
        if (settings.thumbnail) {
            const originalSrc = img.src;
            if (originalSrc.includes('/unzipped_zips/')) {
                // Convert to thumbnail URL
                const thumbnailUrl = this.getThumbnailUrl(originalSrc, settings.thumbnailSize);
                img.src = thumbnailUrl;
                
                // Store original source for full-size loading
                img.dataset.fullSize = originalSrc;
            }
        }
        
        // Add progressive loading
        if (settings.progressive) {
            this.addProgressiveLoading(img);
        }
        
        // Add placeholder if requested
        if (settings.placeholder) {
            this.addPlaceholder(img);
        }
        
        // Setup lazy loading if intersection observer is available
        if (settings.lazy && this.observer) {
            this.observer.observe(img);
        } else if (settings.lazy) {
            // Fallback for browsers without intersection observer
            this.loadImage(img);
        }
        
        return img;
    }

    /**
     * Get thumbnail URL for an image
     */
    getThumbnailUrl(originalUrl, size = '150x150') {
        if (originalUrl.includes('/unzipped_zips/')) {
            // Convert to thumbnail endpoint
            return originalUrl.replace('/unzipped_zips/', '/thumbnail/') + '?size=' + size;
        }
        return originalUrl;
    }

    /**
     * Add progressive loading to an image
     */
    addProgressiveLoading(img) {
        const originalSrc = img.src;
        const fullSizeSrc = img.dataset.fullSize || originalSrc;
        
        // Load thumbnail first
        if (img.src !== fullSizeSrc) {
            img.addEventListener('load', () => {
                // After thumbnail loads, load full size
                setTimeout(() => {
                    if (img.dataset.fullSize) {
                        const fullImg = new Image();
                        fullImg.onload = () => {
                            img.src = fullImg.src;
                            img.classList.add('full-size-loaded');
                        };
                        fullImg.src = fullSizeSrc;
                    }
                }, 100);
            });
        }
    }

    /**
     * Add placeholder for image
     */
    addPlaceholder(img) {
        // Create a simple placeholder
        const placeholder = document.createElement('div');
        placeholder.className = 'image-placeholder';
        placeholder.style.cssText = `
            width: ${img.width || 150}px;
            height: ${img.height || 150}px;
            background: linear-gradient(45deg, #f0f0f0 25%, transparent 25%), 
                        linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), 
                        linear-gradient(45deg, transparent 75%, #f0f0f0 75%), 
                        linear-gradient(-45deg, transparent 75%, #f0f0f0 75%);
            background-size: 20px 20px;
            background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 12px;
        `;
        placeholder.textContent = 'Loading...';
        
        // Insert placeholder before image
        img.parentNode.insertBefore(placeholder, img);
        img.style.display = 'none';
        
        // Show image when loaded
        img.addEventListener('load', () => {
            img.style.display = '';
            if (placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
            }
        });
    }

    /**
     * Load an image (for lazy loading)
     */
    loadImage(img) {
        if (this.loadingImages.has(img)) return;
        
        this.loadingImages.add(img);
        
        // If image has a data-src attribute, use it
        if (img.dataset.src) {
            img.src = img.dataset.src;
            delete img.dataset.src;
        }
        
        // If image has a full-size source, load it
        if (img.dataset.fullSize) {
            img.src = img.dataset.fullSize;
            delete img.dataset.fullSize;
        }
        
        this.loadingImages.delete(img);
    }

    /**
     * Preload critical images
     */
    preloadCriticalImages() {
        const criticalImages = document.querySelectorAll('img[data-critical="true"]');
        criticalImages.forEach(img => this.loadImage(img));
    }

    /**
     * Optimize all images on the page
     */
    optimizeAllImages(options = {}) {
        const images = document.querySelectorAll('img:not([data-optimized])');
        images.forEach(img => {
            img.dataset.optimized = 'true';
            this.optimizeImage(img, options);
        });
    }

    /**
     * Clean up image cache
     */
    cleanupCache() {
        // Clear old cached images
        this.imageCache.clear();
        
        // Force garbage collection if available
        if (window.gc) {
            window.gc();
        }
    }

    /**
     * Preload images for a specific directory
     */
    preloadDirectory(directoryPath, size = '150x150') {
        // This could be used to preload thumbnails for a specific report
        console.log(`Preloading images from ${directoryPath} with size ${size}`);
    }
}

// Initialize the image optimizer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.imageOptimizer = new ImageOptimizer();
    
    // Optimize all existing images
    window.imageOptimizer.optimizeAllImages({
        lazy: true,
        thumbnail: true,
        progressive: true,
        placeholder: true
    });
    
    // Setup mutation observer to optimize dynamically added images
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const images = node.querySelectorAll ? node.querySelectorAll('img:not([data-optimized])') : [];
                    if (node.tagName === 'IMG' && !node.dataset.optimized) {
                        images.push(node);
                    }
                    images.forEach(img => {
                        img.dataset.optimized = 'true';
                        window.imageOptimizer.optimizeImage(img);
                    });
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ImageOptimizer;
}

