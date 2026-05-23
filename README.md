# ArkTS Knowledge Graph

一个用于解析 ArkTS/TypeScript 代码并构建知识图谱的系统。

## 功能特性

- **代码解析**: 解析 ArkTS/TypeScript 文件，提取类、方法、属性、继承关系等
- **知识图谱**: 构建代码实体及其关系的知识图谱
- **Web API**: 提供 RESTful API 进行查询
- **自然语言查询**: 支持 LLM 驱动的自然语言查询
- **实时监控**: 支持文件变更的实时监控和增量更新

## 项目结构

```
arkts_knowledge_graph/
├── build_knowledge_graph.py  # 独立构建脚本
├── main_application.py       # 主应用入口
├── core/                     # 核心模块
│   ├── config_manager.py     # 配置管理
│   ├── entity_models.py      # 实体数据模型
│   └── file_watcher.py       # 文件监控
├── database/                 # 数据库层
│   ├── knowledge_repository.py  # 数据持久化
│   └── schema_definitions.py    # Schema 定义
├── parser/                   # 解析器
│   └── ark_analyzer_adapter.py  # ArkTS 解析适配器
├── llm/                      # LLM 集成
│   └── silicon_flow_client.py   # SiliconFlow API 客户端
└── web/                      # Web 服务
    └── server_application.py    # Flask 服务器
```

## 快速开始

### 安装依赖

```bash
pip install flask flask-cors flask-socketio watchdog requests python-dotenv
```

### 构建知识图谱

```bash
python build_knowledge_graph.py --path /path/to/your/arkts/project --force
```

### 启动 Web 服务

```bash
python main_application.py server --port 5000
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取统计信息 |
| GET | `/api/files` | 获取文件列表 |
| GET | `/api/classes` | 获取类列表 |
| GET | `/api/graph` | 获取知识图谱数据 |
| POST | `/api/query` | 自然语言查询 |

## 配置

创建 `.env` 文件配置 LLM API:

```
SILICON_FLOW_API_KEY=your_api_key
SILICON_FLOW_BASE_URL=https://api.siliconflow.cn/v1
```

## 许可证

MIT License
