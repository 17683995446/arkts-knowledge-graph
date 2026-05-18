"""
自然语言查询引擎
将用户的自然语言问题转换为SQL查询并执行
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List
from core.query.siliconflow_client import SiliconFlowClient
from core.database.graph_query_service import GraphQueryService

logger = logging.getLogger(__name__)


# 系统提示词 - 教LLM如何生成SQL
SYSTEM_PROMPT = """你是一个ArkTS代码知识图谱的SQL查询专家。你的任务是将用户的自然语言问题转换为SQLite查询语句。

## 数据库Schema

```sql
-- 文件表
CREATE TABLE files(id INTEGER PRIMARY KEY, path TEXT UNIQUE, hash BLOB, line_count INTEGER, language TEXT, last_scanned REAL);

-- 类/接口/枚举表
CREATE TABLE classes(id INTEGER PRIMARY KEY, name TEXT, file_id INTEGER, start_line INTEGER, end_line INTEGER, flags INTEGER, parent_class_id INTEGER, doc_comment TEXT);

-- 方法/函数表
CREATE TABLE methods(id INTEGER PRIMARY KEY, name TEXT, class_id INTEGER, file_id INTEGER, start_line INTEGER, end_line INTEGER, flags INTEGER, return_type TEXT, parameters TEXT, doc_comment TEXT);

-- 属性表
CREATE TABLE properties(id INTEGER PRIMARY KEY, name TEXT, class_id INTEGER, file_id INTEGER, type_annotation TEXT, flags INTEGER, default_value TEXT, start_line INTEGER);

-- 调用关系表
CREATE TABLE calls(caller_id INTEGER, callee_id INTEGER, call_type INTEGER, line_number INTEGER, PRIMARY KEY(caller_id, callee_id));

-- 组件关系表
CREATE TABLE components(parent_id INTEGER, child_id INTEGER, relation_type INTEGER, PRIMARY KEY(parent_id, child_id));

-- 导入关系表
CREATE TABLE imports(source_file_id INTEGER, target_file_id INTEGER, import_path TEXT, is_default INTEGER, PRIMARY KEY(source_file_id, target_file_id));

-- 装饰器表
CREATE TABLE decorators(id INTEGER PRIMARY KEY, name TEXT, target_type INTEGER, target_id INTEGER, arguments TEXT);

-- 继承关系表
CREATE TABLE inheritance(child_id INTEGER, parent_id INTEGER, type INTEGER, PRIMARY KEY(child_id, parent_id));

-- 命名空间表
CREATE TABLE namespaces(id INTEGER PRIMARY KEY, name TEXT, file_id INTEGER, start_line INTEGER, end_line INTEGER);

-- 构建元数据表
CREATE TABLE build_metadata(key TEXT PRIMARY KEY, value TEXT, updated_at REAL);
```

## flags 字段说明
- classes.flags: 1=接口, 2=抽象, 4=枚举, 8=结构体, 16=泛型, 32=导出, 64=Entry组件
- methods.flags: 1=静态, 2=异步, 4=私有, 8=保护, 16=重写, 32=getter, 64=setter, 128=构造函数, 256=生命周期
- properties.flags: 1=静态, 2=私有, 4=只读, 8=State, 16=Link, 32=Prop, 64=Provide

## 查询规则
1. 只生成 SELECT 查询，绝不生成修改数据的SQL
2. 使用 JOIN 关联表以获取完整信息
3. 使用 LIKE 进行模糊搜索
4. 限制结果数量（LIMIT 50）
5. 返回格式：直接返回SQL语句，不要加任何解释或markdown标记
6. 如果问题无法用SQL回答，返回 "NONE:" 加上解释

## 示例
用户: "有哪些类"
SQL: SELECT c.name, f.path FROM classes c JOIN files f ON c.file_id = f.id ORDER BY c.name LIMIT 50;

用户: "查找名为HomePage的类"
SQL: SELECT c.*, f.path FROM classes c JOIN files f ON c.file_id = f.id WHERE c.name LIKE '%HomePage%';

用户: "统计每个文件的类数量"
SQL: SELECT f.path, COUNT(c.id) as class_count FROM files f LEFT JOIN classes c ON f.id = c.file_id GROUP BY f.id HAVING class_count > 0 ORDER BY class_count DESC LIMIT 50;

用户: "找出所有被调用的方法"
SQL: SELECT DISTINCT m.name, m2.name as caller_name FROM methods m JOIN calls ca ON ca.callee_id = m.id JOIN methods m2 ON ca.caller_id = m2.id LIMIT 50;
"""


class NaturalLanguageQueryEngine:
    """
    自然语言查询引擎
    1. 接收用户的自然语言问题
    2. 调用LLM生成SQL
    3. 执行SQL获取结果
    4. 调用LLM生成自然语言回答
    """

    def __init__(self):
        self._llm_client = SiliconFlowClient()
        self._query_service = GraphQueryService()
        self._conversation_history: List[Dict[str, str]] = []

    def query(self, question: str) -> Dict[str, Any]:
        """
        处理自然语言查询
        Args:
            question: 用户的问题
        Returns:
            {"sql": str, "results": list, "answer": str, "error": str}
        """
        # 1. 生成SQL
        sql = self._generate_sql(question)
        if sql.startswith("NONE:"):
            return {
                "sql": "",
                "results": [],
                "answer": sql[5:].strip(),
                "error": "",
            }

        # 2. 执行SQL
        try:
            results = self._query_service.execute_raw_sql(sql)
        except Exception as e:
            return {
                "sql": sql,
                "results": [],
                "answer": f"SQL执行错误: {e}",
                "error": str(e),
            }

        # 3. 生成自然语言回答
        answer = self._generate_answer(question, sql, results)

        # 4. 保存对话历史
        self._conversation_history.append({"role": "user", "content": question})
        self._conversation_history.append({"role": "assistant", "content": answer})

        # 限制历史长度
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[-20:]

        return {
            "sql": sql,
            "results": results,
            "answer": answer,
            "error": "",
        }

    def _generate_sql(self, question: str) -> str:
        """调用LLM生成SQL"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        response = self._llm_client.chat_completion(messages, temperature=0.1)

        # 清理响应
        sql = response.strip()
        # 移除可能的markdown代码块标记
        sql = re.sub(r'^```sql\s*', '', sql)
        sql = re.sub(r'^```\s*', '', sql)
        sql = re.sub(r'\s*```$', '', sql)
        sql = sql.strip().rstrip(';') + ';'

        logger.info(f"LLM生成SQL: {sql}")
        return sql

    def _generate_answer(self, question: str, sql: str,
                          results: List[Dict]) -> str:
        """调用LLM根据查询结果生成自然语言回答"""
        if not results:
            return "查询结果为空，没有找到匹配的数据。"

        # 限制结果展示数量
        display_results = results[:20]

        # 构建结果摘要
        result_summary = json.dumps(display_results, ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": "你是一个代码知识图谱助手。根据SQL查询结果，用简洁的中文回答用户的问题。"},
            {"role": "user", "content": f"用户问题: {question}\n\nSQL: {sql}\n\n查询结果:\n{result_summary}\n\n请用中文总结回答。"},
        ]

        answer = self._llm_client.chat_completion(messages, temperature=0.3)
        return answer.strip()

    def clear_history(self) -> None:
        """清空对话历史"""
        self._conversation_history.clear()

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return list(self._conversation_history)
