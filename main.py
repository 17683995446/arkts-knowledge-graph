"""
ArkTS 知识图谱系统 - 主入口
支持命令行构建和Web服务启动
"""
import os
import sys
import argparse
import logging
import time

# 将项目根目录加入Python路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.global_settings import WEB_HOST, WEB_PORT, WEB_DEBUG, DATABASE_DIRECTORY


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_build(args):
    """执行构建命令"""
    from core.scheduler.build_orchestrator import BuildOrchestrator

    project_path = os.path.abspath(args.project)
    if not os.path.isdir(project_path):
        print(f"错误: 项目目录不存在: {project_path}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"  ArkTS 知识图谱构建器")
    print(f"{'='*60}")
    print(f"  项目路径: {project_path}")
    print(f"  构建模式: {'增量' if args.incremental else '全量'}")
    print(f"{'='*60}")

    orchestrator = BuildOrchestrator(project_path)

    if args.incremental:
        report = orchestrator.incremental_build(show_progress=True)
    else:
        report = orchestrator.full_build(show_progress=True)

    # 打印构建报告
    print(f"\n{'='*60}")
    print(f"  构建报告")
    print(f"{'='*60}")
    print(f"  构建模式:     {report.build_mode}")
    print(f"  扫描文件:     {report.total_files_scanned}")
    print(f"  扫描代码行:   {report.total_lines_scanned}")
    print(f"  变更文件:     {report.files_changed}")
    print(f"  删除文件:     {report.files_deleted}")
    print(f"  解析成功:     {report.parse_success}")
    print(f"  解析失败:     {report.parse_failure}")
    print(f"  数据库大小:   {report.database_size_mb} MB")
    print(f"  扫描耗时:     {report.scan_time_ms:.0f} ms")
    print(f"  解析耗时:     {report.parse_time_ms:.0f} ms")
    print(f"  写入耗时:     {report.write_time_ms:.0f} ms")
    print(f"  总耗时:       {report.total_time_ms:.0f} ms ({report.total_time_ms/1000:.1f}s)")

    if report.error:
        print(f"  错误:         {report.error}")

    print(f"{'='*60}")
    print(f"  数据库位置:   {DATABASE_DIRECTORY}/knowledge_graph.db")
    print(f"{'='*60}")


def cmd_server(args):
    """启动Web服务器"""
    from web.flask_application import run_server

    print(f"{'='*60}")
    print(f"  ArkTS 知识图谱 Web 服务")
    print(f"{'='*60}")
    print(f"  地址: http://{args.host}:{args.port}")
    print(f"{'='*60}")

    run_server(host=args.host, port=args.port, debug=args.debug)


def cmd_demo(args):
    """运行演示（构建示例项目 + 启动Web服务）"""
    from core.scheduler.build_orchestrator import BuildOrchestrator
    from web.flask_application import run_server

    sample_path = os.path.join(PROJECT_ROOT, "sample_project")

    print(f"{'='*60}")
    print(f"  ArkTS 知识图谱 - 演示模式")
    print(f"{'='*60}")

    # 构建
    print("\n📦 正在构建示例项目知识图谱...")
    orchestrator = BuildOrchestrator(sample_path)
    report = orchestrator.full_build(show_progress=True)

    print(f"\n✅ 构建完成!")
    print(f"   文件: {report.total_files_scanned}")
    print(f"   代码行: {report.total_lines_scanned}")
    print(f"   数据库: {report.database_size_mb} MB")
    print(f"   耗时: {report.total_time_ms/1000:.1f}s")

    # 启动Web服务
    print(f"\n🌐 启动Web服务: http://{args.host}:{args.port}")
    print(f"{'='*60}")
    run_server(host=args.host, port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(
        description="ArkTS 知识图谱系统 - 百万行级鸿蒙代码分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py demo                    # 演示模式（构建示例项目 + 启动Web）
  python main.py build ./my_project      # 全量构建
  python main.py build ./my_project -i   # 增量构建
  python main.py server                  # 启动Web服务
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # demo 命令
    demo_parser = subparsers.add_parser("demo", help="演示模式")
    demo_parser.add_argument("--host", default=WEB_HOST, help="Web服务地址")
    demo_parser.add_argument("--port", type=int, default=WEB_PORT, help="Web服务端口")
    demo_parser.add_argument("--debug", action="store_true", help="调试模式")

    # build 命令
    build_parser = subparsers.add_parser("build", help="构建知识图谱")
    build_parser.add_argument("project", help="项目根目录路径")
    build_parser.add_argument("-i", "--incremental", action="store_true", help="增量构建")
    build_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # server 命令
    server_parser = subparsers.add_parser("server", help="启动Web服务")
    server_parser.add_argument("--host", default=WEB_HOST, help="服务地址")
    server_parser.add_argument("--port", type=int, default=WEB_PORT, help="服务端口")
    server_parser.add_argument("--debug", action="store_true", help="调试模式")

    args = parser.parse_args()

    if args.command == "demo":
        setup_logging()
        cmd_demo(args)
    elif args.command == "build":
        setup_logging(args.verbose)
        cmd_build(args)
    elif args.command == "server":
        setup_logging()
        cmd_server(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
