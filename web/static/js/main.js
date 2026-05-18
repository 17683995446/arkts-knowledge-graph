/* ==================== 通用工具函数 ==================== */
const API = {
    async get(url) {
        const res = await fetch(url);
        return res.json();
    },
    async post(url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    }
};

function formatNumber(n) {
    if (n === undefined || n === null) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ==================== 仪表盘 ==================== */
const Dashboard = {
    async loadOverview() {
        try {
            const res = await API.get('/api/overview');
            if (!res.success) return;
            const d = res.data;
            document.getElementById('statsGrid').innerHTML = `
                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(79,195,247,0.15);color:#4fc3f7"><i class="fas fa-file-code"></i></div>
                    <div class="stat-value">${formatNumber(d.file_count)}</div>
                    <div class="stat-label">源代码文件</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(129,199,132,0.15);color:#81c784"><i class="fas fa-cubes"></i></div>
                    <div class="stat-value">${formatNumber(d.class_count)}</div>
                    <div class="stat-label">类/接口/枚举</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(255,183,77,0.15);color:#ffb74d"><i class="fas fa-code"></i></div>
                    <div class="stat-value">${formatNumber(d.method_count)}</div>
                    <div class="stat-label">方法/函数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(186,104,200,0.15);color:#ba68c8"><i class="fas fa-project-diagram"></i></div>
                    <div class="stat-value">${formatNumber(d.call_count)}</div>
                    <div class="stat-label">调用关系</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(229,115,115,0.15);color:#e57373"><i class="fas fa-at"></i></div>
                    <div class="stat-value">${formatNumber(d.decorator_count)}</div>
                    <div class="stat-label">装饰器</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(79,195,247,0.15);color:#4fc3f7"><i class="fas fa-database"></i></div>
                    <div class="stat-value">${d.database_size_mb || 0}<small>MB</small></div>
                    <div class="stat-label">数据库大小</div>
                </div>
            `;
        } catch (e) { console.error('加载总览失败:', e); }
    },

    async loadRecentClasses() {
        try {
            const res = await API.get('/api/classes?limit=10');
            if (!res.success || !res.data.length) {
                document.getElementById('recentClasses').innerHTML = '<div class="empty-state">暂无类数据</div>';
                return;
            }
            document.getElementById('recentClasses').innerHTML = res.data.map(c => `
                <div class="list-item" onclick="window.location.href='/classes?id=${c.id}'">
                    <span class="item-icon"><i class="fas fa-cube"></i></span>
                    <span class="item-name">${escapeHtml(c.name)}</span>
                    <span class="item-path">${escapeHtml(c.file_path)}</span>
                </div>
            `).join('');
        } catch (e) { console.error('加载类列表失败:', e); }
    },

    async loadEntryComponents() {
        try {
            const res = await API.get('/api/entry-components');
            if (!res.success || !res.data.length) {
                document.getElementById('entryComponents').innerHTML = '<div class="empty-state">暂无入口组件</div>';
                return;
            }
            document.getElementById('entryComponents').innerHTML = res.data.map(c => `
                <div class="list-item" onclick="window.location.href='/classes?id=${c.id}'">
                    <span class="item-icon"><i class="fas fa-door-open"></i></span>
                    <span class="item-name">${escapeHtml(c.name)}</span>
                    <span class="item-path">${escapeHtml(c.file_path)}</span>
                </div>
            `).join('');
        } catch (e) { console.error('加载入口组件失败:', e); }
    },

    async loadDatabaseStats() {
        try {
            const res = await API.get('/api/database/stats');
            if (!res.success) return;
            const d = res.data;
            const entries = Object.entries(d).filter(([k]) => k !== 'database_size_mb');
            document.getElementById('dbStats').innerHTML = `
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px">
                    ${entries.map(([k, v]) => `
                        <div style="background:#0a0e27;border-radius:8px;padding:10px;text-align:center">
                            <div style="color:#4fc3f7;font-size:18px;font-weight:700">${formatNumber(v)}</div>
                            <div style="color:#666;font-size:11px;margin-top:2px">${escapeHtml(k)}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (e) { console.error('加载数据库统计失败:', e); }
    }
};
