/* ==================== 类浏览器页面 ==================== */
const ClassesPage = {
    selectedClassId: null,
    searchTimeout: null,

    init() {
        const params = new URLSearchParams(window.location.search);
        const search = params.get('search');
        const id = params.get('id');

        if (search) {
            document.getElementById('classSearch').value = search;
            this.searchClasses(search);
        } else if (id) {
            this.loadClassDetail(parseInt(id));
            this.loadAllClasses();
        } else {
            this.loadAllClasses();
        }

        document.getElementById('classSearch').addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchClasses(e.target.value.trim());
            }, 300);
        });
    },

    async loadAllClasses() {
        try {
            const res = await API.get('/api/classes?limit=500');
            if (!res.success) return;
            this.renderClassList(res.data);
        } catch (e) { console.error(e); }
    },

    async searchClasses(keyword) {
        try {
            const url = keyword ? `/api/classes?search=${encodeURIComponent(keyword)}&limit=100` : '/api/classes?limit=500';
            const res = await API.get(url);
            if (!res.success) return;
            this.renderClassList(res.data);
        } catch (e) { console.error(e); }
    },

    renderClassList(classes) {
        const container = document.getElementById('classList');
        if (!classes.length) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-search"></i>未找到匹配的类</div>';
            return;
        }
        container.innerHTML = classes.map(c => {
            const flags = this.parseClassFlags(c.flags || 0);
            const badges = [];
            if (flags.interface) badges.push('<span class="badge">接口</span>');
            if (flags.abstract) badges.push('<span class="badge">抽象</span>');
            if (flags.enum) badges.push('<span class="badge">枚举</span>');
            if (flags.entry) badges.push('<span class="badge" style="background:#1b5e20;color:#a5d6a7">Entry</span>');
            return `
                <div class="class-item ${c.id === this.selectedClassId ? 'active' : ''}"
                     onclick="ClassesPage.loadClassDetail(${c.id})" data-id="${c.id}">
                    <span class="icon"><i class="fas fa-${flags.interface ? 'shapes' : flags.enum ? 'list' : 'cube'}"></i></span>
                    <span class="name">${escapeHtml(c.name)}</span>
                    ${badges.join('')}
                </div>
            `;
        }).join('');
    },

    parseClassFlags(flags) {
        return {
            interface: !!(flags & 1),
            abstract: !!(flags & 2),
            enum: !!(flags & 4),
            struct: !!(flags & 8),
            generic: !!(flags & 16),
            exported: !!(flags & 32),
            entry: !!(flags & 64),
        };
    },

    parseMethodFlags(flags) {
        const result = {};
        if (flags & 1) result.static = true;
        if (flags & 2) result.async = true;
        if (flags & 4) result.private = true;
        if (flags & 8) result.protected = true;
        if (flags & 16) result.override = true;
        if (flags & 32) result.getter = true;
        if (flags & 64) result.setter = true;
        if (flags & 128) result.constructor = true;
        if (flags & 256) result.lifecycle = true;
        return result;
    },

    async loadClassDetail(classId) {
        this.selectedClassId = classId;

        // 高亮列表项
        document.querySelectorAll('.class-item').forEach(el => {
            el.classList.toggle('active', parseInt(el.dataset.id) === classId);
        });

        const detailDiv = document.getElementById('classDetail');
        detailDiv.innerHTML = '<div class="loading-spinner"></div>';

        try {
            const res = await API.get(`/api/classes/${classId}`);
            if (!res.success) {
                detailDiv.innerHTML = '<div class="empty-state">加载失败</div>';
                return;
            }

            const d = res.data;
            const cls = d.class;
            const flags = this.parseClassFlags(cls.flags || 0);

            let html = `
                <div class="class-detail-header">
                    <h2>${escapeHtml(cls.name)}</h2>
                    <div class="meta">
                        <span>${escapeHtml(cls.file_path)}</span>
                        <span> | 行 ${cls.start_line}-${cls.end_line}</span>
                        ${flags.interface ? ' | 接口' : ''}
                        ${flags.abstract ? ' | 抽象' : ''}
                        ${flags.enum ? ' | 枚举' : ''}
                        ${flags.exported ? ' | 导出' : ''}
                    </div>
                </div>
            `;

            // 继承关系
            if (d.parents.length || d.children.length) {
                html += `<div class="detail-section"><h4><i class="fas fa-sitemap"></i> 继承关系</h4>`;
                if (d.parents.length) {
                    html += `<div style="margin-bottom:8px;font-size:12px;color:#888">父类:</div>`;
                    html += `<div class="inheritance-chain">`;
                    d.parents.forEach(p => {
                        html += `<span class="chain-item" onclick="ClassesPage.loadClassDetail(${p.id})">${escapeHtml(p.name)}</span>`;
                    });
                    html += `</div>`;
                }
                if (d.children.length) {
                    html += `<div style="margin-bottom:8px;font-size:12px;color:#888">子类:</div>`;
                    html += `<div class="inheritance-chain">`;
                    d.children.forEach(c => {
                        html += `<span class="chain-item" onclick="ClassesPage.loadClassDetail(${c.id})">${escapeHtml(c.name)}</span>`;
                    });
                    html += `</div>`;
                }
                html += `</div>`;
            }

            // 装饰器
            if (d.decorators.length) {
                html += `<div class="detail-section"><h4><i class="fas fa-at"></i> 装饰器</h4>`;
                d.decorators.forEach(dec => {
                    html += `<div class="member-item"><span class="member-icon" style="color:#ba68c8">@</span><span class="member-name">${escapeHtml(dec.name)}</span></div>`;
                });
                html += `</div>`;
            }

            // 方法
            if (d.methods.length) {
                html += `<div class="detail-section"><h4><i class="fas fa-code"></i> 方法 (${d.methods.length})</h4>`;
                d.methods.forEach(m => {
                    const mf = this.parseMethodFlags(m.flags || 0);
                    const flagHtml = [];
                    if (mf.static) flagHtml.push('<span class="flag-tag flag-static">static</span>');
                    if (mf.private) flagHtml.push('<span class="flag-tag flag-private">private</span>');
                    if (mf.async) flagHtml.push('<span class="flag-tag flag-async">async</span>');
                    if (mf.override) flagHtml.push('<span class="flag-tag flag-override">override</span>');
                    if (mf.lifecycle) flagHtml.push('<span class="flag-tag" style="background:#0d47a1;color:#90caf9">lifecycle</span>');

                    html += `
                        <div class="member-item">
                            <span class="member-icon" style="color:#81c784"><i class="fas fa-${mf.constructor ? 'hammer' : 'code'}"></i></span>
                            <span class="member-name">${escapeHtml(m.name)}</span>
                            <span class="member-type">${escapeHtml(m.return_type || 'void')}</span>
                            <div class="member-flags">${flagHtml.join('')}</div>
                        </div>
                    `;
                });
                html += `</div>`;
            }

            // 属性
            if (d.properties.length) {
                html += `<div class="detail-section"><h4><i class="fas fa-list"></i> 属性 (${d.properties.length})</h4>`;
                d.properties.forEach(p => {
                    const flagHtml = [];
                    if (p.flags & 1) flagHtml.push('<span class="flag-tag flag-static">static</span>');
                    if (p.flags & 2) flagHtml.push('<span class="flag-tag flag-private">private</span>');
                    if (p.flags & 8) flagHtml.push('<span class="flag-tag" style="background:#1b5e20;color:#a5d6a7">@State</span>');
                    if (p.flags & 16) flagHtml.push('<span class="flag-tag" style="background:#0d47a1;color:#90caf9">@Link</span>');
                    if (p.flags & 32) flagHtml.push('<span class="flag-tag" style="background:#e65100;color:#ffcc80">@Prop</span>');

                    html += `
                        <div class="member-item">
                            <span class="member-icon" style="color:#ffb74d"><i class="fas fa-tag"></i></span>
                            <span class="member-name">${escapeHtml(p.name)}</span>
                            <span class="member-type">${escapeHtml(p.type_annotation || '')}</span>
                            <div class="member-flags">${flagHtml.join('')}</div>
                        </div>
                    `;
                });
                html += `</div>`;
            }

            if (!d.methods.length && !d.properties.length && !d.parents.length && !d.children.length) {
                html += '<div class="empty-state">此类暂无详细信息</div>';
            }

            detailDiv.innerHTML = html;

        } catch (e) {
            detailDiv.innerHTML = '<div class="empty-state">加载失败</div>';
            console.error(e);
        }
    }
};
