/**
 * API Communication Layer
 */

const API_BASE_URL = window.location.origin; // Assume frontend is served via FastAPI static

export class ApiService {
    /**
     * Get configured provider options from LocalStorage
     */
    static getProviderOpts() {
        const stored = localStorage.getItem('proposeai_settings');
        if (stored) return JSON.parse(stored);
        
        // Default to Ollama
        return {
            provider: 'ollama',
            api_url: 'http://localhost:11434',
            model: '',
            api_key: ''
        };
    }

    /**
     * Check backend health
     */
    static async checkHealth() {
        try {
            const res = await fetch(`${API_BASE_URL}/health`);
            if (!res.ok) throw new Error('API down');
            return await res.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    /**
     * Get history of proposals
     */
    static async getHistory() {
        try {
            const res = await fetch(`${API_BASE_URL}/proposals`);
            if (!res.ok) throw new Error('Failed to fetch history');
            return await res.json();
        } catch (error) {
            console.error(error);
            return { proposals: [], cost_reports: [] };
        }
    }

    /**
     * Generate raw draft JSON
     */
    static async draftProposal(payload) {
        const opts = this.getProviderOpts();
        const requestData = {
            ...payload,
            provider: opts.provider,
            model: opts.model || null,
            api_key: opts.api_key || null,
            api_url: opts.api_url || null
        };
        
        const res = await fetch(`${API_BASE_URL}/generate-proposal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        if (!res.ok) {
            const errInfo = await res.text();
            throw new Error(`API Error: ${res.status} - ${errInfo}`);
        }
        return await res.json();
    }

    /**
     * Generate PDF and trigger download
     */
    static async generatePDF(payload) {
        const opts = this.getProviderOpts();
        const requestData = {
            ...payload,
            provider: opts.provider,
            model: opts.model || null,
            api_key: opts.api_key || null,
            api_url: opts.api_url || null
        };

        const res = await fetch(`${API_BASE_URL}/download-proposal-pdf`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        if (!res.ok) {
            const errInfo = await res.text();
            throw new Error(`API Error: ${res.status} - ${errInfo}`);
        }
        
        return await res.blob();
    }
}

window.ApiService = ApiService;
