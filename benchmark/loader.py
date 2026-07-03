# benchmark/loader.py

from dataclasses import dataclass
from pathlib import Path
import json
from typing import List, Optional, Sequence, Tuple


@dataclass
class Task:
    name: str
    repo: str
    source_arch: str
    target_arch: str
    operator: str
    prompt: str
    metadata: dict
    overlay_dir: Path
    
    @property
    def task_id(self) -> str:
        """生成任务唯一标识"""
        return f"{self.repo}_{self.source_arch}_{self.target_arch}_{self.operator}"
    
    @property
    def task_dir(self) -> Path:
        """任务目录路径"""
        return Path(f"../tasks/{self.repo}/{self.target_arch}/{self.operator}")


def parse_task_name(task_name: str) -> Tuple[str, str, str, str]:
    """
    解析任务名称，提取各组成部分
    
    Args:
        task_name: 任务名称，格式为 {repo}_{source_arch}_{target_arch}_{operator}
                  例如: opencv_arm_riscv_absdiff
    
    Returns:
        Tuple[str, str, str, str]: (repo, source_arch, target_arch, operator)
    
    Raises:
        ValueError: 任务名格式不正确
    """
    parts = task_name.split('_')
    
    if len(parts) < 4:
        raise ValueError(
            f"任务名格式错误: {task_name}\n"
            f"期望格式: {{repo}}_{{source_arch}}_{{target_arch}}_{{operator}}\n"
            f"例如: opencv_arm_riscv_absdiff"
        )
    
    # 最后一个部分是算子名称
    operator = parts[-1]
    # 倒数第二个是目标架构
    target_arch = parts[-2]
    # 其余部分是仓库名和源架构（如果仓库名包含下划线，需要特殊处理）
    # 假设仓库名可能有下划线，比如 "my_repo"
    
    # 方式1：简单分割（适用于仓库名不包含下划线）
    repo = parts[0]
    source_arch = parts[1]
    
    # 方式2：更智能的分割（如果仓库名包含下划线）
    # 例如: opencv_contrib_arm_riscv_absdiff
    # 我们需要找出 source_arch 和 target_arch
    # 假设架构名是已知的：arm, riscv, x86, rvv, etc.
    known_archs = {'arm', 'riscv', 'x86', 'rvv', 'aarch64', 'x86_64'}
    
    # 尝试找出架构名
    # 从后往前找，倒数第二是 target_arch
    target_arch = parts[-2]
    
    # 往前找 source_arch（它应该在 target_arch 前面）
    # 简单方式：取第二个部分作为 source_arch
    # 但如果仓库名包含下划线，需要更智能的处理
    source_arch = parts[-3]  # 倒数第三个
    
    # 仓库名是剩余的部分
    repo = '_'.join(parts[:-3]) if len(parts) > 4 else parts[0]
    
    # 如果仓库名没有被正确识别（可能太短），调整逻辑
    if not repo or repo == source_arch:
        # 使用更简单的方式
        if len(parts) >= 4:
            # 假设格式为: repo_sourceArch_targetArch_operator
            # 但用下划线分割可能有歧义
            # 更稳健的方式：使用已知的架构列表
            for i, part in enumerate(parts):
                if part in known_archs:
                    # 找到第一个架构名作为 source_arch
                    if source_arch == parts[-3]:  # 如果还没设置
                        source_arch = part
                        repo = '_'.join(parts[:i])
                        break
    
    # 如果仍然有问题，使用 fallback
    if not repo or repo == source_arch:
        # Fallback: 假设格式就是简单的 repo_arch_arch_operator
        repo = parts[0]
        source_arch = parts[1] if len(parts) > 1 else "unknown"
        target_arch = parts[2] if len(parts) > 2 else "unknown"
        operator = parts[3] if len(parts) > 3 else "unknown"
    
    return repo, source_arch, target_arch, operator


def read_task_from_dir(task_name: str, task_dir: Path) -> Task:
    prompt_file = task_dir / "prompt.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"prompt.txt 不存在: {prompt_file}")
    
    metadata_file = task_dir / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"metadata.json 不存在: {metadata_file}")
    
    prompt = prompt_file.read_text(encoding="utf-8")
    
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"metadata.json 格式错误: {e}")
    
    return Task(
        name=task_name,
        repo=metadata.get("repo", "unknown"),
        source_arch=metadata.get("source_arch", "unknown"),
        target_arch=metadata.get("target_arch", "unknown"),
        operator=metadata.get("name", task_dir.name),
        prompt=prompt,
        metadata=metadata,
        overlay_dir=task_dir / "overlay"
    )


def find_task_dir_by_name(task_name: str, tasks_root: Path) -> Optional[Path]:
    for repo_dir in tasks_root.iterdir():
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        
        for first_level_dir in repo_dir.iterdir():
            if not first_level_dir.is_dir() or first_level_dir.name.startswith("."):
                continue
            
            candidate_dirs = []
            if (first_level_dir / "prompt.txt").exists() and (first_level_dir / "metadata.json").exists():
                candidate_dirs.append(first_level_dir)
            else:
                for operator_dir in first_level_dir.iterdir():
                    if operator_dir.is_dir() and not operator_dir.name.startswith("."):
                        candidate_dirs.append(operator_dir)
            
            for candidate_dir in candidate_dirs:
                metadata_file = candidate_dir / "metadata.json"
                prompt_file = candidate_dir / "prompt.txt"
                if not metadata_file.exists() or not prompt_file.exists():
                    continue
                
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                
                repo = metadata.get("repo", repo_dir.name)
                source_arch = metadata.get("source_arch", "unknown")
                target_arch = metadata.get("target_arch", "unknown")
                operator = metadata.get("name", candidate_dir.name)
                candidate_task_name = f"{repo}_{source_arch}_{target_arch}_{operator}"
                
                if candidate_task_name == task_name:
                    return candidate_dir
    
    return None


def load_task(task_name: str, tasks_root: Path = None) -> Task:
    """
    加载任务配置
    
    Args:
        task_name: 任务名称，格式为 {repo}_{source_arch}_{target_arch}_{operator}
                  例如: opencv_arm_riscv_absdiff
        tasks_root: 任务根目录（默认 ../tasks）
    
    Returns:
        Task: 任务对象
    
    Raises:
        FileNotFoundError: 任务目录或文件不存在
        json.JSONDecodeError: metadata.json 格式错误
        ValueError: 任务名格式不正确
    """
    if tasks_root is None:
        tasks_root = Path("../tasks")
    
    # 1. 优先用 metadata 反查任务目录，支持算子名中包含下划线的任务。
    task_dir = find_task_dir_by_name(task_name, tasks_root)
    if task_dir:
        return read_task_from_dir(task_name, task_dir)
    
    # 2. 解析任务名
    repo, source_arch, target_arch, operator = parse_task_name(task_name)
    
    # 3. 构建任务目录路径
    task_dir = tasks_root / repo / target_arch / operator
    
    if not task_dir.exists():
        repo_dir = tasks_root / repo
        if repo_dir.exists():
            for candidate_dir in repo_dir.iterdir():
                if not candidate_dir.is_dir() or candidate_dir.name.startswith("."):
                    continue
                
                metadata_file = candidate_dir / "metadata.json"
                prompt_file = candidate_dir / "prompt.txt"
                if not metadata_file.exists() or not prompt_file.exists():
                    continue
                
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                
                candidate_source_arch = metadata.get("source_arch", "unknown")
                candidate_target_arch = metadata.get("target_arch", "unknown")
                candidate_operator = metadata.get("name", candidate_dir.name)
                candidate_task_name = (
                    f"{repo}_{candidate_source_arch}_{candidate_target_arch}_{candidate_operator}"
                )
                
                if candidate_task_name == task_name:
                    task_dir = candidate_dir
                    source_arch = candidate_source_arch
                    target_arch = candidate_target_arch
                    operator = candidate_operator
                    break
    
    if not task_dir.exists():
        raise FileNotFoundError(
            f"任务目录不存在: {task_dir}\n"
            f"期望路径: ../tasks/{repo}/{target_arch}/{operator}"
        )
    
    return read_task_from_dir(task_name, task_dir)


def normalize_repo_names(repo_names: Optional[Sequence[str] | str]) -> Optional[List[str]]:
    """Normalize repeated and comma-separated repo filters."""
    
    if repo_names is None:
        return None
    
    if isinstance(repo_names, str):
        raw_names = [repo_names]
    else:
        raw_names = list(repo_names)
    
    names = []
    seen = set()
    for raw_name in raw_names:
        for name in raw_name.split(","):
            name = name.strip()
            if name and name not in seen:
                names.append(name)
                seen.add(name)
    
    return names or None


def list_tasks(
    tasks_root: Path = None,
    repo_name: Optional[str] = None,
    repo_names: Optional[Sequence[str] | str] = None
) -> List[str]:
    """
    列出所有任务
    
    Args:
        tasks_root: 任务根目录（默认 ../tasks）
        repo_name: 仓库名；指定后只列出该仓库下的三层目录任务
        repo_names: 一个或多个仓库名；支持列表、重复参数值和逗号分隔值
    
    Returns:
        List[str]: 排序后的任务名列表
    """
    
    if tasks_root is None:
        tasks_root = Path("../tasks")
    
    if not tasks_root.exists():
        print(f"⚠️ 任务目录不存在: {tasks_root}")
        return []
    
    tasks = []
    
    selected_repos = normalize_repo_names(repo_names if repo_names is not None else repo_name)
    
    if selected_repos:
        repo_dirs = [tasks_root / name for name in selected_repos]
    else:
        repo_dirs = [p for p in tasks_root.iterdir()]
    
    # 遍历 tasks/{repo}/{target_arch}/{operator}，同时兼容 tasks/{repo}/{operator}
    for repo_dir in repo_dirs:
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        
        for first_level_dir in repo_dir.iterdir():
            if not first_level_dir.is_dir() or first_level_dir.name.startswith("."):
                continue
            
            candidate_dirs = []
            if (first_level_dir / "prompt.txt").exists() and (first_level_dir / "metadata.json").exists():
                candidate_dirs.append(first_level_dir)
            else:
                for operator_dir in first_level_dir.iterdir():
                    if not operator_dir.is_dir() or operator_dir.name.startswith("."):
                        continue
                    candidate_dirs.append(operator_dir)
            
            for operator_dir in candidate_dirs:
                prompt_file = operator_dir / "prompt.txt"
                metadata_file = operator_dir / "metadata.json"
                if not prompt_file.exists() or not metadata_file.exists():
                    continue
                
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                    source_arch = metadata.get("source_arch", "unknown")
                    target_arch = metadata.get("target_arch", "unknown")
                    operator = metadata.get("name", operator_dir.name)
                except:
                    source_arch = "unknown"
                    target_arch = "unknown"
                    operator = operator_dir.name
                
                task_name = f"{repo_dir.name}_{source_arch}_{target_arch}_{operator}"
                tasks.append(task_name)
    
    return sorted(tasks)


def list_tasks_by_repo(repo_name: str, tasks_root: Path = None) -> List[str]:
    """
    列出指定仓库的所有任务
    
    Args:
        repo_name: 仓库名
        tasks_root: 任务根目录（默认 ../tasks）
    
    Returns:
        List[str]: 任务名列表
    """
    
    return list_tasks(tasks_root=tasks_root, repo_names=[repo_name])
