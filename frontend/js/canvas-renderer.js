/**
 * Canvas Renderer for Text Labs
 * Handles canvas preview and iframe communication
 */

class CanvasRenderer {
    constructor(iframeId, gridOverlayId, placeholderId) {
        this.iframe = document.getElementById(iframeId);
        this.gridOverlay = document.getElementById(gridOverlayId);
        this.placeholder = document.getElementById(placeholderId);
        this.wrapper = document.getElementById('canvas-wrapper');
        this.elements = [];
        this.isLoaded = false;
        this.pendingMessages = [];
        this.currentScale = 0.75;

        this.setupMessageListener();
        this.setupResizeHandler();
        // Initial scale calculation
        setTimeout(() => this.updateScale(), 100);
    }

    /**
     * Set up window resize handler to recalculate scale
     */
    setupResizeHandler() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.updateScale(), 150);
        });
    }

    /**
     * Calculate and apply the appropriate scale for the iframe
     */
    updateScale() {
        if (!this.wrapper) return;

        const wrapperRect = this.wrapper.getBoundingClientRect();
        const wrapperWidth = wrapperRect.width;
        const wrapperHeight = wrapperRect.height;

        // Calculate scale based on wrapper size
        const scaleX = wrapperWidth / 1920;
        const scaleY = wrapperHeight / 1080;
        const scale = Math.min(scaleX, scaleY);

        this.currentScale = scale;
        this.iframe.style.transform = `scale(${scale})`;

        // Update the status bar
        const scalePercent = Math.round(scale * 100);
        const sizeEl = document.getElementById('canvas-size');
        if (sizeEl) {
            sizeEl.textContent = `1920×1080 @ ${scalePercent}%`;
        }

        console.log(`[Canvas] Scale updated: ${scalePercent}%`);
    }

    /**
     * Load presentation viewer in iframe
     * @param {string} viewerUrl - URL of the presentation viewer
     */
    async loadPresentation(viewerUrl) {
        console.log('[Canvas] Loading presentation:', viewerUrl);

        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                console.warn('[Canvas] Viewer load timeout, continuing anyway');
                this.isLoaded = true;
                resolve();
            }, 5000);

            this.iframe.onload = () => {
                clearTimeout(timeout);
                console.log('[Canvas] Viewer loaded');
                this.isLoaded = true;
                this.hidePlaceholder();
                this.processPendingMessages();
                this.updateScale();  // Recalculate scale after load
                resolve();
            };

            this.iframe.onerror = (error) => {
                clearTimeout(timeout);
                console.error('[Canvas] Viewer load error:', error);
                reject(error);
            };

            this.iframe.src = viewerUrl;
        });
    }

    /**
     * Send postMessage command to iframe
     * @param {string} action - Action name
     * @param {object} params - Action parameters
     */
    sendCommand(action, params = {}) {
        const message = { action, params, source: 'text-labs' };

        if (!this.isLoaded) {
            console.log('[Canvas] Queuing message for later:', action);
            this.pendingMessages.push(message);
            return;
        }

        try {
            this.iframe.contentWindow.postMessage(message, '*');
            console.log('[Canvas] Sent command:', action, params);
        } catch (error) {
            console.error('[Canvas] Failed to send command:', error);
        }
    }

    /**
     * Process queued messages after iframe loads
     */
    processPendingMessages() {
        while (this.pendingMessages.length > 0) {
            const message = this.pendingMessages.shift();
            this.sendCommand(message.action, message.params);
        }
    }

    /**
     * Insert generated HTML as a text box element
     * @param {string} html - HTML content
     * @param {object} position - Grid position (optional)
     */
    insertElement(html, position = null) {
        const defaultPosition = {
            gridRow: '4/18',
            gridColumn: '2/32'
        };

        const elementId = 'el_' + Date.now();

        this.sendCommand('insertTextBox', {
            elementId: elementId,
            slideIndex: 0,
            content: html,
            gridRow: position?.gridRow || defaultPosition.gridRow,
            gridColumn: position?.gridColumn || defaultPosition.gridColumn,
            skipAutoSize: !!position,  // Skip auto-sizing when position explicitly provided
            draggable: true,
            resizable: true
        });

        // Track locally
        this.elements.push({
            id: elementId,
            html: html,
            position: position || defaultPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        return elementId;
    }

    /**
     * Insert chart element using Layout Service's insertChart command
     * v7.5.16: Use insertChart (not insertTextBox) for proper drag handling
     * - No iframe wrapping - Layout Service handles script execution
     * - Gets .inserted-chart class with proper drag handling
     * - Canvas pointer-events managed during drag
     *
     * @param {string} html - Chart HTML from analytics service
     * @param {object} position - Grid position (optional)
     * @param {string} elementId - Optional element ID for persistence
     */
    insertChart(html, position = null, elementId = null) {
        // Charts get a larger default area
        const defaultPosition = {
            gridRow: '3/19',
            gridColumn: '2/32'
        };

        // Use provided elementId or generate one
        const id = elementId || ('chart_' + Date.now());

        // v7.5.16: Use insertChart command for proper chart handling
        // - No iframe wrapping - Layout Service handles script execution
        // - Gets .inserted-chart class with proper drag handling
        // - Canvas pointer-events managed during drag
        this.sendCommand('insertChart', {
            id: id,
            slideIndex: 0,
            chartHtml: html,  // Raw HTML, not iframe-wrapped
            gridRow: position?.gridRow || defaultPosition.gridRow,
            gridColumn: position?.gridColumn || defaultPosition.gridColumn,
            draggable: true,
            resizable: true
        });

        // Track locally with type indicator
        this.elements.push({
            id: id,
            type: 'chart',
            html: html,
            position: position || defaultPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        console.log('[Canvas] Chart inserted via insertChart command:', id);
        return id;
    }

    /**
     * Insert image element
     * @param {string} html - HTML content with image
     * @param {object} position - Grid position (optional) with grid_row and grid_column
     * @param {string} elementId - Optional element ID from backend
     */
    insertImage(html, position = null, elementId = null) {
        // Default full content area
        const defaultPosition = {
            gridRow: '4/18',
            gridColumn: '2/32'
        };

        // Use provided elementId or generate one
        const id = elementId || ('img_' + Date.now());

        // Convert backend position format (grid_row/grid_column) to frontend format (gridRow/gridColumn)
        const gridPosition = {
            gridRow: position?.grid_row || position?.gridRow || defaultPosition.gridRow,
            gridColumn: position?.grid_column || position?.gridColumn || defaultPosition.gridColumn
        };

        // Use insertTextBox - Layout Service renders the image HTML
        this.sendCommand('insertTextBox', {
            elementId: id,
            slideIndex: 0,
            content: html,
            gridRow: gridPosition.gridRow,
            gridColumn: gridPosition.gridColumn,
            skipAutoSize: !!position,  // Skip auto-sizing when position explicitly provided
            draggable: true,
            resizable: true
        });

        // Track locally with type indicator
        this.elements.push({
            id: id,
            type: 'image',
            html: html,
            position: gridPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        console.log('[Canvas] Image inserted:', id);
        return id;
    }

    /**
     * Update content of an existing element
     * @param {string} elementId - Element ID
     * @param {string} html - New HTML content
     */
    updateElementContent(elementId, html) {
        this.sendCommand('updateTextBoxContent', {
            elementId: elementId,
            content: html
        });

        // Update local tracking
        const element = this.elements.find(e => e.id === elementId);
        if (element) {
            element.html = html;
        }
    }

    /**
     * Delete an element
     * @param {string} elementId - Element ID
     */
    deleteElement(elementId) {
        this.sendCommand('deleteElement', {
            elementId: elementId
        });

        // Remove from local tracking
        this.elements = this.elements.filter(e => e.id !== elementId);
        this.updateElementCount();
    }

    /**
     * Hide the default content slot in C01 template
     */
    hideContentSlot() {
        this.sendCommand('toggleElement', {
            selector: '[data-slot="content"]',
            visible: false
        });
        console.log('[Canvas] Hiding content slot');
    }

    /**
     * Show the default content slot
     */
    showContentSlot() {
        this.sendCommand('toggleElement', {
            selector: '[data-slot="content"]',
            visible: true
        });
    }

    /**
     * Toggle edit mode in the viewer
     */
    toggleEditMode() {
        this.sendCommand('toggleEditMode', {});
    }

    /**
     * Toggle grid overlay visibility
     */
    toggleGrid() {
        this.gridOverlay.classList.toggle('hidden');
        return !this.gridOverlay.classList.contains('hidden');
    }

    /**
     * Show grid overlay
     */
    showGrid() {
        this.gridOverlay.classList.remove('hidden');
    }

    /**
     * Hide grid overlay
     */
    hideGrid() {
        this.gridOverlay.classList.add('hidden');
    }

    /**
     * Clear all elements from canvas
     */
    clearElements() {
        // Delete all tracked elements
        this.elements.forEach(element => {
            this.sendCommand('deleteElement', { elementId: element.id });
        });

        this.elements = [];
        this.updateElementCount();

        // Reload presentation to fully reset
        this.sendCommand('reloadPresentation', {});
    }

    /**
     * Update element count display
     */
    updateElementCount() {
        const countEl = document.getElementById('element-count');
        if (countEl) {
            countEl.textContent = `Elements: ${this.elements.length}`;
        }
    }

    /**
     * Hide placeholder when content is added
     */
    hidePlaceholder() {
        if (this.placeholder) {
            this.placeholder.classList.add('hidden');
        }
    }

    /**
     * Show placeholder when canvas is empty
     */
    showPlaceholder() {
        if (this.placeholder && this.elements.length === 0) {
            this.placeholder.classList.remove('hidden');
        }
    }

    /**
     * Get current element count
     */
    getElementCount() {
        return this.elements.length;
    }

    /**
     * Get all tracked elements
     */
    getElements() {
        return [...this.elements];
    }

    /**
     * Set up message listener for responses from iframe
     */
    setupMessageListener() {
        window.addEventListener('message', (event) => {
            // Validate message source
            if (!event.data || event.data.source === 'text-labs') {
                return; // Ignore our own messages
            }

            const { action, success, elementId, error } = event.data;

            switch (action) {
                case 'insertTextBox':
                    if (success) {
                        console.log('[Canvas] Element inserted:', elementId);
                    } else {
                        console.error('[Canvas] Element insert failed:', error);
                    }
                    break;

                case 'insertChart':
                    if (success) {
                        console.log('[Canvas] Chart inserted:', elementId);
                    } else {
                        console.error('[Canvas] Chart insert failed:', error);
                    }
                    break;

                case 'deleteElement':
                    if (success) {
                        console.log('[Canvas] Element deleted:', elementId);
                    }
                    break;

                case 'elementSelected':
                    console.log('[Canvas] Element selected:', elementId);
                    break;

                case 'elementMoved':
                    console.log('[Canvas] Element moved:', event.data.position);
                    break;

                case 'viewerReady':
                    console.log('[Canvas] Viewer ready');
                    this.isLoaded = true;
                    this.processPendingMessages();
                    break;

                default:
                    // Ignore unknown actions
                    break;
            }
        });
    }

    /**
     * Set connection status indicator
     * @param {string} status - 'connected', 'disconnected', or 'connecting'
     */
    setConnectionStatus(status) {
        const statusDot = document.getElementById('connection-status');
        if (statusDot) {
            statusDot.classList.remove('connected', 'disconnected', 'connecting');
            statusDot.classList.add(status);
        }
    }
}

// Export as global
window.CanvasRenderer = CanvasRenderer;
