/**
 * Text Labs Main Application
 * Orchestrates all components and handles user interactions
 */

class TextLabsApp {
    constructor() {
        // Initialize services
        this.session = new SessionManager();
        this.api = new TextLabsAPI('http://localhost:8080');
        this.canvas = new CanvasRenderer('layout-viewer', 'grid-overlay', 'canvas-placeholder');
        this.modal = new AtomicModal('atomic-modal');

        // State
        this.currentMode = 'chat';
        this.componentInfo = null;
        this.presentationId = null;
        this.viewerUrl = null;
        this.isLoading = false;

        // DOM elements
        this.sessionIdEl = document.getElementById('session-id');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.chatSendBtn = document.getElementById('chat-send');
        this.suggestionsBar = document.getElementById('suggestions-bar');
        this.loadingOverlay = document.getElementById('loading-overlay');
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('[App] Initializing Text Labs...');

        // Display session ID
        this.sessionIdEl.textContent = this.session.getDisplayId();
        this.sessionIdEl.title = this.session.id;

        try {
            // Check backend health
            await this.api.healthCheck();
            this.canvas.setConnectionStatus('connected');

            // Get component info
            this.componentInfo = await this.api.getComponentInfo();
            console.log('[App] Component info loaded:', this.componentInfo);

            // Get or create presentation
            const presResult = await this.api.getOrCreatePresentation(this.session.id);
            if (presResult.presentation_id) {
                this.presentationId = presResult.presentation_id;
                this.viewerUrl = presResult.viewer_url;
                console.log('[App] Presentation ready:', this.presentationId);

                // Load viewer in canvas (if URL available)
                if (this.viewerUrl) {
                    await this.canvas.loadPresentation(this.viewerUrl);
                }
            }

            // Restore canvas state if any
            await this.restoreCanvasState();

        } catch (error) {
            console.error('[App] Initialization error:', error);
            this.canvas.setConnectionStatus('disconnected');
            this.addChatMessage('error', `Connection error: ${error.message}. Make sure the backend is running on localhost:8080`);
        }

        // Bind event handlers
        this.bindEvents();

        console.log('[App] Initialization complete');
    }

    /**
     * Restore canvas state from backend
     */
    async restoreCanvasState() {
        try {
            const state = await this.api.getCanvasState(this.session.id);
            if (state && state.elements && state.elements.length > 0) {
                console.log('[App] Restoring', state.elements.length, 'elements');
                state.elements.forEach(element => {
                    if (element.html) {
                        this.canvas.insertElement(element.html, {
                            gridRow: element.grid_position?.grid_row || '4/18',
                            gridColumn: element.grid_position?.grid_column || '2/32'
                        });
                    }
                });
            }
        } catch (error) {
            console.log('[App] No existing canvas state');
        }
    }

    /**
     * Bind all event handlers
     */
    bindEvents() {
        // Mode switching
        this.bindModeSwitch();

        // Chat mode events
        this.bindChatEvents();

        // Toolbar mode events
        this.bindToolbarEvents();

        // Canvas control events
        this.bindCanvasControls();
    }

    /**
     * Bind mode tab switching
     */
    bindModeSwitch() {
        const tabs = document.querySelectorAll('#mode-tabs .tab-btn');
        const chatPanel = document.getElementById('chat-mode');
        const toolbarPanel = document.getElementById('toolbar-mode');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const mode = tab.dataset.mode;

                // Update tab active state
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Switch panels
                if (mode === 'chat') {
                    chatPanel.classList.add('active');
                    toolbarPanel.classList.remove('active');
                } else {
                    toolbarPanel.classList.add('active');
                    chatPanel.classList.remove('active');
                }

                this.currentMode = mode;
                console.log('[App] Switched to mode:', mode);
            });
        });
    }

    /**
     * Bind chat mode events
     */
    bindChatEvents() {
        // Send button
        this.chatSendBtn.addEventListener('click', () => this.handleChatSend());

        // Enter key (without shift)
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleChatSend();
            }
        });
    }

    /**
     * Handle sending a chat message
     */
    async handleChatSend() {
        const message = this.chatInput.value.trim();
        if (!message || this.isLoading) return;

        // Clear input
        this.chatInput.value = '';

        // Show user message
        this.addChatMessage('user', message);

        // Show loading
        this.setLoading(true);

        try {
            // Send to backend
            const response = await this.api.sendChatMessage(this.session.id, message);
            console.log('[App] Chat response:', response);

            // Show assistant response
            if (response.response_text) {
                this.addChatMessage('assistant', response.response_text);
            }

            // If element was generated, add to canvas
            if (response.element && response.element.html) {
                const position = response.element.grid_position ? {
                    gridRow: response.element.grid_position.grid_row,
                    gridColumn: response.element.grid_position.grid_column
                } : null;

                // Use appropriate insert method based on component type
                if (response.element.component_type === 'CHART') {
                    this.canvas.insertChart(response.element.html, position);
                } else if (response.element.component_type === 'IMAGE') {
                    this.canvas.insertImage(
                        response.element.html,
                        response.element.grid_position,
                        response.element.element_id
                    );
                } else {
                    this.canvas.insertElement(response.element.html, position);
                }
            }

            // Show suggestions
            if (response.suggestions && response.suggestions.length > 0) {
                this.showSuggestions(response.suggestions);
            }

        } catch (error) {
            console.error('[App] Chat error:', error);
            this.addChatMessage('error', `Error: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * Add a message to the chat display
     */
    addChatMessage(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${role}`;
        msgDiv.textContent = content;

        this.chatMessages.appendChild(msgDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    /**
     * Show suggestion buttons
     */
    showSuggestions(suggestions) {
        this.suggestionsBar.innerHTML = suggestions.map(s =>
            `<button class="suggestion-btn">${s}</button>`
        ).join('');

        this.suggestionsBar.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.chatInput.value = btn.textContent;
                this.chatInput.focus();
            });
        });
    }

    /**
     * Bind toolbar mode events
     */
    bindToolbarEvents() {
        const atomicBtns = document.querySelectorAll('.atomic-btn');

        atomicBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const componentType = btn.dataset.type;
                this.modal.open(componentType, async (config) => {
                    await this.handleToolbarAdd(config);
                });
            });
        });
    }

    /**
     * Handle adding element via toolbar
     */
    async handleToolbarAdd(config) {
        console.log('[App] Toolbar add:', config);

        // Build natural language message from config
        const message = this.modal.buildMessage(config);

        // Show loading
        this.setLoading(true);

        try {
            // Build options - pass configs directly to bypass NLP parsing for position
            const options = {};
            if (config.type === 'IMAGE' && config.imageConfig) {
                options.imageConfig = config.imageConfig;
                console.log('[App] Passing imageConfig directly:', config.imageConfig);
            }
            // Pass position config for TEXT_BOX, METRICS, TABLE
            // Note: atomic-modal sends snake_case 'position_config'
            if (config.position_config && ['TEXT_BOX', 'METRICS', 'TABLE'].includes(config.type)) {
                options.positionConfig = config.position_config;
                options.componentType = config.type;
                console.log('[App] Passing position_config directly:', config.position_config);
                // Also pass component-specific config if available
                if (config.type === 'TEXT_BOX' && config.textboxConfig) {
                    options.textboxConfig = config.textboxConfig;
                }
                if (config.type === 'METRICS' && config.metricsConfig) {
                    options.metricsConfig = config.metricsConfig;
                }
                if (config.type === 'TABLE' && config.tableConfig) {
                    options.tableConfig = config.tableConfig;
                }
            }

            // Send as chat message to leverage existing backend logic
            const response = await this.api.sendChatMessage(this.session.id, message, options);
            console.log('[App] Toolbar response:', response);

            // Add to canvas if element generated
            if (response.element && response.element.html) {
                const position = response.element.grid_position ? {
                    gridRow: response.element.grid_position.grid_row,
                    gridColumn: response.element.grid_position.grid_column
                } : null;

                // Use appropriate insert method based on component type
                if (response.element.component_type === 'CHART') {
                    this.canvas.insertChart(response.element.html, position);
                } else if (response.element.component_type === 'IMAGE') {
                    this.canvas.insertImage(
                        response.element.html,
                        response.element.grid_position,
                        response.element.element_id
                    );
                } else {
                    this.canvas.insertElement(response.element.html, position);
                }

                // Also show success in chat
                this.addChatMessage('user', message);
                this.addChatMessage('assistant', response.response_text || 'Element added!');
            }

        } catch (error) {
            console.error('[App] Toolbar add error:', error);
            this.addChatMessage('error', `Error adding element: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * Bind canvas control buttons
     */
    bindCanvasControls() {
        // Clear canvas
        document.getElementById('clear-canvas').addEventListener('click', async () => {
            if (!confirm('Clear all elements from the canvas?')) return;

            try {
                await this.api.clearCanvas(this.session.id);
                this.canvas.clearElements();
                this.canvas.showPlaceholder();
                this.addChatMessage('assistant', 'Canvas cleared.');
            } catch (error) {
                console.error('[App] Clear error:', error);
            }
        });

        // Toggle grid
        document.getElementById('toggle-grid').addEventListener('click', () => {
            const isVisible = this.canvas.toggleGrid();
            console.log('[App] Grid visible:', isVisible);
        });

        // Hide content slot
        document.getElementById('hide-content-slot').addEventListener('click', () => {
            this.canvas.hideContentSlot();
            this.addChatMessage('assistant', 'Content slot hidden.');
        });

        // Generate AI content
        document.getElementById('generate-all').addEventListener('click', async () => {
            if (this.canvas.getElementCount() === 0) {
                this.addChatMessage('assistant', 'Add some elements first, then generate AI content.');
                return;
            }

            this.setLoading(true);

            try {
                const response = await this.api.sendChatMessage(this.session.id, 'generate');
                console.log('[App] Generate response:', response);

                this.addChatMessage('assistant', response.response_text || 'AI content generated!');

                // If updated elements returned, update them
                if (response.element && response.element.updated_elements) {
                    response.element.updated_elements.forEach(el => {
                        this.canvas.updateElementContent(el.element_id, el.html);
                    });
                }

            } catch (error) {
                console.error('[App] Generate error:', error);
                this.addChatMessage('error', `Error generating content: ${error.message}`);
            } finally {
                this.setLoading(false);
            }
        });
    }

    /**
     * Set loading state
     */
    setLoading(isLoading) {
        this.isLoading = isLoading;

        if (isLoading) {
            this.loadingOverlay.classList.remove('hidden');
            this.chatSendBtn.disabled = true;
        } else {
            this.loadingOverlay.classList.add('hidden');
            this.chatSendBtn.disabled = false;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TextLabsApp();
    window.app.init();
});
