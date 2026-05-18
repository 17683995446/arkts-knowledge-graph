/* ==================== 知识图谱可视化引擎 ==================== */
const GraphVisualization = {
    canvas: null,
    ctx: null,
    infoEl: null,
    nodes: [],
    edges: [],
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    dragging: false,
    dragNode: null,
    lastMouse: { x: 0, y: 0 },
    hoveredNode: null,
    animationId: null,

    // 颜色配置
    colors: {
        class: '#4fc3f7',
        method: '#81c784',
        calls: 'rgba(255, 183, 77, 0.4)',
        extends: 'rgba(229, 115, 115, 0.4)',
        component: 'rgba(186, 104, 200, 0.4)',
        imports: 'rgba(150, 150, 150, 0.2)',
    },

    init(canvasId, infoId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.infoEl = document.getElementById(infoId);
        this.resize();
        window.addEventListener('resize', () => this.resize());

        // 鼠标事件
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', () => this.onMouseUp());
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        this.canvas.addEventListener('dblclick', (e) => this.onDblClick(e));

        // 触摸事件
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', () => this.onMouseUp());
    },

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
        this.draw();
    },

    async load() {
        try {
            const type = document.getElementById('graphType').value;
            const res = await API.get(`/api/graph/data?limit=2000`);
            if (!res.success) return;

            let { nodes, edges } = res.data;

            // 按类型过滤
            if (type === 'classes') {
                edges = edges.filter(e => e.type === 'extends');
                nodes = nodes.filter(n => n.type === 'class');
            } else if (type === 'calls') {
                edges = edges.filter(e => e.type === 'calls');
            } else if (type === 'inherit') {
                edges = edges.filter(e => e.type === 'extends');
            }

            // 初始化节点位置
            const w = this.canvas.width / window.devicePixelRatio;
            const h = this.canvas.height / window.devicePixelRatio;
            nodes.forEach((n, i) => {
                n.x = w / 2 + (Math.random() - 0.5) * w * 0.6;
                n.y = h / 2 + (Math.random() - 0.5) * h * 0.6;
                n.vx = 0;
                n.vy = 0;
                n.radius = n.type === 'class' ? 8 : 5;
            });

            this.nodes = nodes;
            this.edges = edges;
            this.simulate();
        } catch (e) {
            console.error('加载图谱数据失败:', e);
        }
    },

    reload() {
        if (this.animationId) cancelAnimationFrame(this.animationId);
        this.load();
    },

    simulate() {
        // 力导向布局
        const iterations = 200;
        const k = 80; // 理想距离
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;

        for (let iter = 0; iter < iterations; iter++) {
            const alpha = 1 - iter / iterations;

            // 斥力
            for (let i = 0; i < this.nodes.length; i++) {
                for (let j = i + 1; j < this.nodes.length; j++) {
                    const dx = this.nodes[j].x - this.nodes[i].x;
                    const dy = this.nodes[j].y - this.nodes[i].y;
                    const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
                    const force = (k * k) / dist * alpha;
                    const fx = (dx / dist) * force;
                    const fy = (dy / dist) * force;
                    this.nodes[i].vx -= fx;
                    this.nodes[i].vy -= fy;
                    this.nodes[j].vx += fx;
                    this.nodes[j].vy += fy;
                }
            }

            // 引力（边）
            for (const edge of this.edges) {
                const source = this.nodes.find(n => n.id === edge.source);
                const target = this.nodes.find(n => n.id === edge.target);
                if (!source || !target) continue;
                const dx = target.x - source.x;
                const dy = target.y - source.y;
                const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
                const force = (dist - k) * 0.05 * alpha;
                const fx = (dx / dist) * force;
                const fy = (dy / dist) * force;
                source.vx += fx;
                source.vy += fy;
                target.vx -= fx;
                target.vy -= fy;
            }

            // 中心引力
            for (const node of this.nodes) {
                node.vx += (w / 2 - node.x) * 0.001;
                node.vy += (h / 2 - node.y) * 0.001;
            }

            // 更新位置
            for (const node of this.nodes) {
                node.vx *= 0.9;
                node.vy *= 0.9;
                node.x += node.vx;
                node.y += node.vy;
                node.x = Math.max(20, Math.min(w - 20, node.x));
                node.y = Math.max(20, Math.min(h - 20, node.y));
            }
        }

        this.draw();
    },

    draw() {
        const ctx = this.ctx;
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;

        ctx.clearRect(0, 0, w, h);

        ctx.save();
        ctx.translate(this.offsetX, this.offsetY);
        ctx.scale(this.scale, this.scale);

        // 绘制边
        for (const edge of this.edges) {
            const source = this.nodes.find(n => n.id === edge.source);
            const target = this.nodes.find(n => n.id === edge.target);
            if (!source || !target) continue;

            ctx.beginPath();
            ctx.moveTo(source.x, source.y);
            ctx.lineTo(target.x, target.y);
            ctx.strokeStyle = this.colors[edge.type] || this.colors.calls;
            ctx.lineWidth = edge.type === 'calls' ? 0.5 : 1;
            ctx.stroke();
        }

        // 绘制节点
        for (const node of this.nodes) {
            const isHovered = this.hoveredNode === node;
            const r = isHovered ? node.radius * 1.5 : node.radius;

            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
            ctx.fillStyle = this.colors[node.type] || '#888';
            ctx.fill();

            if (isHovered) {
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // 标签
            if (this.scale > 0.5 || isHovered) {
                ctx.fillStyle = '#e0e0e0';
                ctx.font = `${isHovered ? 12 : 10}px sans-serif`;
                ctx.textAlign = 'center';
                ctx.fillText(node.name || '', node.x, node.y - r - 4);
            }
        }

        ctx.restore();
    },

    screenToWorld(x, y) {
        return {
            x: (x - this.offsetX) / this.scale,
            y: (y - this.offsetY) / this.scale,
        };
    },

    findNodeAt(x, y) {
        const { x: wx, y: wy } = this.screenToWorld(x, y);
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const n = this.nodes[i];
            const dx = n.x - wx;
            const dy = n.y - wy;
            if (dx * dx + dy * dy < (n.radius + 4) * (n.radius + 4)) return n;
        }
        return null;
    },

    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        this.lastMouse = { x, y };
        this.dragNode = this.findNodeAt(x, y);
        this.dragging = true;
    },

    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (this.dragging && this.dragNode) {
            const { x: wx, y: wy } = this.screenToWorld(x, y);
            this.dragNode.x = wx;
            this.dragNode.y = wy;
            this.draw();
        } else if (this.dragging) {
            this.offsetX += x - this.lastMouse.x;
            this.offsetY += y - this.lastMouse.y;
            this.draw();
        } else {
            const node = this.findNodeAt(x, y);
            if (node !== this.hoveredNode) {
                this.hoveredNode = node;
                this.canvas.style.cursor = node ? 'pointer' : 'grab';
                this.draw();
                if (node) {
                    this.infoEl.style.display = 'block';
                    this.infoEl.style.left = (e.clientX + 12) + 'px';
                    this.infoEl.style.top = (e.clientY + 12) + 'px';
                    this.infoEl.innerHTML = `<strong>${escapeHtml(node.name)}</strong><br><small style="color:#888">类型: ${node.type} | ID: ${node.id}</small>`;
                } else {
                    this.infoEl.style.display = 'none';
                }
            }
        }
        this.lastMouse = { x, y };
    },

    onMouseUp() {
        this.dragging = false;
        this.dragNode = null;
    },

    onWheel(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        this.offsetX = x - (x - this.offsetX) * delta;
        this.offsetY = y - (y - this.offsetY) * delta;
        this.scale *= delta;
        this.scale = Math.max(0.1, Math.min(5, this.scale));
        this.draw();
    },

    onDblClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const node = this.findNodeAt(x, y);
        if (node && node.type === 'class') {
            window.open(`/classes?id=${node.id}`, '_blank');
        }
    },

    onTouchStart(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const rect = this.canvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        this.lastMouse = { x, y };
        this.dragNode = this.findNodeAt(x, y);
        this.dragging = true;
    },

    onTouchMove(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const rect = this.canvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        if (this.dragging && this.dragNode) {
            const { x: wx, y: wy } = this.screenToWorld(x, y);
            this.dragNode.x = wx;
            this.dragNode.y = wy;
            this.draw();
        } else if (this.dragging) {
            this.offsetX += x - this.lastMouse.x;
            this.offsetY += y - this.lastMouse.y;
            this.draw();
        }
        this.lastMouse = { x, y };
    },

    zoomIn() {
        this.scale *= 1.2;
        this.scale = Math.min(5, this.scale);
        this.draw();
    },

    zoomOut() {
        this.scale *= 0.8;
        this.scale = Math.max(0.1, this.scale);
        this.draw();
    },

    resetView() {
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.draw();
    }
};
