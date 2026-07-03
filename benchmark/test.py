# benchmark/prepare.py

import shutil
from pathlib import Path


def prepare_repo():
    base_repo = Path("a/opencv")

    workspace = Path("workspace/task/opencv")
    
    if workspace.exists():
        shutil.rmtree(workspace)

    shutil.copytree(
        base_repo,
        workspace
    )

    return workspace

def main():
    prepare_repo()
    
if __name__ == "__main__":
    main()