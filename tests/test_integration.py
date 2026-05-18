"""
集成测试 - 验证核心模块功能
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class TestLexer(unittest.TestCase):
    """测试词法分析器"""

    def test_tokenize_basic(self):
        from core.parser.arkts_lexer import ArkTSLexer, TokenType
        source = "class MyClass { private name: string = '' }"
        lexer = ArkTSLexer(source)
        tokens = lexer.tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.KEYWORD, types)
        self.assertIn(TokenType.IDENTIFIER, types)
        self.assertIn(TokenType.PUNCTUATION, types)

    def test_tokenize_decorator(self):
        from core.parser.arkts_lexer import ArkTSLexer, TokenType
        source = "@Entry\n@Component\nstruct MyPage {}"
        lexer = ArkTSLexer(source)
        tokens = lexer.tokenize()
        dec_tokens = [t for t in tokens if t.type == TokenType.DECORATOR]
        self.assertEqual(len(dec_tokens), 2)

    def test_tokenize_import(self):
        from core.parser.arkts_lexer import ArkTSLexer, TokenType
        source = "import { User } from './model'"
        lexer = ArkTSLexer(source)
        tokens = lexer.tokenize()
        keywords = [t for t in tokens if t.type == TokenType.KEYWORD and t.value == "import"]
        self.assertEqual(len(keywords), 1)


class TestParser(unittest.TestCase):
    """测试语法分析器"""

    def test_parse_class(self):
        from core.parser.arkts_parser import ArkTSParser
        source = """
        @Entry
        @Component
        export class MainPage {
            @State message: string = 'Hello'
            private count: number = 0

            aboutToAppear() {
                this.initData()
            }

            private initData() {
                this.message = 'Welcome'
            }

            build() {
                Column() {
                    Text(this.message)
                }
            }
        }
        """
        parser = ArkTSParser(source, "test.ets")
        file_node = parser.parse()
        self.assertGreater(len(file_node.children), 0)

        class_node = file_node.children[0]
        self.assertEqual(class_node.name, "MainPage")
        self.assertIn("Entry", class_node.decorators)
        self.assertIn("Component", class_node.decorators)
        self.assertTrue(class_node.is_exported)

    def test_parse_interface(self):
        from core.parser.arkts_parser import ArkTSParser
        source = "interface UserInfo { id: string; name: string; }"
        parser = ArkTSParser(source, "test.ets")
        file_node = parser.parse()
        self.assertEqual(len(file_node.children), 1)
        self.assertTrue(file_node.children[0].is_interface)

    def test_parse_enum(self):
        from core.parser.arkts_parser import ArkTSParser
        source = "enum Status { ACTIVE, INACTIVE, DELETED }"
        parser = ArkTSParser(source, "test.ets")
        file_node = parser.parse()
        self.assertEqual(len(file_node.children), 1)
        self.assertTrue(file_node.children[0].is_enum)

    def test_parse_function(self):
        from core.parser.arkts_parser import ArkTSParser
        source = "function formatDate(date: Date): string { return '' }"
        parser = ArkTSParser(source, "test.ets")
        file_node = parser.parse()
        self.assertEqual(len(file_node.children), 1)


class TestFileParser(unittest.TestCase):
    """测试文件解析器"""

    def test_parse_full_file(self):
        from core.parser.arkts_file_parser import ArkTSFileParser
        source = """
        @Entry
        @Component
        export class IndexPage {
            @State message: string = 'Hello'
            @Link counter: number

            aboutToAppear() {
                this.initData()
            }

            private initData() {
                this.message = 'Welcome'
                this.loadData()
            }

            private loadData() {
                const data = this.fetchData()
                this.processData(data)
            }

            private fetchData(): string {
                return 'data'
            }

            private processData(data: string) {
                console.log(data)
            }

            build() {
                Column() {
                    Text(this.message)
                        .onClick(() => {
                            this.handleClick()
                        })
                }
            }

            private handleClick() {
                this.message = 'Clicked'
            }
        }
        """
        parser = ArkTSFileParser()
        result = parser.parse_file("test/IndexPage.ets", source)

        self.assertEqual(result.file_path, "test/IndexPage.ets")
        self.assertGreater(result.line_count, 0)
        self.assertEqual(len(result.classes), 1)
        self.assertEqual(result.classes[0]["name"], "IndexPage")
        self.assertGreater(len(result.methods), 0)
        self.assertGreater(len(result.properties), 0)
        self.assertGreater(len(result.calls), 0)
        self.assertGreater(len(result.decorators), 0)
        self.assertEqual(result.error, "")


class TestDatabase(unittest.TestCase):
    """测试数据库模块"""

    @classmethod
    def setUpClass(cls):
        from core.database.database_initializer import DatabaseInitializer
        cls.db_init = DatabaseInitializer()
        cls.db_init.initialize_database(force_recreate=True)

    def test_database_ready(self):
        self.assertTrue(self.db_init.is_database_ready())

    def test_tables_exist(self):
        tables = self.db_init.get_database_stats()
        self.assertIn("files", tables)
        self.assertIn("classes", tables)
        self.assertIn("methods", tables)
        self.assertIn("calls", tables)

    def test_batch_writer(self):
        from core.database.batch_writer import BatchWriter
        writer = BatchWriter()
        writer.add_record("files", {"path": "/test.ts", "hash": b"test", "line_count": 10, "language": "arkts", "last_scanned": 0})
        count = writer.flush_all()
        self.assertGreater(count, 0)


class TestScanner(unittest.TestCase):
    """测试项目扫描器"""

    def test_scan_sample_project(self):
        from core.scanner.project_scanner import ProjectScanner
        sample_path = os.path.join(PROJECT_ROOT, "sample_project")
        if not os.path.isdir(sample_path):
            self.skipTest("示例项目不存在")
        scanner = ProjectScanner(sample_path)
        result = scanner.scan_all_files()
        self.assertGreater(result.total_files, 0)
        self.assertGreater(result.total_lines, 0)


class TestBuildOrchestrator(unittest.TestCase):
    """测试构建编排器"""

    def test_full_build_sample(self):
        from core.scheduler.build_orchestrator import BuildOrchestrator
        sample_path = os.path.join(PROJECT_ROOT, "sample_project")
        if not os.path.isdir(sample_path):
            self.skipTest("示例项目不存在")

        orchestrator = BuildOrchestrator(sample_path)
        report = orchestrator.full_build(show_progress=False)

        self.assertEqual(report.build_mode, "full")
        self.assertGreater(report.total_files_scanned, 0)
        self.assertGreater(report.parse_success, 0)
        self.assertEqual(report.error, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
