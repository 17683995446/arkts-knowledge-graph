/* ==================== 统计分析页面 ==================== */
const StatsPage = {
    async init() {
        await this.loadStats();
    },

    async loadStats() {
        try {
            const [overviewRes, dbRes] = await Promise.all([
                API.get('/api/overview'),
                API.get('/api/database/stats'),
            ]);

            if (overviewRes.success) this.renderSummary(overviewRes.data);
            if (dbRes.success) this.renderDbTables(dbRes.data);

            this.loadFileDistribution();
            this.loadClassMethodDistribution();
        } catch (e) { console.error(e); }
    },

    renderSummary(d) {
        document.getElementById('summaryCards').innerHTML = `
            <div class="stat-card">
                <h4>源代码文件</h4>
                <div class="value">${formatNumber(d.file_count)}</div>
                <div class="sub">已扫描</div>
            </div>
            <div class="stat-card">
                <h4>类/接口/枚举</h4>
                <div class="value">${formatNumber(d.class_count)}</div>
                <div class="sub">类型定义</div>
            </div>
            <div class="stat-card">
                <h4>方法/函数</h4>
                <div class="value">${formatNumber(d.method_count)}</div>
                <div class="sub">可调用单元</div>
            </div>
            <div class="stat-card">
                <h4>调用关系</h4>
                <div class="value">${formatNumber(d.call_count)}</div>
                <div class="sub">依赖边</div>
            </div>
        `;
    },

    renderDbTables(d) {
        const entries = Object.entries(d).filter(([k]) => k !== 'database_size_mb');
        const colors = ['blue', 'green', 'orange', 'purple', 'red'];
        document.getElementById('dbTableList').innerHTML = entries.map(([k, v], i) => `
            <div class="db-table-item">
                <div class="table-name">${escapeHtml(k)}</div>
                <div class="table-count">${formatNumber(v)}</div>
                <div class="table-label">条记录</div>
            </div>
        `).join('');
    },

    async loadFileDistribution() {
        try {
            const res = await API.get('/api/files?limit=500');
            if (!res.success) return;
            const files = res.data.sort((a, b) => (b.line_count || 0) - (a.line_count || 0)).slice(0, 10);
            const maxLines = files[0]?.line_count || 1;
            const colors = ['blue', 'green', 'orange', 'purple', 'red'];

            document.getElementById('fileSizeChart').innerHTML = files.map((f, i) => `
                <div class="bar-row">
                    <div class="bar-label" title="${escapeHtml(f.path)}">${escapeHtml(f.path.split('/').pop())}</div>
                    <div class="bar-track">
                        <div class="bar-fill ${colors[i % colors.length]}" style="width:${(f.line_count / maxLines * 100)}%">
                            ${f.line_count} 行
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (e) { console.error(e); }
    },

    async loadClassMethodDistribution() {
        try {
            const res = await API.get('/api/classes?limit=500');
            if (!res.success) return;

            // 统计每个类的方法数
            const classMethods = {};
            for (const cls of res.data) {
                try {
                    const detail = await API.get(`/api/classes/${cls.id}`);
                    if (detail.success) {
                        classMethods[cls.name] = {
                            methods: detail.data.methods?.length || 0,
                            props: detail.data.properties?.length || 0,
                            id: cls.id,
                        };
                    }
                } catch (e) { /* skip */ }

                // 限制请求数量
                if (Object.keys(classMethods).length >= 10) break;
            }

            const sorted = Object.entries(classMethods)
                .sort((a, b) => b[1].methods - a[1].methods)
                .slice(0, 10);
            const maxMethods = sorted[0]?.[1].methods || 1;
            const colors = ['blue', 'green', 'orange', 'purple', 'red'];

            document.getElementById('classMethodChart').innerHTML = sorted.map(([name, info], i) => `
                <div class="bar-row">
                    <div class="bar-label">
                        <a href="/classes?id=${info.id}" style="color:#4fc3f7;text-decoration:none">${escapeHtml(name)}</a>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill ${colors[i % colors.length]}" style="width:${(info.methods / maxMethods * 100)}%">
                            ${info.methods} 方法 / ${info.props} 属性
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (e) { console.error(e); }
    }
};
