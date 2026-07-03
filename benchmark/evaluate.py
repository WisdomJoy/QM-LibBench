# benchmark/evaluate.py

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

from loader import load_task, list_tasks
from prepare import prepare_workspace, cleanup_workspace
from repo_config import get_repo_config


# 配置
PRED_DIR = Path("../predictions")  # 预测补丁目录
RESULTS_DIR = Path("../results")   # 结果目录
DOCKER_IMAGE = "qml-bench"    # Docker 镜像名
KEEP_WORKSPACE = False             # 是否保留工作区（调试用）


def get_patch_tasks(pred_dir: Path = None) -> List[str]:
    """
    从 predictions 目录读取所有补丁文件，提取任务名
    
    Args:
        pred_dir: 补丁目录
    
    Returns:
        List[str]: 任务名列表（按字母排序）
    """
    
    if pred_dir is None:
        pred_dir = PRED_DIR
    
    if not pred_dir.exists():
        print(f"⚠️ 补丁目录不存在: {pred_dir}")
        return []
    
    # 获取所有 .patch 文件
    patch_files = list(pred_dir.glob("*.patch"))
    
    if not patch_files:
        print(f"⚠️ 补丁目录中没有 .patch 文件: {pred_dir}")
        return []
    
    # 提取任务名（文件名不带扩展名）
    tasks = sorted([p.stem for p in patch_files])
    
    print(f"找到 {len(tasks)} 个补丁文件")
    return tasks


def check_tasks_exist(
    tasks: List[str],
    repo_names: Optional[List[str] | str] = None
) -> Dict[str, bool]:
    """
    检查任务是否存在于 tasks 目录
    
    Args:
        tasks: 任务名列表
        repo_names: 一个或多个仓库名；指定后只在这些仓库的三层目录任务中检查
    
    Returns:
        Dict[str, bool]: 任务名 -> 是否存在
    """
    
    all_tasks = set(list_tasks(repo_names=repo_names))
    return {task: task in all_tasks for task in tasks}

def apply_patch(repo_path: Path, patch_file: Path) -> bool:
    """
    应用补丁到仓库
    
    Args:
        repo_path: 仓库路径
        patch_file: 补丁文件路径
    
    Returns:
        bool: 是否成功应用
    """
    
    # 1. 检查补丁文件是否存在
    if not patch_file.exists():
        print(f"❌ 补丁文件不存在: {patch_file}")
        return False
    
    # 2. 检查补丁文件是否为空
    if patch_file.stat().st_size == 0:
        print(f"⚠️ 补丁文件为空: {patch_file}")
        return False
    
    try:
        # 3. 先检查补丁是否可以应用（--check 模式）
        check_result = subprocess.run(
            ["git", "apply", "--check", str(patch_file.resolve())],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if check_result.returncode != 0:
            print(f"⚠️ 补丁检查失败:\n{check_result.stderr}")
            return False
        
        # 4. 应用补丁
        subprocess.run(
            ["git", "apply", str(patch_file.resolve())],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✅ 补丁已应用: {patch_file.name}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 应用补丁失败: {e.stderr}")
        return False

def _metadata_command_executables(task) -> List[str]:
    commands = (
        task.metadata.get("correctness_test_commands", [])
        + task.metadata.get("performance_test_commands", [])
    )
    
    executables = []
    seen = set()
    for command in commands:
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        
        if not parts:
            continue
        
        name = Path(parts[0]).name
        if name and name not in seen:
            executables.append(name)
            seen.add(name)
    
    return executables


def docker_environment_args(task) -> List[str]:
    env_args = []
    
    if task.repo == "libjpeg":
        targets = _metadata_command_executables(task)
        if targets:
            env_args.extend(["-e", f"LIBJPEG_TARGETS={' '.join(targets)}"])
    
    return env_args


def _copy_named_binaries(search_root: Path, names: List[str], bins_dir: Path) -> int:
    copied_count = 0
    
    if not search_root.exists():
        print(f"⚠️ build 目录不存在: {search_root}")
        return copied_count
    
    for name in names:
        candidates = [p for p in search_root.rglob(name) if p.is_file()]
        
        if not candidates:
            print(f"   ⚠️ 文件不存在: {name}")
            continue
        
        src = candidates[0]
        dst = bins_dir / name
        shutil.copy2(src, dst)
        print(f"   ✅ 已保存: {name} ({src.relative_to(search_root)})")
        copied_count += 1
    
    return copied_count


def save_bin_files(repo_path: Path, task) -> Path:
    """
    保存 Docker 中生成的 bin 文件到本地
    
    Args:
        repo_path: 仓库路径
        task: 任务对象
    
    Returns:
        Path: 保存的目录路径
    """
    
    # 1. 创建保存目录: ../bins/{task_id}/
    bins_dir = Path("../bins") / task.task_id
    bins_dir.mkdir(parents=True, exist_ok=True)
    
    repo_config = get_repo_config(task.repo)
    
    # 2. 确定要保存的文件列表
    repo = task.repo
    module = task.metadata.get("module", "")
    
    files_to_save = []
    
    if repo == "opencv":
        if module == "core":
            files_to_save = [
                "opencv_test_core",
                "opencv_perf_core"
            ]
        elif module == "imgproc":
            files_to_save = [
                "opencv_test_imgproc",
                "opencv_perf_imgproc"
            ]
        else:
            print(f"⚠️ 未知的 OpenCV 模块: {module}")
            return bins_dir
    elif repo == "ncnn":
        files_to_save = [
            f"test_{task.operator}",
            f"perf_{task.operator}",
        ]
    elif repo == "libjpeg":
        files_to_save = _metadata_command_executables(task)
        if not files_to_save:
            print("⚠️ libjpeg 任务没有 correctness/performance 命令，无法推导 bin 文件")
            return bins_dir
    
    # 3. 从 repo 对应 build 目录中复制文件
    build_bin_dir = repo_path / repo_config.build_bin_dir
    copied_count = _copy_named_binaries(build_bin_dir, files_to_save, bins_dir)
    
    print(f"\n📁 Bin 文件已保存到: {bins_dir}")
    print(f"   共保存 {copied_count}/{len(files_to_save)} 个文件")
    
    return bins_dir

def run_docker(repo_path: Path, task, docker_image: str = DOCKER_IMAGE) -> Dict[str, Any]:
    """
    在 Docker 容器中运行评估
    
    Args:
        repo_path: 仓库路径
        task: 任务对象
        docker_image: Docker 镜像名
    
    Returns:
        Dict: 包含 returncode, stdout, stderr
    """
    
    # 检查 Docker 是否可用
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "Docker 不可用或未安装"
        }
    
    # 检查镜像是否存在
    check_image = subprocess.run(
        ["docker", "image", "inspect", docker_image],
        capture_output=True,
        text=True
    )
    
    if check_image.returncode != 0:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Docker 镜像不存在: {docker_image}\n请先构建: docker build -t {docker_image} ."
        }
    
    try:
        repo_config = get_repo_config(task.repo)
        entrypoint = repo_config.entrypoint_for(task)
    except ValueError as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e)
        }
    
    # 运行容器
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--entrypoint",
                entrypoint,
                *docker_environment_args(task),
                "--user",              # 新增：指定用户
                f"{os.getuid()}:{os.getgid()}",  # 使用当前用户的 UID:GID
                "-v",
                f"{repo_path.resolve()}:{repo_config.mount_path}",
                "-w",
                repo_config.mount_path,
                docker_image
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

            
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "Docker 运行超时 (300s)"
        }
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Docker 运行失败: {e}"
        }
        
def evaluate_task(task_name: str) -> Dict[str, Any]:
    """
    评估单个任务
    
    Args:
        task_name: 任务名称，格式为 {repo}_{source_arch}_{target_arch}_{operator}
                  例如: opencv_arm_riscv_absdiff
    
    Returns:
        Dict: 评估结果
    """
    
    print(f"\n{'=' * 60}")
    print(f"Evaluating: {task_name}")
    print(f"{'=' * 60}")
    
    # 1. 检查补丁文件
    patch_file = PRED_DIR / f"{task_name}.patch"
    
    if not patch_file.exists():
        print(f"❌ 补丁文件不存在: {patch_file}")
        return {
            "task": task_name,
            "status": "missing_patch",
            "score": 0,
            "error": f"Patch file not found: {patch_file}"
        }
    
    if patch_file.stat().st_size == 0:
        print(f"⚠️ 补丁文件为空: {patch_file}")
        return {
            "task": task_name,
            "status": "empty_patch",
            "score": 0,
            "error": "Patch file is empty"
        }
    
    repo_path = None
    
    try:
        # 2. 加载任务（使用新的 load_task）
        task = load_task(task_name)
        print(f"✅ 任务加载成功:")
        print(f"   仓库: {task.repo}")
        print(f"   源架构: {task.source_arch}")
        print(f"   目标架构: {task.target_arch}")
        print(f"   算子: {task.operator}")
        print(f"   Task ID: {task.task_id}")
        
        # 3. 准备仓库（从基准开始）
        print("\n准备仓库...")
        repo_path, commit_id_start = prepare_workspace(task)
        print(f"✅ 仓库已准备: {repo_path}")
        print(f"   基准 Commit: {commit_id_start[:8]}")
        
        # 4. 应用补丁
        print("\n应用补丁...")
        if not apply_patch(repo_path, patch_file):
            return {
                "task": task_name,
                "task_id": task.task_id,
                "status": "patch_failed",
                "score": 0,
                "error": "Failed to apply patch"
            }
        
        # 5. 运行 Docker 评估
        print("\n运行 Docker 评估...")
        result = run_docker(repo_path, task)
        
        passed = result["returncode"] == 0
        
        # =====保存 bin 文件 =====
        if passed:
            print("\n保存 Bin 文件...")
            bins_dir = save_bin_files(repo_path, task)
        else:
            print("\n跳过 Bin 保存: 编译失败，未生成完整可执行文件")
        
        # 6. 构建结果
        evaluation_result = {
            "task": task_name,
            "task_id": task.task_id,
            "repo": task.repo,
            "source_arch": task.source_arch,
            "target_arch": task.target_arch,
            "operator": task.operator,
            "status": "passed" if passed else "failed",
            "score": 1 if passed else 0,
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"]
        }
        
        print(f"\n✅ 编译完成: {'PASSED' if passed else 'FAILED'}")
        
        return evaluation_result
        
    except FileNotFoundError as e:
        print(f"❌ 文件不存在: {e}")
        return {
            "task": task_name,
            "status": "task_not_found",
            "score": 0,
            "error": str(e)
        }
    except ValueError as e:
        print(f"❌ 任务名解析错误: {e}")
        return {
            "task": task_name,
            "status": "error",
            "score": 0,
            "error": str(e)
        }
    except Exception as e:
        print(f"❌ 评估失败: {e}")
        return {
            "task": task_name,
            "status": "error",
            "score": 0,
            "error": str(e)
        }
    
    finally:
        # 7. 清理工作区
        if repo_path and not KEEP_WORKSPACE:
            print("\n清理工作区...")
            cleanup_workspace(repo_path.parent)
        elif repo_path:
            print(f"\nℹ️ 保留工作区: {repo_path}")


def save_results(results: List[Dict], output_file: Path = None) -> Dict[str, Any]:
    """
    保存评估结果
    
    Args:
        results: 结果列表
        output_file: 输出文件路径
    
    Returns:
        Dict: 汇总结果
    """
    
    if output_file is None:
        output_file = RESULTS_DIR / "evaluation_results.json"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 计算统计数据
    total_tasks = len(results)
    passed = sum(1 for r in results if r.get("score", 0) == 1)
    failed = sum(1 for r in results if r.get("status") == "failed")
    errors = sum(1 for r in results if r.get("status") == "error")
    missing = sum(1 for r in results if r.get("status") == "missing_patch")
    empty = sum(1 for r in results if r.get("status") == "empty_patch")
    patch_failed = sum(1 for r in results if r.get("status") == "patch_failed")
    task_not_found = sum(1 for r in results if r.get("status") == "task_not_found")
    
    # 按仓库和算子分组统计
    by_repo = {}
    by_operator = {}
    by_target_arch = {}
    by_status = {}
    
    for r in results:
        repo = r.get("repo", "unknown")
        operator = r.get("operator", "unknown")
        target_arch = r.get("target_arch", "unknown")
        status = r.get("status", "unknown")
        score = r.get("score", 0)
        
        by_repo[repo] = by_repo.get(repo, 0) + score
        by_operator[operator] = by_operator.get(operator, 0) + score
        by_target_arch[target_arch] = by_target_arch.get(target_arch, 0) + score
        by_status[status] = by_status.get(status, 0) + 1
    
    summary = {
        "total_tasks": total_tasks,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "missing_patches": missing,
        "empty_patches": empty,
        "patch_failed": patch_failed,
        "task_not_found": task_not_found,
        "score": passed,
        "score_percentage": round(passed / total_tasks * 100, 2) if total_tasks > 0 else 0,
        "by_repo": by_repo,
        "by_operator": by_operator,
        "by_target_arch": by_target_arch,
        "by_status": by_status,
        "results": results
    }
    
    # 保存 JSON
    output_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"\n✅ 结果已保存: {output_file}")
    
    return summary


def print_summary(summary: Dict[str, Any]):
    """打印评估摘要"""
    
    print("\n" + "=" * 80)
    print(f"📊 评估完成!")
    print(f"   总任务: {summary['total_tasks']}")
    print(f"   通过: {summary['passed']}")
    print(f"   失败: {summary['failed']}")
    print(f"   错误: {summary['errors']}")
    print(f"   缺失补丁: {summary['missing_patches']}")
    print(f"   空补丁: {summary['empty_patches']}")
    print(f"   补丁应用失败: {summary['patch_failed']}")
    print(f"   任务不存在: {summary['task_not_found']}")
    print(f"   得分: {summary['score']}/{summary['total_tasks']} ({summary['score_percentage']}%)")
    print("=" * 80)
    
    # 按状态统计
    if summary.get("by_status"):
        print("\n📊 按状态统计:")
        for status, count in sorted(summary["by_status"].items()):
            print(f"   {status}: {count}")
    
    # 按仓库统计
    if summary.get("by_repo"):
        print("\n📦 按仓库统计:")
        for repo, score in sorted(summary["by_repo"].items()):
            print(f"   {repo}: {score}")
    
    # 按算子统计
    if summary.get("by_operator"):
        print("\n🔧 按算子统计:")
        for operator, score in sorted(summary["by_operator"].items()):
            print(f"   {operator}: {score}")
    
    # 按目标架构统计
    if summary.get("by_target_arch"):
        print("\n🏗️ 按目标架构统计:")
        for arch, score in sorted(summary["by_target_arch"].items()):
            print(f"   {arch}: {score}")
    
    # 显示失败的任务
    failed_tasks = [r for r in summary["results"] if r.get("score", 0) == 0]
    if failed_tasks:
        print("\n❌ 失败的任务:")
        for r in failed_tasks:
            status = r.get("status", "unknown")
            error = r.get("error", "")
            task_id = r.get("task_id", r.get("task", "unknown"))
            print(f"   - {task_id}: {status}" + (f" ({error})" if error else ""))


def main():
    """主函数"""
    global PRED_DIR, DOCKER_IMAGE, KEEP_WORKSPACE, RESULTS_DIR
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="评估基准测试结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 评估所有补丁
  python evaluate.py
  
  # 评估特定任务
  python evaluate.py --task opencv_arm_riscv_absdiff
  
  # 列出所有补丁
  python evaluate.py --list
  
  # 保留工作区（调试用）
  python evaluate.py --keep-workspace
  
  # 从 predictions 目录读取（默认行为）
  python evaluate.py --predictions ../my_predictions
        """
    )
    parser.add_argument(
        "--task", "-t",
        help="指定评估的任务名称"
    )
    parser.add_argument(
        "--keep-workspace", "-k",
        action="store_true",
        help="保留工作区（调试用）"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出所有补丁文件"
    )
    parser.add_argument(
        "--predictions", "-p",
        type=Path,
        default=PRED_DIR,
        help=f"补丁目录（默认: {PRED_DIR}）"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="结果输出文件（默认: {RESULTS_DIR}/evaluation_results.json）"
    )
    parser.add_argument(
        "--docker-image", "-d",
        default=DOCKER_IMAGE,
        help=f"Docker 镜像名（默认: {DOCKER_IMAGE}）"
    )
    parser.add_argument(
        "--repo", "-r",
        action="append",
        help="只检索指定仓库名下的任务；可重复使用，也支持逗号分隔"
    )
    
    args = parser.parse_args()
    
    # 设置全局配置
    PRED_DIR = args.predictions
    DOCKER_IMAGE = args.docker_image
    KEEP_WORKSPACE = args.keep_workspace
    if args.output:
        RESULTS_DIR = args.output.parent
    else:
        RESULTS_DIR = Path("../results")
    
    # 确保目录存在
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 列出补丁
    if args.list:
        tasks = get_patch_tasks(PRED_DIR)
        if not tasks:
            print("⚠️ 没有找到补丁文件")
            return
        
        # 检查哪些任务存在
        existence = check_tasks_exist(tasks, repo_names=args.repo)
        
        print(f"Found {len(tasks)} patches:")
        for task in tasks:
            exists = existence.get(task, False)
            status = "✅" if exists else "⚠️ (task not found)"
            print(f"  {task} {status}")
        return
    
    # 获取任务列表（从补丁文件）
    if args.task:
        tasks = [args.task]
    else:
        tasks = get_patch_tasks(PRED_DIR)
    
    if not tasks:
        print("⚠️ 没有找到补丁文件")
        return
    
    # 检查任务是否存在
    existence = check_tasks_exist(tasks, repo_names=args.repo)
    missing_tasks = [t for t, exists in existence.items() if not exists]
    if missing_tasks:
        print(f"⚠️ 以下任务在 tasks 目录中不存在:")
        for task in missing_tasks:
            print(f"   {task}")
        print()
    
    print(f"Found {len(tasks)} tasks from patches")
    print(f"Docker 镜像: {DOCKER_IMAGE}")
    print(f"补丁目录: {PRED_DIR}")
    print(f"结果目录: {RESULTS_DIR}")
    if KEEP_WORKSPACE:
        print("⚠️ 工作区将保留（调试模式）")
    print()
    
    # ===== 新增：清理 bins 目录 =====
    bins_dir = Path("../bins")
    if bins_dir.exists():
        print(f"🧹 清理旧 bin 目录: {bins_dir}")
        shutil.rmtree(bins_dir)
    bins_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 已创建干净的 bins 目录: {bins_dir}")

    # 评估所有任务
    results = []
    for task_name in tasks:
        # 检查任务是否存在
        if not existence.get(task_name, False):
            print(f"\n⚠️ 跳过不存在的任务: {task_name}")
            results.append({
                "task": task_name,
                "status": "task_not_found",
                "score": 0,
                "error": f"Task {task_name} not found in tasks directory"
            })
            continue
        
        result = evaluate_task(task_name)
        
        results.append(result)
        
        # 实时显示进度
        status = result.get("status", "unknown")
        score = result.get("score", 0)
        print(f"  → {task_name}: {status} (score: {score})")
    
    # 保存结果
    output_file = args.output if args.output else RESULTS_DIR / "evaluation_results.json"
    summary = save_results(results, output_file)
    
    # 打印摘要
    print_summary(summary)

if __name__ == "__main__":
    main()
