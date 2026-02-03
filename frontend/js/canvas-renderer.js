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
     * Get auto-calculated position from backend occupancy tracker.
     * @param {string} elementId - Element ID
     * @param {string} elementType - METRICS, CHART, TABLE, IMAGE, TEXT_BOX, etc.
     * @param {number} width - Width in grid columns
     * @param {number} height - Height in grid rows
     * @returns {Promise<{gridRow: string, gridColumn: string}>}
     */
    async getAutoPosition(elementId, elementType, width, height) {
        const sessionId = window.sessionManager?.getSessionId?.() || 'default';

        try {
            const response = await fetch('/api/position/auto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    element_id: elementId,
                    element_type: elementType,
                    width: width,
                    height: height
                })
            });

            if (!response.ok) {
                throw new Error(`Position API error: ${response.status}`);
            }

            const data = await response.json();
            console.log('[Canvas] Backend auto-position:', data.grid_row, data.grid_column);
            return {
                gridRow: data.grid_row,
                gridColumn: data.grid_column
            };
        } catch (error) {
            console.error('[Canvas] Auto-position API failed, using fallback:', error);
            // Fallback to default top-left position
            return {
                gridRow: `4/${4 + height}`,
                gridColumn: `2/${2 + width}`
            };
        }
    }

    /**
     * Notify backend when an element is removed (to free grid cells).
     * @param {string} elementId - Element ID to remove from tracking
     */
    async notifyElementRemoved(elementId) {
        const sessionId = window.sessionManager?.getSessionId?.() || 'default';

        try {
            await fetch(`/api/position/${sessionId}/elements/${elementId}`, {
                method: 'DELETE'
            });
            console.log('[Canvas] Notified backend of element removal:', elementId);
        } catch (error) {
            console.warn('[Canvas] Failed to notify backend of removal:', error);
        }
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
     * Uses backend auto-positioning when useAutoPosition is true.
     * @param {string} html - HTML content
     * @param {object} position - Grid position (optional)
     * @param {object} options - Additional options including useAutoPosition
     * @returns {Promise<string>} - Element ID
     */
    async insertElement(html, position = null, options = {}) {
        const defaultPosition = {
            gridRow: '4/18',
            gridColumn: '2/32'
        };

        const elementId = options.elementId || 'el_' + Date.now();
        const useAutoPosition = options.useAutoPosition === true;

        let finalPosition = position || defaultPosition;

        // If auto-position enabled, get position from backend
        if (useAutoPosition && options.positionWidth && options.positionHeight) {
            const autoPos = await this.getAutoPosition(
                elementId,
                options.elementType || 'TEXT_BOX',
                options.positionWidth,
                options.positionHeight
            );
            finalPosition = {
                gridRow: autoPos.gridRow,
                gridColumn: autoPos.gridColumn
            };
        }

        this.sendCommand('insertTextBox', {
            elementId: elementId,
            slideIndex: 0,
            content: html,
            gridRow: finalPosition.gridRow,
            gridColumn: finalPosition.gridColumn,
            positionWidth: options.positionWidth,
            positionHeight: options.positionHeight,
            skipAutoSize: true,  // Position already calculated by backend
            draggable: true,
            resizable: true
        });

        console.log('[Canvas] insertElement with useAutoPosition:', useAutoPosition,
                    'position:', finalPosition.gridRow, finalPosition.gridColumn);

        // Track locally
        this.elements.push({
            id: elementId,
            html: html,
            position: finalPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        return elementId;
    }

    /**
     * Extract body content from complete HTML document
     * Backend wraps chart HTML in <!DOCTYPE html><html>... for iframe srcdoc
     * For direct innerHTML injection, we need just the body content
     * v7.5.17: Strip HTML wrapper for insertChart compatibility
     * @param {string} html - Potentially complete HTML document
     * @returns {string} - Extracted body content with scripts preserved
     */
    _extractBodyContent(html) {
        // If it's a complete HTML document, extract body content
        if (html.includes('<!DOCTYPE') || html.includes('<html')) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Get all scripts from head (Chart.js CDN, ApexCharts, etc.)
            const headScripts = Array.from(doc.head.querySelectorAll('script'));

            // Get body content
            const bodyContent = doc.body.innerHTML;

            // Reconstruct: scripts first, then body content
            const scriptTags = headScripts.map(s => s.outerHTML).join('\n');
            const result = scriptTags + '\n' + bodyContent;

            console.log('[Canvas] Extracted body content from HTML document');
            return result;
        }
        return html;
    }

    /**
     * Insert chart element using Layout Service's insertChart command
     * Uses backend auto-positioning when useAutoPosition is true.
     * v7.5.16: Use insertChart (not insertTextBox) for proper drag handling
     * v7.5.17: Strip HTML document wrapper before sending
     * v7.5.24: Backend auto-positioning via occupancy tracker
     *
     * @param {string} html - Chart HTML from analytics service
     * @param {object} position - Grid position (optional)
     * @param {string} elementId - Optional element ID for persistence
     * @param {object} options - Additional options including useAutoPosition
     * @returns {Promise<string>} - Element ID
     */
    async insertChart(html, position = null, elementId = null, options = {}) {
        // Charts default to 16×12 grids (4:3 ratio) at content safe zone
        const defaultPosition = {
            gridRow: '4/16',      // Row 4 to 16 = 12 rows
            gridColumn: '2/18'    // Col 2 to 18 = 16 cols
        };

        // Use provided elementId or generate one
        const id = elementId || ('chart_' + Date.now());

        // Extract body content from HTML document wrapper
        const cleanHtml = this._extractBodyContent(html);

        const useAutoPosition = options.useAutoPosition === true;
        const width = options.positionWidth || 14;
        const height = options.positionHeight || 10;

        let finalPosition = position || defaultPosition;

        // If auto-position enabled, get position from backend
        if (useAutoPosition) {
            const autoPos = await this.getAutoPosition(id, 'CHART', width, height);
            finalPosition = {
                gridRow: autoPos.gridRow,
                gridColumn: autoPos.gridColumn
            };
        }

        // Use insertChart command for proper chart handling
        this.sendCommand('insertChart', {
            id: id,
            slideIndex: 0,
            chartHtml: cleanHtml,
            gridRow: finalPosition.gridRow,
            gridColumn: finalPosition.gridColumn,
            positionWidth: width,
            positionHeight: height,
            draggable: true,
            resizable: true
        });

        // Track locally with type indicator
        this.elements.push({
            id: id,
            type: 'chart',
            html: html,
            position: finalPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        console.log('[Canvas] Chart inserted with useAutoPosition:', useAutoPosition,
                    'position:', finalPosition.gridRow, finalPosition.gridColumn);
        return id;
    }

    /**
     * Insert image element
     * Uses backend auto-positioning when useAutoPosition is true.
     * v7.5.24: Backend auto-positioning via occupancy tracker
     * @param {string} html - HTML content with image
     * @param {object} position - Grid position (optional) with grid_row and grid_column
     * @param {string} elementId - Optional element ID from backend
     * @param {object} options - Additional options including useAutoPosition
     * @returns {Promise<string>} - Element ID
     */
    async insertImage(html, position = null, elementId = null, options = {}) {
        // Default full content area
        const defaultPosition = {
            gridRow: '4/18',
            gridColumn: '2/32'
        };

        // Use provided elementId or generate one
        const id = elementId || ('img_' + Date.now());

        const useAutoPosition = options.useAutoPosition === true;
        const width = options.positionWidth || 14;
        const height = options.positionHeight || 10;

        // Convert backend position format (grid_row/grid_column) to frontend format (gridRow/gridColumn)
        let finalPosition = {
            gridRow: position?.grid_row || position?.gridRow || defaultPosition.gridRow,
            gridColumn: position?.grid_column || position?.gridColumn || defaultPosition.gridColumn
        };

        // If auto-position enabled, get position from backend
        if (useAutoPosition) {
            const autoPos = await this.getAutoPosition(id, 'IMAGE', width, height);
            finalPosition = {
                gridRow: autoPos.gridRow,
                gridColumn: autoPos.gridColumn
            };
        }

        // Use insertImage - Layout Service handles image rendering
        this.sendCommand('insertImage', {
            id: id,
            slideIndex: 0,
            imageUrl: null,  // Using HTML content instead
            imageHtml: html,
            gridRow: finalPosition.gridRow,
            gridColumn: finalPosition.gridColumn,
            positionWidth: width,
            positionHeight: height,
            skipAutoSize: true,  // Position already calculated by backend
            draggable: true,
            resizable: true
        });

        // Track locally with type indicator
        this.elements.push({
            id: id,
            type: 'image',
            html: html,
            position: finalPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        console.log('[Canvas] Image inserted with useAutoPosition:', useAutoPosition,
                    'position:', finalPosition.gridRow, finalPosition.gridColumn);
        return id;
    }

    /**
     * Insert diagram element (via Diagram Generator v3.0)
     * Uses backend auto-positioning when useAutoPosition is true.
     * @param {string} html - Diagram HTML content
     * @param {object} position - Grid position (optional) with grid_row and grid_column
     * @param {string} elementId - Optional element ID from backend
     * @param {object} options - Additional options including useAutoPosition, diagramType
     * @returns {Promise<string>} - Element ID
     */
    async insertDiagram(html, position = null, elementId = null, options = {}) {
        // Default full content area for diagrams
        const defaultPosition = {
            gridRow: '4/18',
            gridColumn: '2/32'
        };

        // Use provided elementId or generate one
        const id = elementId || ('diagram_' + Date.now());

        // Extract body content from HTML document wrapper
        const cleanHtml = this._extractBodyContent(html);

        const useAutoPosition = options.useAutoPosition === true;
        const width = options.positionWidth || 30;
        const height = options.positionHeight || 14;
        const diagramType = options.diagramType || 'DIAGRAM';

        // Convert backend position format to frontend format
        let finalPosition = {
            gridRow: position?.grid_row || position?.gridRow || defaultPosition.gridRow,
            gridColumn: position?.grid_column || position?.gridColumn || defaultPosition.gridColumn
        };

        // If auto-position enabled, get position from backend
        if (useAutoPosition) {
            const autoPos = await this.getAutoPosition(id, diagramType, width, height);
            finalPosition = {
                gridRow: autoPos.gridRow,
                gridColumn: autoPos.gridColumn
            };
        }

        // Use insertDiagram command for Layout Service (uses "diagram" element type)
        this.sendCommand('insertDiagram', {
            id: id,
            slideIndex: 0,
            diagramHtml: cleanHtml,
            gridRow: finalPosition.gridRow,
            gridColumn: finalPosition.gridColumn,
            positionWidth: width,
            positionHeight: height,
            draggable: true,
            resizable: true
        });

        // Force iframe to reload the presentation from Layout Service
        // The diagram was already added by the backend, so reload shows it immediately
        this.sendCommand('reloadPresentation', {});

        // Track locally with type indicator
        this.elements.push({
            id: id,
            type: 'diagram',
            diagramType: diagramType,
            html: html,
            position: finalPosition
        });

        this.updateElementCount();
        this.hidePlaceholder();

        console.log('[Canvas] Diagram inserted:', diagramType,
                    'useAutoPosition:', useAutoPosition,
                    'position:', finalPosition.gridRow, finalPosition.gridColumn);
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
     * Notifies backend to free grid cells.
     * @param {string} elementId - Element ID
     */
    deleteElement(elementId) {
        this.sendCommand('deleteElement', {
            elementId: elementId
        });

        // Remove from local tracking
        this.elements = this.elements.filter(e => e.id !== elementId);
        this.updateElementCount();

        // Notify backend to free grid cells
        this.notifyElementRemoved(elementId);
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
     * Also clears backend occupancy tracking.
     */
    async clearElements() {
        // Delete all tracked elements
        this.elements.forEach(element => {
            this.sendCommand('deleteElement', { elementId: element.id });
        });

        this.elements = [];
        this.updateElementCount();

        // Clear backend occupancy tracking
        const sessionId = window.sessionManager?.getSessionId?.() || 'default';
        try {
            await fetch(`/api/position/${sessionId}/clear`, { method: 'DELETE' });
            console.log('[Canvas] Backend occupancy cleared');
        } catch (error) {
            console.warn('[Canvas] Failed to clear backend occupancy:', error);
        }

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
