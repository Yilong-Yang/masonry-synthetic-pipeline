"""Import OBJ groups from subfolders and place each group in its own collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import bpy


@dataclass(frozen=True)
class GroupImportConfig:
    root_directory: Path
    global_scale: float = 0.001
    forward_axis: str = "Y"
    up_axis: str = "Z"
    collection_prefix: str = "Collection_"


def list_subdirectories(root_directory: Path) -> List[Path]:
    return sorted([path for path in root_directory.iterdir() if path.is_dir()])


def list_obj_files(directory: Path) -> List[Path]:
    return sorted([path for path in directory.iterdir() if path.suffix.lower() == ".obj"])


def ensure_scene_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name=name)

    scene_root = bpy.context.scene.collection
    if collection.name not in scene_root.children.keys():
        scene_root.children.link(collection)
    return collection


def _import_with_wm_obj_import(
    directory: Path,
    obj_files: Sequence[Path],
    config: GroupImportConfig,
) -> None:
    bpy.ops.wm.obj_import(
        directory=f"{directory}\\",
        files=[{"name": file_path.name} for file_path in obj_files],
        forward_axis=config.forward_axis,
        up_axis=config.up_axis,
        global_scale=config.global_scale,
    )


def _import_with_legacy_import_scene_obj(
    obj_files: Sequence[Path],
    config: GroupImportConfig,
) -> None:
    for file_path in obj_files:
        bpy.ops.import_scene.obj(
            filepath=str(file_path),
            axis_forward=config.forward_axis,
            axis_up=config.up_axis,
            global_scale=config.global_scale,
        )


def import_obj_files(directory: Path, config: GroupImportConfig) -> List[bpy.types.Object]:
    obj_files = list_obj_files(directory)
    if not obj_files:
        return []

    before = {obj.as_pointer() for obj in bpy.data.objects}
    if hasattr(bpy.ops.wm, "obj_import"):
        _import_with_wm_obj_import(directory, obj_files, config)
    elif hasattr(bpy.ops.import_scene, "obj"):
        _import_with_legacy_import_scene_obj(obj_files, config)
    else:
        raise RuntimeError("No OBJ import operator found in this Blender build.")

    return [obj for obj in bpy.data.objects if obj.as_pointer() not in before]


def move_objects_to_collection(
    objects: Sequence[bpy.types.Object],
    target_collection: bpy.types.Collection,
) -> None:
    for obj in objects:
        if target_collection not in obj.users_collection:
            target_collection.objects.link(obj)

        for source_collection in list(obj.users_collection):
            if source_collection != target_collection:
                source_collection.objects.unlink(obj)


def import_groups(config: GroupImportConfig) -> None:
    root_directory = config.root_directory.expanduser().resolve()
    if not root_directory.exists():
        raise FileNotFoundError(f"Root directory not found: {root_directory}")
    if not root_directory.is_dir():
        raise NotADirectoryError(f"Root path is not a directory: {root_directory}")

    subdirectories = list_subdirectories(root_directory)
    if not subdirectories:
        raise RuntimeError(f"No subdirectories found in: {root_directory}")

    total_imported = 0
    for index, folder in enumerate(subdirectories, start=1):
        collection_name = f"{config.collection_prefix}{index:03d}_{folder.name}"
        target_collection = ensure_scene_collection(collection_name)
        imported_objects = import_obj_files(folder, config)
        move_objects_to_collection(imported_objects, target_collection)
        total_imported += len(imported_objects)
        print(
            f"[INFO] {folder.name}: imported {len(imported_objects)} objects "
            f"into '{target_collection.name}'."
        )

    print(f"[DONE] Imported {total_imported} objects from {len(subdirectories)} groups.")


def main() -> None:
    config = GroupImportConfig(
        root_directory=Path(r"C:\path\to\obj_root_directory"),
        global_scale=0.001,
        forward_axis="Y",
        up_axis="Z",
        collection_prefix="Collection_",
    )
    import_groups(config)


if __name__ == "__main__":
    main()
