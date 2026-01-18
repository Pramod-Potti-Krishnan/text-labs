/**
 * Session Manager for Text Labs
 * Handles session ID generation and persistence
 */

class SessionManager {
    constructor(storageKey = 'textlabs_session_id') {
        this.storageKey = storageKey;
        this.id = this.loadOrCreate();
    }

    /**
     * Load existing session ID or create a new one
     */
    loadOrCreate() {
        let sessionId = localStorage.getItem(this.storageKey);

        if (!sessionId) {
            sessionId = this.generateId();
            localStorage.setItem(this.storageKey, sessionId);
            console.log('[Session] Created new session:', sessionId);
        } else {
            console.log('[Session] Restored session:', sessionId);
        }

        return sessionId;
    }

    /**
     * Generate a new unique session ID
     */
    generateId() {
        // Generate a UUID v4-like ID
        return 'tl_' + 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Reset session (create new ID)
     */
    reset() {
        const newId = this.generateId();
        localStorage.setItem(this.storageKey, newId);
        this.id = newId;
        console.log('[Session] Reset to new session:', newId);
        return newId;
    }

    /**
     * Get short display version of session ID
     */
    getDisplayId() {
        return this.id.substring(0, 12) + '...';
    }
}

// Export as global
window.SessionManager = SessionManager;
