/**
 * Main Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation ---
    const navLinks = document.querySelectorAll('.nav-links li[data-target]');
    const views = document.querySelectorAll('.view');

    function switchView(targetId) {
        views.forEach(v => v.classList.add('hidden'));
        document.getElementById(`view-${targetId}`).classList.remove('hidden');
        
        navLinks.forEach(link => link.classList.remove('active'));
        const activeLink = document.querySelector(`.nav-links li[data-target="${targetId}"]`);
        if (activeLink) activeLink.classList.add('active');

        if (targetId === 'dashboard' || targetId === 'history') {
            loadHistory();
        }
        if (targetId === 'settings') {
            loadSettingsForm();
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', () => switchView(link.dataset.target));
    });

    // --- Toast Notifications ---
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info');
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- Loader ---
    const loader = document.getElementById('loader');
    const toggleLoader = (show, text = 'Generating...') => {
        document.getElementById('loader-text').innerText = text;
        if (show) loader.classList.remove('hidden');
        else loader.classList.add('hidden');
    }

    // --- Health Check ---
    async function initHealth() {
        const ind = document.querySelector('.status-indicator');
        const txt = document.getElementById('api-status');
        const health = await ApiService.checkHealth();
        if (health) {
            ind.classList.add('online');
            txt.innerText = 'Connected';
        } else {
            ind.style.background = 'var(--status-red)';
            txt.innerText = 'Offline';
            txt.style.color = 'var(--status-red)';
            showToast('Cannot connect to backend server', 'error');
        }
    }
    initHealth();

    // --- Dashboard & History Data ---
    async function loadHistory() {
        const data = await ApiService.getHistory();
        const statTotal = document.getElementById('stat-total');
        if (statTotal) statTotal.innerText = data.proposals.length;

        const renderGrid = (containerId) => {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            if (data.proposals.length === 0) {
                container.innerHTML = `<div style="text-align:center; padding: 40px; color: var(--text-muted);">No proposals generated yet.</div>`;
                return;
            }

            container.innerHTML = data.proposals.map(p => `
                <div class="proposal-card">
                    <div class="card-left">
                        <div class="card-icon pdf"><i class="fa-solid fa-file-pdf"></i></div>
                        <div class="card-info">
                            <h4>${p.filename.split('_Proposal')[0].replace(/_/g, ' ')}</h4>
                            <p class="card-meta">
                                <span><i class="fa-regular fa-clock"></i> ${new Date(p.created_at).toLocaleDateString()}</span>
                                <span><i class="fa-solid fa-weight-hanging"></i> ${p.size_kb} KB</span>
                            </p>
                        </div>
                    </div>
                    <div class="card-right">
                        <span class="tag ${Date.now() - new Date(p.created_at).getTime() < 86400000 ? 'new' : ''}">${Date.now() - new Date(p.created_at).getTime() < 86400000 ? 'New' : 'Old'}</span>
                        <a href="${p.download_url}" target="_blank" class="btn btn-outline" download="${p.filename}"><i class="fa-solid fa-download"></i></a>
                    </div>
                </div>
            `).join('');
        };

        renderGrid('recent-grid');
        renderGrid('history-container');
    }
    document.getElementById('btn-refresh-history')?.addEventListener('click', loadHistory);

    // --- Settings / Provider Form ---
    const providerRadios = document.querySelectorAll('input[name="provider"]');
    const settingsOllama = document.getElementById('settings-ollama');
    const settingsExt = document.getElementById('settings-external');

    providerRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'ollama') {
                settingsOllama.classList.remove('hidden');
                settingsExt.classList.add('hidden');
            } else {
                settingsOllama.classList.add('hidden');
                settingsExt.classList.remove('hidden');
            }
        });
    });

    function loadSettingsForm() {
        const opts = ApiService.getProviderOpts();
        document.querySelector(`input[name="provider"][value="${opts.provider}"]`).checked = true;
        
        if (opts.provider === 'ollama') {
            settingsOllama.classList.remove('hidden');
            settingsExt.classList.add('hidden');
            document.getElementById('ollama_url').value = opts.api_url || 'http://localhost:11434';
            document.getElementById('ollama_model').value = opts.model || '';
        } else {
            settingsOllama.classList.add('hidden');
            settingsExt.classList.remove('hidden');
            document.getElementById('ext_model').value = opts.model || '';
            document.getElementById('ext_url').value = opts.api_url || '';
        }
        
        document.getElementById('api_key').value = opts.api_key || '';
        
        const label = document.getElementById('stat-provider');
        if (label) label.innerText = opts.provider === 'ollama' ? 'Ollama (Local)' : opts.provider.toUpperCase();
    }
    loadSettingsForm();

    document.getElementById('btn-save-settings').addEventListener('click', () => {
        const provider = document.querySelector('input[name="provider"]:checked').value;
        let apiUrl = '', model = '';
        const apiKey = document.getElementById('api_key').value;

        if (provider === 'ollama') {
            apiUrl = document.getElementById('ollama_url').value;
            model = document.getElementById('ollama_model').value;
        } else {
            model = document.getElementById('ext_model').value;
            apiUrl = document.getElementById('ext_url').value;
            if (!apiKey && provider !== 'ollama') {
                showToast('API Key is highly recommended for external providers.', 'error');
                // Allow save anyway
            }
        }

        const opts = { provider, api_url: apiUrl, model, api_key: apiKey };
        localStorage.setItem('proposeai_settings', JSON.stringify(opts));
        
        showToast('Settings saved successfully', 'success');
        loadSettingsForm();
    });

    // --- Form Helper ---
    function getFormData() {
        return {
            project_title: document.getElementById('project_title').value,
            client_name: document.getElementById('client_name').value || '',
            industry: document.getElementById('industry').value,
            duration_months: parseInt(document.getElementById('duration_months').value, 10),
            expected_users: parseInt(document.getElementById('expected_users').value, 10),
            tech_stack: document.getElementById('tech_stack').value.split(',').map(s=>s.trim()).filter(x=>x)
        };
    }

    // --- Generate Draft (JSON) ---
    document.getElementById('btn-draft').addEventListener('click', async () => {
        const form = document.getElementById('proposal-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        toggleLoader(true, 'Drafting structural layout using AI...');
        try {
            const data = getFormData();
            const result = await ApiService.draftProposal(data);
            
            document.querySelector('.preview-empty').classList.add('hidden');
            const pContent = document.getElementById('preview-content');
            pContent.classList.remove('hidden');
            pContent.innerText = JSON.stringify(result, null, 2);
            
            showToast('Draft generated successfully', 'success');
        } catch (e) {
            showToast(e.message, 'error');
        } finally {
            toggleLoader(false);
        }
    });

    // --- Generate PDF ---
    document.getElementById('proposal-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        toggleLoader(true, 'Synthesizing PDF and calculating cost logic...');
        try {
            const data = getFormData();
            const blob = await ApiService.generatePDF(data);
            
            // Create object URL and download
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${data.project_title.replace(/[ /]/g, '_')}_Proposal.pdf`;
            document.body.appendChild(a);
            a.click();
            
            window.URL.revokeObjectURL(url);
            showToast('PDF downloaded successfully!', 'success');
            
            // Auto switch to dashboard
            loadHistory();
            switchView('dashboard');
        } catch (e) {
            showToast(e.message, 'error');
        } finally {
            toggleLoader(false);
        }
    });

    // --- Magic Prompt Parser ---
    document.getElementById('magic-btn').addEventListener('click', () => {
        const txt = document.getElementById('magic-prompt').value;
        if (!txt) return;

        // Simple heuristic parser
        let titleMatch = txt.match(/for (.*?) in/i) || txt.match(/for (.*)/i);
        let title = "Magic Project";
        if (titleMatch && titleMatch[1]) title = titleMatch[1].trim();

        let monthsMatch = txt.match(/(\d+)\s*month/i);
        let duration = monthsMatch ? parseInt(monthsMatch[1], 10) : 6;

        let usersMatch = txt.match(/(\d+)\s*user/i) || txt.match(/(\d+k)\s*user/i);
        let users = 5000;
        if (usersMatch && usersMatch[1]) {
            let str = usersMatch[1].toLowerCase().replace('k', '000');
            users = parseInt(str, 10);
        }

        let industryMatch = txt.toLowerCase().match(/(healthcare|finance|ecommerce|retail|education|cloud|saas|manufacturing|logistics)/i);
        let ind = industryMatch ? industryMatch[1] : 'Technology';

        let stackMatch = txt.match(/in (react|aws|python|java|go|node|postgres.*?)/gi);
        let stack = stackMatch ? stackMatch.map(s=>s.replace(/in /i,'').trim()).join(', ') : 'Cloud Native, Fullstack';

        // Navigate to form and fill
        switchView('generate');
        document.getElementById('project_title').value = title;
        document.getElementById('client_name').value = title.includes('Inc') || title.includes('Corp') ? title : '';
        document.getElementById('industry').value = ind;
        document.getElementById('duration_months').value = duration;
        document.getElementById('expected_users').value = users;
        document.getElementById('tech_stack').value = stack;

        showToast('Form pre-filled by Magic Prompt', 'info');
    });

    // Load initial views
    switchView('dashboard');
});
