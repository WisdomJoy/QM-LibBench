from pathlib import Path
import subprocess
from typing import Optional

def export_patch(
    repo_path: Path,
    output_patch: Path,
    commit_id_start: str,
) -> bool:
    """
    导出 Git 补丁
    
    Args:
        repo_path: Git 仓库路径
        output_patch: 输出文件路径
        commit_id_start: 起始 commit ID
    
    Returns:
        bool: 是否成功导出
    """
    
    output_patch.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    
  # 捕获输出，不重定向到文件
    result = subprocess.run(
        ["git", "format-patch", f"{commit_id_start}..HEAD", "--stdout"],
        cwd=repo_path,
        capture_output=True,  # 捕获 stdout 和 stderr
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Git 命令失败: {result.stderr}")
        return False
    
    # 检查是否有变更
    if not result.stdout:
        print("⚠️: 没有变更可导出")
        # 创建空文件或跳过
        output_patch.write_text("", encoding="utf-8")
        return False
    
    # 写入文件
    output_patch.write_text(result.stdout, encoding="utf-8")
    
    print(f"✅ 补丁已导出: {output_patch}")
    print(f"   大小: {len(result.stdout)} 字节 ({len(result.stdout.splitlines())} 行)")
    return True