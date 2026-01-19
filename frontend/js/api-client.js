/**
 * API Client for Text Labs Backend
 * Handles all HTTP communication with the backend
 */

class TextLabsAPI {
    constructor(baseUrl = 'http://localhost:8080') {
        this.baseUrl = baseUrl;
    }

    /**
     * Make a fetch request with standard options
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`[API] Error ${options.method || 'GET'} ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * Send a chat message to create/modify elements
     * @param {string} sessionId - Session identifier
     * @param {string} message - Natural language message
     * @param {object} options - Optional config (e.g., imageConfig for IMAGE components)
     */
    async sendChatMessage(sessionId, message, options = {}) {
        console.log('[API] Sending chat message:', message);
        const payload = {
            session_id: sessionId,
            message: message
        };
        // Include image_config if provided (bypasses natural language parsing for positioning)
        if (options.imageConfig) {
            payload.image_config = options.imageConfig;
            console.log('[API] Including image_config:', options.imageConfig);
        }
        // Include position_config for TEXT_BOX, METRICS, TABLE (bypasses NLP parsing)
        if (options.positionConfig) {
            payload.position_config = options.positionConfig;
            console.log('[API] Including position_config:', options.positionConfig);
        }
        if (options.textboxConfig) {
            payload.textbox_config = options.textboxConfig;
            console.log('[API] Including textbox_config:', options.textboxConfig);
        }
        if (options.metricsConfig) {
            payload.metrics_config = options.metricsConfig;
            console.log('[API] Including metrics_config:', options.metricsConfig);
        }
        if (options.tableConfig) {
            payload.table_config = options.tableConfig;
            console.log('[API] Including table_config:', options.tableConfig);
        }
        if (options.chartConfig) {
            payload.chart_config = options.chartConfig;
            console.log('[API] Including chart_config:', options.chartConfig);
        }
        return this.request('/api/chat/message', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    /**
     * Get or create a presentation for the session
     * @param {string} sessionId - Session identifier
     */
    async getOrCreatePresentation(sessionId) {
        console.log('[API] Getting/creating presentation for session:', sessionId);
        return this.request(`/api/chat/presentation/${sessionId}`, {
            method: 'POST'
        });
    }

    /**
     * Get canvas state with all elements
     * @param {string} sessionId - Session identifier
     */
    async getCanvasState(sessionId) {
        console.log('[API] Getting canvas state for session:', sessionId);
        try {
            return await this.request(`/api/canvas/state/${sessionId}`);
        } catch (error) {
            if (error.message.includes('404')) {
                return null; // No state yet
            }
            throw error;
        }
    }

    /**
     * Create a new canvas session
     */
    async createSession() {
        console.log('[API] Creating new canvas session');
        return this.request('/api/canvas/session', {
            method: 'POST'
        });
    }

    /**
     * Clear all elements from canvas
     * @param {string} sessionId - Session identifier
     */
    async clearCanvas(sessionId) {
        console.log('[API] Clearing canvas for session:', sessionId);
        return this.request(`/api/canvas/state/${sessionId}`, {
            method: 'DELETE'
        });
    }

    /**
     * Get component info and configuration
     */
    async getComponentInfo() {
        console.log('[API] Getting component info');
        return this.request('/api/info');
    }

    /**
     * Health check
     */
    async healthCheck() {
        console.log('[API] Health check');
        return this.request('/health');
    }

    /**
     * Add an element directly to the canvas
     * @param {string} sessionId - Session identifier
     * @param {object} element - Element data
     */
    async addElement(sessionId, element) {
        console.log('[API] Adding element to canvas');
        return this.request(`/api/element/${sessionId}`, {
            method: 'POST',
            body: JSON.stringify(element)
        });
    }

    /**
     * Update an element
     * @param {string} sessionId - Session identifier
     * @param {string} elementId - Element identifier
     * @param {object} updates - Element updates
     */
    async updateElement(sessionId, elementId, updates) {
        console.log('[API] Updating element:', elementId);
        return this.request(`/api/element/${sessionId}/${elementId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
    }

    /**
     * Delete an element
     * @param {string} sessionId - Session identifier
     * @param {string} elementId - Element identifier
     */
    async deleteElement(sessionId, elementId) {
        console.log('[API] Deleting element:', elementId);
        return this.request(`/api/element/${sessionId}/${elementId}`, {
            method: 'DELETE'
        });
    }

    /**
     * Get chat history
     * @param {string} sessionId - Session identifier
     * @param {number} limit - Max messages to retrieve
     */
    async getChatHistory(sessionId, limit = 50) {
        console.log('[API] Getting chat history for session:', sessionId);
        return this.request(`/api/chat/history/${sessionId}?limit=${limit}`);
    }

    /**
     * Save session progress
     * @param {string} sessionId - Session identifier
     */
    async saveSession(sessionId) {
        console.log('[API] Saving session:', sessionId);
        return this.request(`/api/chat/save/${sessionId}`, {
            method: 'POST'
        });
    }
}

// Export as global
window.TextLabsAPI = TextLabsAPI;
