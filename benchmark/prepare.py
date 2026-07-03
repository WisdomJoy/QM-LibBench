# benchmark/prepare.py

import shutil
import subprocess
from pathlib import Path
from typing import Tuple
from loader import Task
from repo_config import get_repo_config


def replace_overlay_path(source: Path, target: Path):
    """完整替换 overlay 目标路径，支持目录和单文件。"""
    
    if not source.exists():
        print(f"⚠️ 覆盖层路径不存在: {source}")
        return
    
    print(f"应用覆盖层: {source} -> {target}")
    
    if target.exists() or target.is_symlink():
        print(f"完整替换覆盖层目标路径: {target}")
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    
    target.parent.mkdir(parents=True, exist_ok=True)
    
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def prepare_workspace(
    task: Task,
    base_repo: Path = None,
    workspace_root: Path = None
) -> Tuple[Path, str]:
    """
    准备任务工作区
    
    Args:
        task: 任务对象
        base_repo: 基础仓库路径（默认 ../repo/{task.repo}）
        workspace_root: 工作区根目录（默认 ../workspace）
    
    Returns:
        Tuple[Path, str]: (工作区路径, 基准 commit ID)
    """
    
    if base_repo is None:
        base_repo = Path(f"../repo/{task.repo}")
    
    if workspace_root is None:
        workspace_root = Path("../workspace")
    
    repo_config = get_repo_config(task.repo)
    
    # 生成工作区路径: workspace/{repo}_{source_arch}_{target_arch}_{operator}/{repo}
    workspace = workspace_root / task.task_id / task.repo
    
    # 清理旧工作区
    if workspace.exists():
        print(f"清理旧工作区: {workspace}")
        shutil.rmtree(workspace)
    
    # 复制基础仓库
    print(f"复制基础仓库: {base_repo} -> {workspace}")
    shutil.copytree(base_repo, workspace)
    
    # 应用覆盖层
    for overlay_source, overlay_target in repo_config.overlay_pairs(workspace, task):
        replace_overlay_path(overlay_source, overlay_target)
    
    # 初始化 Git 仓库
    commit_id_start = init_git_baseline(workspace)
    
    return workspace, commit_id_start


def init_git_baseline(
    repo_path: Path,
    author_name: str = "benchmark",
    author_email: str = "benchmark@example.com"
) -> str:
    """
    初始化 Git 仓库并创建基准提交
    
    Args:
        repo_path: 仓库路径
        author_name: 作者名
        author_email: 作者邮箱
    
    Returns:
        str: 基准提交的 commit ID
    """
    
    # 初始化
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    
    # 添加所有文件
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    
    # 提交
    subprocess.run(
        [
            "git",
            "-c", f"user.name={author_name}",
            "-c", f"user.email={author_email}",
            "commit",
            "-m",
            "benchmark_start"
        ],
        cwd=repo_path,
        check=True
    )
    
    # 获取 commit ID
    commit_id_start = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        text=True
    ).strip()
    
    print(f"✅ 基准提交: {commit_id_start[:8]}")
    
    return commit_id_start


def cleanup_workspace(workspace: Path):
    """清理工作区"""
    if workspace.exists():
        print(f"清理工作区: {workspace}")
        shutil.rmtree(workspace)
