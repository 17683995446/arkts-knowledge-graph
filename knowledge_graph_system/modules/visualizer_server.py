"""
可视化网站模块 (visualizer_server)

职责：
1. 提供Web界面展示知识图谱
2. 实时推送更新（WebSocket）
3. 展示架构图、流程图、时序图
4. 提供搜索和导航功能

第一性原理：
- 单页应用：减少页面刷新，提升体验
- 实时同步：文件变化立即反映在界面上
- 交互式图谱：支持缩放、拖拽、筛选
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn


class VisualizerServer:
    """
    可视化服务器
    
    提供：
    - 静态Web界面
    - REST API获取数据
    - WebSocket实时推送
    """
    
    def __init__(self, storage, host: str = "0.0.0.0", port: int = 8080):
        self.storage = storage
        self.host = host
        self.port = port
        self.app = FastAPI(title="ArkTS Knowledge Graph Visualizer")
        
        # WebSocket连接管理
        self.active_connections: Set[WebSocket] = set()
        
        # 设置路由
        self._setup_routes()
        
        # 静态文件目录
        self.static_dir = Path(__file__).parent / "static"
        self.static_dir.mkdir(exist_ok=True)
        self._create_static_files()
    
    def _setup_routes(self) -> None:
        """设置路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            return self._get_index_html()
        
        @self.app.get("/api/stats")
        async def get_stats():
            """获取统计信息"""
            return self.storage.get_statistics()
        
        @self.app.get("/api/graph")
        async def get_graph():
            """获取完整依赖图"""
            return self.storage.get_dependency_graph()
        
        @self.app.get("/api/file/{file_path:path}")
        async def get_file_graph(file_path: str):
            """获取单个文件的知识图谱"""
            full_path = f"/{file_path}"
            return self.storage.get_file_graph(full_path)
        
        @self.app.get("/api/entities")
        async def get_entities(
            file_path: Optional[str] = Query(None),
            entity_type: Optional[str] = Query(None)
        ):
            """获取代码实体"""
            return self.storage.get_entities(file_path, entity_type)
        
        @self.app.get("/api/search")
        async def search_entities(q: str, limit: int = 20):
            """搜索实体"""
            return self.storage.search_entities(q, limit)
        
        @self.app.get("/api/events")
        async def get_events(limit: int = 50):
            """获取最近事件"""
            return self.storage.get_recent_events(limit)
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket(websocket)
    
    async def _handle_websocket(self, websocket: WebSocket):
        """处理WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        try:
            # 发送初始数据
            stats = self.storage.get_statistics()
            await websocket.send_json({
                "type": "init",
                "data": stats
            })

            # 保持连接
            while True:
                try:
                    message = await websocket.receive_text()
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        # 忽略畸形JSON，保持连接
                        continue

                    if data.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})

                    elif data.get("action") == "get_graph":
                        graph = self.storage.get_dependency_graph()
                        await websocket.send_json({
                            "type": "graph",
                            "data": graph
                        })
                except WebSocketDisconnect:
                    raise
                except Exception:
                    # 其他错误（包括json.JSONDecodeError），继续接收
                    continue
        
        except WebSocketDisconnect:
            self.active_connections.discard(websocket)
        except Exception as e:
            print(f"[visualizer] WebSocket错误: {e}")
            self.active_connections.discard(websocket)
    
    async def broadcast_update(self, file_path: str) -> None:
        """广播文件更新（并发发送，提升多客户端性能）"""
        if not self.active_connections:
            return

        message = {
            "type": "file_updated",
            "file_path": file_path,
            "timestamp": datetime.now().isoformat()
        }

        # 修复：使用 asyncio.gather 并发发送，而非串行逐个 await
        tasks = []
        disconnected = set()
        for ws in list(self.active_connections):
            tasks.append(self._safe_send(ws, message, disconnected))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # 清理断开的连接
        self.active_connections -= disconnected

    async def _safe_send(self, ws: WebSocket, message: dict, disconnected: set) -> None:
        """安全发送消息，失败时记录断开连接"""
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    
    def _get_index_html(self) -> str:
        """获取主页面HTML"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArkTS Knowledge Graph</title>
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            height: 100vh;
            overflow: hidden;
        }
        
        .container {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            height: 100vh;
        }
        
        /* 左侧导航 */
        .sidebar {
            background: #1e293b;
            border-right: 1px solid #334155;
            display: flex;
            flex-direction: column;
        }
        
        .logo {
            padding: 20px;
            border-bottom: 1px solid #334155;
        }
        
        .logo h1 {
            font-size: 18px;
            color: #38bdf8;
            margin-bottom: 4px;
        }
        
        .logo p {
            font-size: 12px;
            color: #64748b;
        }
        
        .nav {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .nav-item {
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
        }
        
        .nav-item:hover {
            background: #334155;
        }
        
        .nav-item.active {
            background: #0ea5e9;
            color: white;
        }
        
        .nav-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .stats {
            padding: 15px;
            border-top: 1px solid #334155;
            font-size: 12px;
        }
        
        .stat-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .stat-value {
            color: #38bdf8;
            font-weight: 600;
        }
        
        /* 中间主区域 */
        .main {
            display: flex;
            flex-direction: column;
            background: #0f172a;
        }
        
        .toolbar {
            height: 50px;
            background: #1e293b;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            padding: 0 20px;
            gap: 15px;
        }
        
        .search-box {
            flex: 1;
            max-width: 400px;
            position: relative;
        }
        
        .search-box input {
            width: 100%;
            padding: 8px 15px 8px 35px;
            border: 1px solid #334155;
            border-radius: 6px;
            background: #0f172a;
            color: #e2e8f0;
            font-size: 14px;
        }
        
        .search-box::before {
            content: "🔍";
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 12px;
        }
        
        .view-toggle {
            display: flex;
            gap: 5px;
        }
        
        .view-btn {
            padding: 6px 12px;
            border: 1px solid #334155;
            background: #0f172a;
            color: #94a3b8;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }
        
        .view-btn.active {
            background: #0ea5e9;
            color: white;
            border-color: #0ea5e9;
        }
        
        .graph-container {
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        
        #graph {
            width: 100%;
            height: 100%;
        }
        
        /* 右侧面板 */
        .panel {
            background: #1e293b;
            border-left: 1px solid #334155;
            display: flex;
            flex-direction: column;
        }
        
        .panel-header {
            padding: 15px 20px;
            border-bottom: 1px solid #334155;
            font-weight: 600;
        }
        
        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }
        
        .entity-card {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
        }
        
        .entity-type {
            font-size: 11px;
            text-transform: uppercase;
            color: #38bdf8;
            margin-bottom: 5px;
        }
        
        .entity-name {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
            word-break: break-all;
        }
        
        .entity-file {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 10px;
        }
        
        .entity-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        
        .tag {
            padding: 3px 8px;
            background: #334155;
            border-radius: 4px;
            font-size: 11px;
        }
        
        .code-preview {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre;
        }
        
        /* 架构图样式 */
        .architecture-diagram {
            padding: 20px;
        }
        
        .arch-layer {
            margin-bottom: 30px;
        }
        
        .arch-title {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 15px;
            text-transform: uppercase;
        }
        
        .arch-modules {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }
        
        .arch-module {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        
        .arch-module-name {
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .arch-module-desc {
            font-size: 12px;
            color: #64748b;
        }
        
        /* 流程图样式 */
        .flow-container {
            padding: 20px;
        }
        
        .flow-step {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .flow-number {
            width: 30px;
            height: 30px;
            background: #0ea5e9;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            margin-right: 15px;
            flex-shrink: 0;
        }
        
        .flow-content {
            flex: 1;
        }
        
        .flow-title {
            font-weight: 600;
            margin-bottom: 3px;
        }
        
        .flow-desc {
            font-size: 12px;
            color: #64748b;
        }
        
        .flow-arrow {
            width: 30px;
            text-align: center;
            color: #64748b;
        }
        
        /* 时序图样式 */
        .sequence-container {
            padding: 20px;
            font-family: monospace;
            font-size: 13px;
            overflow-x: auto;
        }
        
        .seq-line {
            margin-bottom: 8px;
            white-space: pre;
        }
        
        .seq-actor {
            color: #38bdf8;
        }
        
        .seq-action {
            color: #a78bfa;
        }
        
        /* 状态指示器 */
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: #0f172a;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="container">
        <!-- 左侧导航 -->
        <div class="sidebar">
            <div class="logo">
                <h1>ArkTS Graph</h1>
                <p>Knowledge Graph Visualizer</p>
            </div>
            
            <nav class="nav">
                <div class="nav-item active" data-view="graph">
                    <span class="nav-icon">🕸️</span>
                    <span>知识图谱</span>
                </div>
                <div class="nav-item" data-view="architecture">
                    <span class="nav-icon">🏗️</span>
                    <span>系统架构</span>
                </div>
                <div class="nav-item" data-view="flow">
                    <span class="nav-icon">🔄</span>
                    <span>处理流程</span>
                </div>
                <div class="nav-item" data-view="sequence">
                    <span class="nav-icon">⏱️</span>
                    <span>时序图</span>
                </div>
                <div class="nav-item" data-view="files">
                    <span class="nav-icon">📁</span>
                    <span>文件列表</span>
                </div>
                <div class="nav-item" data-view="events">
                    <span class="nav-icon">📋</span>
                    <span>事件日志</span>
                </div>
            </nav>
            
            <div class="stats">
                <div class="stat-item">
                    <span>文件数</span>
                    <span class="stat-value" id="stat-files">0</span>
                </div>
                <div class="stat-item">
                    <span>实体数</span>
                    <span class="stat-value" id="stat-entities">0</span>
                </div>
                <div class="stat-item">
                    <span>关系数</span>
                    <span class="stat-value" id="stat-relations">0</span>
                </div>
                <div class="stat-item">
                    <span>状态</span>
                    <span class="status-indicator">
                        <span class="status-dot"></span>
                        <span>运行中</span>
                    </span>
                </div>
            </div>
        </div>
        
        <!-- 中间主区域 -->
        <div class="main">
            <div class="toolbar">
                <div class="search-box">
                    <input type="text" id="search-input" placeholder="搜索实体...">
                </div>
                <div class="view-toggle">
                    <button class="view-btn active" data-layout="force">力导向</button>
                    <button class="view-btn" data-layout="circle">环形</button>
                    <button class="view-btn" data-layout="grid">网格</button>
                </div>
            </div>
            
            <div class="graph-container">
                <div id="graph"></div>
            </div>
        </div>
        
        <!-- 右侧面板 -->
        <div class="panel">
            <div class="panel-header" id="panel-title">实体详情</div>
            <div class="panel-content" id="panel-content">
                <p style="color: #64748b; text-align: center; padding: 40px 0;">
                    选择一个实体查看详情
                </p>
            </div>
        </div>
    </div>
    
    <script>
        // 全局状态
        const state = {
            currentView: 'graph',
            currentLayout: 'force',
            selectedNode: null,
            graphData: { nodes: [], edges: [] },
            stats: {},
            ws: null
        };
        
        // 初始化WebSocket（指数退避重连）
        let wsRetryCount = 0;
        const WS_MAX_RETRY = 10;
        const WS_BASE_DELAY = 1000;
        function initWebSocket() {
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            wsRetryCount = 0;

            ws.onopen = () => {
                console.log('WebSocket connected');
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                handleWebSocketMessage(msg);
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected, retrying...');
                wsRetryCount++;
                if (wsRetryCount <= WS_MAX_RETRY) {
                    // 指数退避: 1s, 2s, 4s, 8s... 最大30s
                    const delay = Math.min(WS_BASE_DELAY * Math.pow(2, wsRetryCount - 1), 30000);
                    setTimeout(initWebSocket, delay);
                }
            };

            state.ws = ws;
        }
        
        function handleWebSocketMessage(msg) {
            switch(msg.type) {
                case 'init':
                    updateStats(msg.data);
                    break;
                case 'file_updated':
                    showNotification(`文件已更新: ${msg.file_path}`);
                    refreshGraph();
                    break;
                case 'graph':
                    renderGraph(msg.data);
                    break;
            }
        }
        
        function updateStats(stats) {
            state.stats = stats;
            document.getElementById('stat-files').textContent = stats.total_files || 0;
            document.getElementById('stat-entities').textContent = stats.total_entities || 0;
            document.getElementById('stat-relations').textContent = stats.total_relations || 0;
        }
        
        function showNotification(message) {
            // 简单的通知实现
            console.log('Notification:', message);
        }
        
        // 渲染知识图谱
        let cyInstance = null;
        function renderGraph(data) {
            state.graphData = data;
            const container = document.getElementById('graph');

            if (!data.nodes.length) {
                container.innerHTML = '<p style="text-align: center; padding: 40px; color: #64748b;">暂无数据</p>';
                cyInstance = null;
                return;
            }

            const elements = [
                ...data.nodes.map(n => ({
                    data: {
                        id: n.id,
                        label: n.name,
                        type: n.type,
                        filePath: n.file_path
                    }
                })),
                ...data.edges.map((e, i) => ({
                    data: {
                        id: `e${i}`,
                        source: e.source,
                        target: e.target,
                        type: e.type
                    }
                }))
            ];

            // 修复：复用已有 Cytoscape 实例，避免每次重建导致性能问题和闪烁
            if (cyInstance) {
                cyInstance.json({ elements: elements });
                cyInstance.layout({
                    name: state.currentLayout === 'circle' ? 'circle' :
                          state.currentLayout === 'grid' ? 'grid' : 'cose',
                    padding: 20,
                    nodeRepulsion: 400000,
                    edgeElasticity: 100,
                    gravity: 0.1
                }).run();
            } else {
                container.innerHTML = '';
                cyInstance = cytoscape({
                    container: container,
                    elements: elements,
                    style: [
                        {
                            selector: 'node',
                            style: {
                                'background-color': '#0ea5e9',
                                'label': 'data(label)',
                                'width': 40,
                                'height': 40,
                                'font-size': '12px',
                                'text-valign': 'bottom',
                                'text-halign': 'center',
                                'color': '#e2e8f0',
                                'text-background-color': '#0f172a',
                                'text-background-opacity': 0.8,
                                'text-background-padding': '3px',
                                'text-background-shape': 'roundrectangle'
                            }
                        },
                        {
                            selector: 'node[type="class"]',
                            style: { 'background-color': '#8b5cf6' }
                        },
                        {
                            selector: 'node[type="function"]',
                            style: { 'background-color': '#22c55e' }
                        },
                        {
                            selector: 'node[type="interface"]',
                            style: { 'background-color': '#f59e0b' }
                        },
                        {
                            selector: 'edge',
                            style: {
                                'width': 2,
                                'line-color': '#334155',
                                'target-arrow-color': '#334155',
                                'target-arrow-shape': 'triangle',
                                'curve-style': 'bezier'
                            }
                        }
                    ],
                    layout: {
                        name: state.currentLayout === 'circle' ? 'circle' :
                              state.currentLayout === 'grid' ? 'grid' : 'cose',
                        padding: 20,
                        nodeRepulsion: 400000,
                        edgeElasticity: 100,
                        gravity: 0.1
                    }
                });

                // 节点点击事件
                cyInstance.on('tap', 'node', (evt) => {
                    const node = evt.target;
                    showNodeDetails(node.data());
                });
            }
        }
        
        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function showNodeDetails(data) {
            state.selectedNode = data;
            document.getElementById('panel-title').textContent = data.label || '';
            
            const content = document.getElementById('panel-content');
            content.innerHTML = `
                <div class="entity-card">
                    <div class="entity-type">${escapeHtml(data.type || '')}</div>
                    <div class="entity-name">${escapeHtml(data.label || '')}</div>
                    <div class="entity-file">${escapeHtml(data.filePath || '')}</div>
                </div>
                <div style="margin-top: 15px;">
                    <h4 style="margin-bottom: 10px;">相关信息</h4>
                    <p style="color: #64748b; font-size: 13px;">
                        点击图谱中的节点可以查看详细信息。
                    </p>
                </div>
            `;
        }
        
        function refreshGraph() {
            fetch('/api/graph')
                .then(r => r.json())
                .then(data => renderGraph(data));
            
            fetch('/api/stats')
                .then(r => r.json())
                .then(stats => updateStats(stats));
        }
        
        // 导航切换
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                
                const view = item.dataset.view;
                switchView(view);
            });
        });
        
        function switchView(view) {
            state.currentView = view;
            const container = document.getElementById('graph');
            
            switch(view) {
                case 'graph':
                    refreshGraph();
                    break;
                case 'architecture':
                    showArchitecture(container);
                    break;
                case 'flow':
                    showFlowDiagram(container);
                    break;
                case 'sequence':
                    showSequenceDiagram(container);
                    break;
                case 'files':
                    showFileList(container);
                    break;
                case 'events':
                    showEventLog(container);
                    break;
            }
        }
        
        function showArchitecture(container) {
            container.innerHTML = `
                <div class="architecture-diagram">
                    <div class="arch-layer">
                        <div class="arch-title">用户界面层</div>
                        <div class="arch-modules">
                            <div class="arch-module">
                                <div class="arch-module-name">Visualizer</div>
                                <div class="arch-module-desc">可视化网站</div>
                            </div>
                        </div>
                    </div>
                    <div class="arch-layer">
                        <div class="arch-title">核心控制层</div>
                        <div class="arch-modules">
                            <div class="arch-module">
                                <div class="arch-module-name">Orchestrator</div>
                                <div class="arch-module-desc">任务调度中心</div>
                            </div>
                        </div>
                    </div>
                    <div class="arch-layer">
                        <div class="arch-title">功能模块层</div>
                        <div class="arch-modules">
                            <div class="arch-module">
                                <div class="arch-module-name">FileWatcher</div>
                                <div class="arch-module-desc">文件监控</div>
                            </div>
                            <div class="arch-module">
                                <div class="arch-module-name">ArkTSParser</div>
                                <div class="arch-module-desc">代码解析</div>
                            </div>
                            <div class="arch-module">
                                <div class="arch-module-name">LLMAnalyzer</div>
                                <div class="arch-module-desc">语义分析</div>
                            </div>
                            <div class="arch-module">
                                <div class="arch-module-name">SQLiteStorage</div>
                                <div class="arch-module-desc">数据存储</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function showFlowDiagram(container) {
            container.innerHTML = `
                <div class="flow-container">
                    <div class="flow-step">
                        <div class="flow-number">1</div>
                        <div class="flow-content">
                            <div class="flow-title">文件变更检测</div>
                            <div class="flow-desc">FileWatcher监控文件系统，检测.ets/.ts文件变化</div>
                        </div>
                    </div>
                    <div class="flow-arrow">↓</div>
                    <div class="flow-step">
                        <div class="flow-number">2</div>
                        <div class="flow-content">
                            <div class="flow-title">防抖处理</div>
                            <div class="flow-desc">等待用户停手1秒，避免连续打字触发多次更新</div>
                        </div>
                    </div>
                    <div class="flow-arrow">↓</div>
                    <div class="flow-step">
                        <div class="flow-number">3</div>
                        <div class="flow-content">
                            <div class="flow-title">指纹比对</div>
                            <div class="flow-desc">计算SHA256指纹，确认内容真正发生变化</div>
                        </div>
                    </div>
                    <div class="flow-arrow">↓</div>
                    <div class="flow-step">
                        <div class="flow-number">4</div>
                        <div class="flow-content">
                            <div class="flow-title">增量更新</div>
                            <div class="flow-desc">删除旧数据，解析新内容，插入新数据</div>
                        </div>
                    </div>
                    <div class="flow-arrow">↓</div>
                    <div class="flow-step">
                        <div class="flow-number">5</div>
                        <div class="flow-content">
                            <div class="flow-title">实时推送</div>
                            <div class="flow-desc">WebSocket推送更新，可视化界面实时刷新</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function showSequenceDiagram(container) {
            container.innerHTML = `
                <div class="sequence-container">
<div class="seq-line"><span class="seq-actor">Developer</span>    <span class="seq-action">--&gt;</span> <span class="seq-actor">FileWatcher</span>   : 修改文件</div>
<div class="seq-line"><span class="seq-actor">FileWatcher</span>  <span class="seq-action">--&gt;</span> <span class="seq-actor">FileWatcher</span>   : 防抖等待1秒</div>
<div class="seq-line"><span class="seq-actor">FileWatcher</span>  <span class="seq-action">--&gt;</span> <span class="seq-actor">Orchestrator</span>  : 文件变更事件</div>
<div class="seq-line"><span class="seq-actor">Orchestrator</span> <span class="seq-action">--&gt;</span> <span class="seq-actor">SQLiteStorage</span> : 删除旧数据</div>
<div class="seq-line"><span class="seq-actor">Orchestrator</span> <span class="seq-action">--&gt;</span> <span class="seq-actor">ArkTSParser</span>   : 解析代码</div>
<div class="seq-line"><span class="seq-actor">ArkTSParser</span>  <span class="seq-action">--&gt;</span> <span class="seq-actor">Orchestrator</span>  : 返回实体和关系</div>
<div class="seq-line"><span class="seq-actor">Orchestrator</span> <span class="seq-action">--&gt;</span> <span class="seq-actor">LLMAnalyzer</span>   : 语义分析(异步)</div>
<div class="seq-line"><span class="seq-actor">Orchestrator</span> <span class="seq-action">--&gt;</span> <span class="seq-actor">SQLiteStorage</span> : 插入新数据</div>
<div class="seq-line"><span class="seq-actor">Orchestrator</span> <span class="seq-action">--&gt;</span> <span class="seq-actor">Visualizer</span>    : WebSocket推送</div>
<div class="seq-line"><span class="seq-actor">Visualizer</span>   <span class="seq-action">--&gt;</span> <span class="seq-actor">Browser</span>       : 刷新图谱</div>
                </div>
            `;
        }
        
        function showFileList(container) {
            fetch('/api/stats')
                .then(r => r.json())
                .then(stats => {
                    const files = stats.recent_files || [];
                    container.innerHTML = `
                        <div style="padding: 20px;">
                            <h3 style="margin-bottom: 15px;">最近更新的文件</h3>
                            ${files.map(f => {
                                const safePath = escapeHtml(f.file_path || '');
                                return `
                                <div class="entity-card" style="cursor: pointer;" data-file-path="${safePath}">
                                    <div class="entity-name">${safePath}</div>
                                    <div class="entity-file">
                                        实体数: ${f.entity_count || 0} | 
                                        更新时间: ${f.last_parsed_at ? new Date(f.last_parsed_at * 1000).toLocaleString() : '-'}
                                    </div>
                                </div>`;
                            }).join('')}
                        </div>
                    `;
                    container.querySelectorAll('[data-file-path]').forEach(card => {
                        card.addEventListener('click', () => {
                            showFileGraph(card.dataset.filePath);
                        });
                    });
                });
        }
        
        function showEventLog(container) {
            fetch('/api/events')
                .then(r => r.json())
                .then(events => {
                    container.innerHTML = `
                        <div style="padding: 20px;">
                            <h3 style="margin-bottom: 15px;">系统事件</h3>
                            ${events.map(e => `
                                <div class="entity-card">
                                    <div class="entity-type">${escapeHtml(e.event_type || '')}</div>
                                    <div class="entity-file">${escapeHtml(e.file_path || '-')}</div>
                                    <div style="font-size: 12px; color: #64748b; margin-top: 5px;">
                                        ${escapeHtml(e.details || '')} | 
                                        ${e.duration_ms ? e.duration_ms + 'ms' : ''} |
                                        ${e.created_at ? new Date(e.created_at * 1000).toLocaleString() : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                });
        }
        
        function showFileGraph(filePath) {
            fetch(`/api/file/${encodeURIComponent(filePath)}`)
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('graph');
                    container.innerHTML = `
                        <div style="padding: 20px;">
                            <h3 style="margin-bottom: 15px;">${escapeHtml(data.file_path || '')}</h3>
                            <h4 style="margin: 15px 0 10px;">实体 (${data.entities.length})</h4>
                            ${(data.entities || []).map(e => `
                                <div class="entity-card">
                                    <div class="entity-type">${escapeHtml(e.entity_type || '')}</div>
                                    <div class="entity-name">${escapeHtml(e.name || '')}</div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                });
        }
        
        // 搜索功能 - 显示搜索结果下拉
        let searchTimeout = null;
        document.getElementById('search-input').addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query.length < 2) {
                removeSearchResults();
                return;
            }
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(results => {
                        showSearchResults(results);
                    });
            }, 300);
        });
        
        function showSearchResults(results) {
            removeSearchResults();
            if (!results || results.length === 0) return;
            
            const dropdown = document.createElement('div');
            dropdown.id = 'search-results';
            dropdown.style.cssText = 'position:absolute;top:40px;left:0;width:100%;max-height:300px;overflow-y:auto;background:#1e293b;border:1px solid #334155;border-radius:6px;z-index:100;';
            
            results.forEach(r => {
                const item = document.createElement('div');
                item.style.cssText = 'padding:8px 12px;cursor:pointer;border-bottom:1px solid #334155;font-size:13px;';
                item.innerHTML = `<span style="color:#38bdf8;">[${escapeHtml(r.entity_type || '')}]</span> ${escapeHtml(r.name || '')} <span style="color:#64748b;font-size:11px;">${escapeHtml(r.file_path || '')}</span>`;
                item.addEventListener('click', () => {
                    document.getElementById('search-input').value = r.name || '';
                    removeSearchResults();
                    if (r.file_path) showFileGraph(r.file_path);
                });
                dropdown.appendChild(item);
            });
            
            document.querySelector('.search-box').appendChild(dropdown);
        }
        
        function removeSearchResults() {
            const existing = document.getElementById('search-results');
            if (existing) existing.remove();
        }
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) removeSearchResults();
        });
        
        // 布局切换
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentLayout = btn.dataset.layout;
                // 重新渲染图谱
                refreshGraph();
            });
        });
        
        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            initWebSocket();
            refreshGraph();
        });
    </script>
</body>
</html>"""
    
    def _create_static_files(self) -> None:
        """创建静态文件"""
        # 这里可以创建额外的静态资源
        pass
    
    def run(self) -> None:
        """启动服务器"""
        print(f"[visualizer] 启动服务器: http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="warning")
    
    async def start_async(self) -> None:
        """异步启动服务器"""
        import uvicorn
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        await server.serve()


# 简单测试
if __name__ == '__main__':
    # 创建模拟存储
    class MockStorage:
        def get_statistics(self):
            return {
                'total_files': 10,
                'total_entities': 50,
                'total_relations': 30,
                'entities_by_type': {'class': 10, 'function': 30, 'interface': 10},
                'recent_files': []
            }
        
        def get_dependency_graph(self):
            return {
                'nodes': [
                    {'id': 'n1', 'type': 'class', 'name': 'UserService', 'file_path': '/test.ts'},
                    {'id': 'n2', 'type': 'function', 'name': 'getUser', 'file_path': '/test.ts'}
                ],
                'edges': [
                    {'source': 'n2', 'target': 'n1', 'type': 'calls'}
                ]
            }
        
        def get_file_graph(self, file_path):
            return {
                'file_path': file_path,
                'entities': [],
                'relations': [],
                'dependencies': []
            }
        
        def get_entities(self, file_path=None, entity_type=None):
            return []
        
        def search_entities(self, query, limit=20):
            return []
        
        def get_recent_events(self, limit=50):
            return []
    
    storage = MockStorage()
    server = VisualizerServer(storage, port=8080)
    server.run()
