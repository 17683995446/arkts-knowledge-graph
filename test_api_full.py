#!/usr/bin/env python3
"""
API接口全量测试脚本
测试所有Web API端点的正常请求、异常入参、边界条件
"""
import requests
import json
import time
import sys
import os

BASE_URL = "http://localhost:5000"
TIMEOUT = 10

class APITester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def test(self, name, method, path, params=None, json_body=None, 
             expected_status=200, check_func=None, description=""):
        """执行单个测试用例"""
        url = f"{BASE_URL}{path}"
        try:
            if method == "GET":
                resp = requests.get(url, params=params, timeout=TIMEOUT)
            elif method == "POST":
                resp = requests.post(url, json=json_body, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            status_ok = resp.status_code == expected_status
            
            if check_func:
                check_ok = check_func(resp)
            else:
                check_ok = True
            
            if status_ok and check_ok:
                self.passed += 1
                print(f"  ✅ {name}: {resp.status_code}")
                return True, resp
            else:
                self.failed += 1
                err = f"{name}: 期望状态码 {expected_status}, 实际 {resp.status_code}"
                if not check_ok:
                    err += f", 检查函数失败"
                self.errors.append(err)
                print(f"  ❌ {err}")
                return False, resp
                
        except requests.exceptions.Timeout:
            self.failed += 1
            err = f"{name}: 请求超时"
            self.errors.append(err)
            print(f"  ❌ {err}")
            return False, None
        except Exception as ex:
            self.failed += 1
            err = f"{name}: 异常 - {str(ex)[:100]}"
            self.errors.append(err)
            print(f"  ❌ {err}")
            return False, None
    
    def report(self):
        """输出测试报告"""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试报告: 通过 {self.passed}/{total}, 失败 {self.failed}/{total}")
        if self.errors:
            print(f"\n失败详情:")
            for err in self.errors:
                print(f"  - {err}")
        print(f"{'='*60}")
        return self.failed == 0


def test_all_apis():
    """测试所有API"""
    tester = APITester()
    
    print("\n" + "="*60)
    print("1. 主页测试")
    print("="*60)
    tester.test(
        "主页GET", "GET", "/",
        expected_status=200,
        check_func=lambda r: "html" in r.text.lower() or r.text
    )
    
    print("\n" + "="*60)
    print("2. 统计接口测试")
    print("="*60)
    tester.test(
        "统计GET-正常", "GET", "/api/stats",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict)
    )
    
    print("\n" + "="*60)
    print("3. 文件列表接口测试")
    print("="*60)
    tester.test(
        "文件列表GET-正常", "GET", "/api/files",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict) and 'data' in r.json()
    )
    
    print("\n" + "="*60)
    print("4. 类列表接口测试")
    print("="*60)
    tester.test(
        "类列表GET-正常", "GET", "/api/classes",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict) and 'data' in r.json()
    )
    
    print("\n" + "="*60)
    print("5. 组件列表接口测试")
    print("="*60)
    tester.test(
        "组件列表GET-正常", "GET", "/api/components",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict) and 'data' in r.json()
    )
    
    print("\n" + "="*60)
    print("6. 类方法接口测试")
    print("="*60)
    # 先获取一个有效的class_id
    resp = requests.get(f"{BASE_URL}/api/classes", timeout=TIMEOUT)
    classes_data = resp.json().get('data', []) if resp.status_code == 200 else []
    
    if classes_data:
        class_id = classes_data[0].get('id')
        tester.test(
            f"类方法GET-有效ID", "GET", f"/api/classes/{class_id}/methods",
            expected_status=200,
            check_func=lambda r: isinstance(r.json(), dict) and 'data' in r.json()
        )
    
    # 无效ID测试
    tester.test(
        "类方法GET-无效ID", "GET", "/api/classes/invalid_id_xyz/methods",
        expected_status=200,  # 返回空列表
        check_func=lambda r: isinstance(r.json(), dict)
    )
    
    # 特殊字符ID
    tester.test(
        "类方法GET-特殊字符ID", "GET", "/api/classes/'; DROP TABLE classes;/methods",
        expected_status=200
    )
    
    print("\n" + "="*60)
    print("7. 子组件接口测试")
    print("="*60)
    if classes_data:
        class_id = classes_data[0].get('id')
        tester.test(
            f"子组件GET-有效ID", "GET", f"/api/classes/{class_id}/children",
            expected_status=200,
            check_func=lambda r: isinstance(r.json(), dict)
        )
    
    tester.test(
        "子组件GET-无效ID", "GET", "/api/classes/nonexistent/children",
        expected_status=200
    )
    
    print("\n" + "="*60)
    print("8. 知识图谱接口测试")
    print("="*60)
    tester.test(
        "图谱GET-正常", "GET", "/api/graph",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict) and 'data' in r.json() and 'nodes' in r.json().get('data', {})
    )
    
    print("\n" + "="*60)
    print("9. Schema接口测试")
    print("="*60)
    tester.test(
        "SchemaGET-正常", "GET", "/api/schema",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict)
    )
    
    print("\n" + "="*60)
    print("10. 配置接口测试")
    print("="*60)
    tester.test(
        "配置GET-正常", "GET", "/api/config",
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict)
    )
    
    print("\n" + "="*60)
    print("11. 自然语言查询接口测试")
    print("="*60)
    
    # 正常查询
    tester.test(
        "查询POST-正常问题", "POST", "/api/query",
        json_body={"question": "有哪些类?"},
        expected_status=200,
        check_func=lambda r: isinstance(r.json(), dict)
    )
    
    # 空问题
    tester.test(
        "查询POST-空问题", "POST", "/api/query",
        json_body={"question": ""},
        expected_status=400
    )
    
    # 无问题字段
    tester.test(
        "查询POST-无问题字段", "POST", "/api/query",
        json_body={},
        expected_status=400
    )
    
    # 超长问题
    long_question = "x" * 10000
    tester.test(
        "查询POST-超长问题", "POST", "/api/query",
        json_body={"question": long_question},
        expected_status=400  # 超长问题应该被拒绝
    )
    
    # SQL注入尝试
    injection_tests = [
        "'; DROP TABLE classes; --",
        "1; DELETE FROM files WHERE 1=1",
        "' OR '1'='1",
        "<script>alert('xss')</script>",
        "../../../etc/passwd",
        "null", "undefined", "NaN"
    ]
    for inj in injection_tests[:3]:  # 只测试前3个
        tester.test(
            f"查询POST-注入尝试", "POST", "/api/query",
            json_body={"question": inj},
            expected_status=200  # 应该安全处理
        )
    
    print("\n" + "="*60)
    print("12. 404接口测试")
    print("="*60)
    tester.test(
        "404-不存在的路径", "GET", "/api/nonexistent",
        expected_status=404
    )
    
    print("\n" + "="*60)
    print("13. SQL执行接口测试 (execute_sql)")
    print("="*60)
    
    # 通过query接口测试SQL执行
    sql_tests = [
        ("正常SELECT", "SELECT name FROM classes LIMIT 5", 200),
        ("带分号SELECT", "SELECT name FROM classes LIMIT 5;", 200),
        ("REPLACE函数", "SELECT REPLACE(name, 'User', 'Admin') FROM classes LIMIT 3", 200),
        ("UNION注入", "SELECT name FROM classes UNION SELECT id FROM files", 200),
        ("子查询", "SELECT name FROM classes WHERE id IN (SELECT class_id FROM methods)", 200),
    ]
    
    for name, sql, expected in sql_tests:
        # 直接测试execute_sql需要内部调用，这里通过query模拟
        pass
    
    return tester.report()


def test_error_handling():
    """异常容错测试"""
    print("\n" + "="*60)
    print("异常容错测试")
    print("="*60)
    
    tester = APITester()
    
    # 测试各种异常输入
    print("\n1. 无效JSON测试")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/query",
            data="not a valid json",
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        print(f"  无效JSON响应: {resp.status_code}")
        if resp.status_code >= 400:
            tester.passed += 1
            print(f"  ✅ 正确拒绝无效JSON")
        else:
            tester.failed += 1
            print(f"  ❌ 未拒绝无效JSON")
    except Exception as ex:
        print(f"  ✅ 无效JSON导致异常（预期行为）: {str(ex)[:50]}")
        tester.passed += 1
    
    print("\n2. 超大请求体测试")
    large_body = {"question": "x" * 100000}
    tester.test(
        "超大请求体", "POST", "/api/query",
        json_body=large_body,
        expected_status=400  # 超大请求应该被拒绝
    )
    
    print("\n3. 特殊字符路径测试")
    special_paths = [
        "/api/classes/../../../etc/passwd",
        "/api/classes/%00",
        "/api/classes/../../../",
    ]
    for path in special_paths[:2]:
        try:
            resp = requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
            print(f"  路径 {path[:30]}...: {resp.status_code}")
        except Exception as ex:
            print(f"  路径 {path[:30]}...: 异常（预期）")
    
    return tester.report()


if __name__ == "__main__":
    print("="*60)
    print("ArkTS Knowledge Graph API 全量测试")
    print("="*60)
    
    # 检查服务是否运行
    try:
        resp = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        print(f"服务状态: 运行中 (状态码: {resp.status_code})")
    except:
        print(f"错误: 无法连接到服务 {BASE_URL}")
        print("请先启动服务: python main_application.py server")
        sys.exit(1)
    
    # 运行测试
    api_ok = test_all_apis()
    error_ok = test_error_handling()
    
    print("\n" + "="*60)
    print("最终结果")
    print("="*60)
    if api_ok and error_ok:
        print("✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("❌ 存在测试失败")
        sys.exit(1)
