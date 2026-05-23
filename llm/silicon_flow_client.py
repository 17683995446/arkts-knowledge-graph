"""
Silicon Flow LLM Client Module

Provides integration with Silicon Flow's Qwen2.5-7B API for natural language
to SQL conversion and code analysis queries.
"""

import json
import time
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM API."""
    success: bool
    content: str
    error_message: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0.0


class SiliconFlowClient:
    """
    Client for Silicon Flow LLM API.
    
    Provides methods for:
    - Natural language to SQL conversion
    - Code analysis queries
    - General question answering about code
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        timeout_seconds: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize the Silicon Flow client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            model: Model name to use
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.chat_endpoint = f"{self.base_url}/chat/completions"
    
    def _make_request(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> LLMResponse:
        """
        Make a request to the LLM API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (lower = more deterministic)
        
        Returns:
            LLMResponse object
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2048,
            "stream": False
        }
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.chat_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    tokens_used = data.get('usage', {}).get('total_tokens', 0)
                    
                    return LLMResponse(
                        success=True,
                        content=content,
                        tokens_used=tokens_used,
                        latency_ms=latency_ms
                    )
                else:
                    error_msg = f"API error: {response.status_code} - {response.text}"
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return LLMResponse(
                        success=False,
                        content="",
                        error_message=error_msg,
                        latency_ms=latency_ms
                    )
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return LLMResponse(
                    success=False,
                    content="",
                    error_message="Request timeout",
                    latency_ms=(time.time() - start_time) * 1000
                )
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return LLMResponse(
                    success=False,
                    content="",
                    error_message=f"Request failed: {str(e)}",
                    latency_ms=(time.time() - start_time) * 1000
                )
        
        return LLMResponse(
            success=False,
            content="",
            error_message="Max retries exceeded"
        )
    
    def natural_language_to_sql(self, question: str, schema_info: str) -> LLMResponse:
        """
        Convert natural language question to SQL query.
        
        Args:
            question: Natural language question about the code
            schema_info: Database schema information
        
        Returns:
            LLMResponse containing the SQL query
        """
        system_prompt = """You are a SQL expert. Convert natural language questions about code structure into SQL queries.

Rules:
1. Only return the SQL query, no explanation
2. Use standard SQLite syntax
3. Use table aliases for readability
4. Handle case-insensitive searches with LOWER()
5. Return meaningful columns, use * only when necessary
6. Limit results to 100 rows unless specified otherwise
7. If the question cannot be answered with the schema, return "-- CANNOT_CONVERT"

Available tables and columns:
"""
        
        user_prompt = f"{schema_info}\n\nQuestion: {question}\n\nSQL Query:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self._make_request(messages, temperature=0.1)
    
    def explain_code_structure(self, code_summary: str) -> LLMResponse:
        """
        Get an explanation of code structure.
        
        Args:
            code_summary: Summary of code structure
        
        Returns:
            LLMResponse containing the explanation
        """
        system_prompt = """You are a code analysis expert. Explain code structure in clear, concise terms.
Focus on:
1. Overall architecture
2. Key components and their relationships
3. Important patterns used
4. Entry points and data flow

Keep explanations under 200 words."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this code structure:\n\n{code_summary}"}
        ]
        
        return self._make_request(messages, temperature=0.3)
    
    def suggest_refactoring(self, code_context: str, issue_description: str) -> LLMResponse:
        """
        Get refactoring suggestions.
        
        Args:
            code_context: Context of the code to refactor
            issue_description: Description of the issue
        
        Returns:
            LLMResponse containing refactoring suggestions
        """
        system_prompt = """You are a code refactoring expert. Provide specific, actionable refactoring suggestions.
Format your response as:
1. Issue Summary
2. Suggested Changes (with code examples if applicable)
3. Expected Benefits"""
        
        user_prompt = f"Code Context:\n{code_context}\n\nIssue: {issue_description}\n\nProvide refactoring suggestions:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self._make_request(messages, temperature=0.4)
    
    def answer_code_question(self, question: str, context: str) -> LLMResponse:
        """
        Answer a general question about code.
        
        Args:
            question: The question to answer
            context: Context about the code
        
        Returns:
            LLMResponse containing the answer
        """
        system_prompt = """You are a helpful coding assistant. Answer questions about code based on the provided context.
Be concise and accurate. If you don't have enough information, say so."""
        
        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self._make_request(messages, temperature=0.3)


class QueryEngine:
    """
    Query engine that combines LLM with database queries.
    
    Provides a high-level interface for asking questions about code.
    """
    
    def __init__(self, llm_client: SiliconFlowClient, schema_info: str):
        self.llm_client = llm_client
        self.schema_info = schema_info
    
    def ask(self, question: str, db_execute_func) -> Dict[str, Any]:
        """
        Ask a question and get results.
        
        Args:
            question: Natural language question
            db_execute_func: Function to execute SQL queries
        
        Returns:
            Dictionary with question, sql, results, and explanation
        """
        # Convert question to SQL
        sql_response = self.llm_client.natural_language_to_sql(question, self.schema_info)
        
        if not sql_response.success:
            return {
                "success": False,
                "question": question,
                "error": sql_response.error_message,
                "sql": None,
                "results": None
            }
        
        sql = sql_response.content.strip()
        
        # Check if conversion failed
        if sql.startswith("-- CANNOT_CONVERT"):
            return {
                "success": False,
                "question": question,
                "error": "Question cannot be answered with available data",
                "sql": None,
                "results": None
            }
        
        # Clean up SQL (remove markdown code blocks if present)
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        
        # Execute SQL
        try:
            results = db_execute_func(sql)
            
            return {
                "success": True,
                "question": question,
                "sql": sql,
                "results": results,
                "latency_ms": sql_response.latency_ms,
                "tokens_used": sql_response.tokens_used
            }
        except Exception as e:
            return {
                "success": False,
                "question": question,
                "sql": sql,
                "error": f"SQL execution error: {str(e)}",
                "results": None
            }
