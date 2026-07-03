from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RepoConfig:
    name: str
    mount_path: str
    entrypoint: str
    entrypoints_by_arch: Optional[Dict[str, str]]
    overlay_subdir: Optional[str]
    overlay_target_template: Optional[str]
    overlay_mappings: Optional[Tuple[Tuple[str, str], ...]]
    build_bin_dir: Path

    def entrypoint_for(self, task) -> str:
        if not self.entrypoints_by_arch:
            return self.entrypoint
        
        try:
            return self.entrypoints_by_arch[task.target_arch]
        except KeyError as exc:
            supported = ", ".join(sorted(self.entrypoints_by_arch))
            raise ValueError(
                f"{self.name} 不支持目标架构 {task.target_arch} 的 Docker 入口脚本. "
                f"当前支持: {supported}"
            ) from exc

    def overlay_source(self, task) -> Optional[Path]:
        if not self.overlay_subdir:
            return None
        return task.overlay_dir / self.overlay_subdir.format(
            target_arch=task.target_arch,
            source_arch=task.source_arch,
            operator=task.operator,
        )

    def overlay_target(self, workspace: Path, task) -> Optional[Path]:
        if not self.overlay_target_template:
            return None
        return workspace / self.overlay_target_template.format(
            target_arch=task.target_arch,
            source_arch=task.source_arch,
            operator=task.operator,
        )

    def overlay_pairs(self, workspace: Path, task) -> Tuple[Tuple[Path, Path], ...]:
        if self.overlay_mappings:
            return tuple(
                (
                    task.overlay_dir / source.format(
                        target_arch=task.target_arch,
                        source_arch=task.source_arch,
                        operator=task.operator,
                    ),
                    workspace / target.format(
                        target_arch=task.target_arch,
                        source_arch=task.source_arch,
                        operator=task.operator,
                    ),
                )
                for source, target in self.overlay_mappings
            )
        
        overlay_source = self.overlay_source(task)
        overlay_target = self.overlay_target(workspace, task)
        if overlay_source and overlay_target:
            return ((overlay_source, overlay_target),)
        return tuple()


REPO_CONFIGS = {
    "opencv": RepoConfig(
        name="opencv",
        mount_path="/opencv",
        entrypoint="/opencv_run.sh",
        entrypoints_by_arch=None,
        overlay_subdir="riscv-rvv",
        overlay_target_template="hal/riscv-rvv",
        overlay_mappings=None,
        build_bin_dir=Path("build/bin"),
    ),
    "ncnn": RepoConfig(
        name="ncnn",
        mount_path="/ncnn",
        entrypoint="/ncnn_riscv_run.sh",
        entrypoints_by_arch={
            "arm": "/ncnn_arm_run.sh",
            "loongarch": "/ncnn_loongarch_run.sh",
            "riscv": "/ncnn_riscv_run.sh",
        },
        overlay_subdir="{target_arch}",
        overlay_target_template="src/layer/{target_arch}",
        overlay_mappings=None,
        build_bin_dir=Path("build/tests"),
    ),
    "libjpeg": RepoConfig(
        name="libjpeg",
        mount_path="/libjpeg",
        entrypoint="/libjpeg_run.sh",
        entrypoints_by_arch=None,
        overlay_subdir=None,
        overlay_target_template=None,
        overlay_mappings=(
            ("rvv", "simd/rvv"),
            ("jsimd.c", "simd/jsimd.c"),
            ("jsimd.h", "simd/jsimd.h"),
        ),
        build_bin_dir=Path("build"),
    ),
}


def get_repo_config(repo_name: str) -> RepoConfig:
    try:
        return REPO_CONFIGS[repo_name]
    except KeyError as exc:
        supported = ", ".join(sorted(REPO_CONFIGS))
        raise ValueError(f"不支持的仓库: {repo_name}. 当前支持: {supported}") from exc
