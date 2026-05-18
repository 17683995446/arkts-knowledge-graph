/* ==================== AI 智能查询页面 ==================== */
const QueryPage = {
    init() {
        // 从URL参数加载搜索
        const params = new URLSearchParams(window.location.search);
        const q = params.get('q');
        if (q) {
            document.getElementById('queryInput').value = q;
            this.submit();
        }
    },

    ask(question) {
        document.getElementById('queryInput').value = question;
        this.submit();
    },

    clearInput() {
        document.getElementById('queryInput').value = '';
    },

    async submit() {
        const input = document.getElementById('queryInput');
        const question = input.value.trim();
        if (!question) return;

        const resultsDiv = document.getElementById('queryResults');
        const btn = document.getElementById('submitBtn');

        // 添加加载状态
        const loadingHtml = `
            <div class="query-result" id="loading-${Date.now()}">
                <div class="question"><i class="fas fa-user" style="color:#4fc3f7;margin-right:6px"></i>${escapeHtml(question)}</div>
                <div class="loading-indicator">
                    <div class="loading-dots"><span></span><span></span><span></span></div>
                    <span>AI 正在思考...</span>
                </div>
            </div>
        `;
        resultsDiv.insertAdjacentHTML('afterbegin', loadingHtml);

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询中...';

        try {
            const res = await API.post('/api/query', { question });

            // 移除加载状态
            const loadingEl = resultsDiv.querySelector('.loading-indicator');
            if (loadingEl) loadingEl.closest('.query-result').remove();

            if (res.success) {
                const data = res.data;
                let resultsHtml = '';

                if (data.results && data.results.length > 0) {
                    const cols = Object.keys(data.results[0]);
                    resultsHtml = `
                        <div class="result-table-wrapper">
                            <table class="result-table">
                                <thead><tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr></thead>
                                <tbody>${data.results.map(row =>
                                    `<tr>${cols.map(c => `<td>${escapeHtml(String(row[c] ?? ''))}</td>`).join('')}</tr>`
                                ).join('')}</tbody>
                            </table>
                        </div>
                    `;
                }

                const resultHtml = `
                    <div class="query-result">
                        <div class="question"><i class="fas fa-user" style="color:#4fc3f7;margin-right:6px"></i>${escapeHtml(question)}</div>
                        <div class="answer"><i class="fas fa-robot" style="color:#81c784;margin-right:6px"></i>${escapeHtml(data.answer)}</div>
                        ${data.sql ? `<div class="sql-block"><i class="fas fa-database" style="margin-right:6px"></i>${escapeHtml(data.sql)}</div>` : ''}
                        ${resultsHtml}
                    </div>
                `;
                resultsDiv.insertAdjacentHTML('afterbegin', resultHtml);
            } else {
                const errorHtml = `
                    <div class="query-result">
                        <div class="question"><i class="fas fa-user" style="color:#4fc3f7;margin-right:6px"></i>${escapeHtml(question)}</div>
                        <div class="answer" style="color:#e57373"><i class="fas fa-exclamation-triangle" style="margin-right:6px"></i>${escapeHtml(res.error)}</div>
                    </div>
                `;
                resultsDiv.insertAdjacentHTML('afterbegin', errorHtml);
            }
        } catch (e) {
            const loadingEl = resultsDiv.querySelector('.loading-indicator');
            if (loadingEl) loadingEl.closest('.query-result').remove();
            resultsDiv.insertAdjacentHTML('afterbegin', `
                <div class="query-result">
                    <div class="answer" style="color:#e57373">网络请求失败: ${escapeHtml(e.message)}</div>
                </div>
            `);
        }

        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> 发送查询';
    },

    async clearHistory() {
        try {
            await API.post('/api/query/clear', {});
            document.getElementById('queryResults').innerHTML = '';
        } catch (e) { console.error(e); }
    }
};
