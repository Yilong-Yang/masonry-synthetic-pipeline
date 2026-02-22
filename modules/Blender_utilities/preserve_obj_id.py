"""Assign an integer mesh attribute from trailing digits in object names.

Example:
- ``Wall_015`` -> ``category_id = 15`` assigned to every face in that object.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Pattern, Tuple

import bpy


@dataclass(frozen=True)
class CategoryIdConfig:
    attribute_name: str = "category_id"
    id_pattern: str = r"(\d+)$"
    selected_objects_only: bool = False


def ensure_face_int_attribute(
    mesh: bpy.types.Mesh,
    attribute_name: str,
) -> bpy.types.Attribute:
    attribute = mesh.attributes.get(attribute_name)
    if attribute is None:
        return mesh.attributes.new(name=attribute_name, type="INT", domain="FACE")

    if attribute.domain != "FACE" or attribute.data_type != "INT":
        raise TypeError(
            f'Attribute "{attribute_name}" exists on mesh "{mesh.name}" '
            f"but is not INT/FACE."
        )
    return attribute


def assign_category_id_for_object(
    obj: bpy.types.Object,
    pattern: Pattern[str],
    attribute_name: str,
) -> bool:
    match = pattern.search(obj.name)
    if match is None:
        print(f"[WARN] No trailing id in '{obj.name}'. Skipping.")
        return False

    category_id = int(match.group(1))
    mesh = obj.data
    attribute = ensure_face_int_attribute(mesh, attribute_name)

    for polygon in mesh.polygons:
        attribute.data[polygon.index].value = category_id

    print(f"[INFO] {obj.name}: {attribute_name}={category_id}")
    return True


def iter_target_meshes(selected_objects_only: bool) -> Iterable[bpy.types.Object]:
    candidates = (
        bpy.context.selected_objects if selected_objects_only else bpy.context.scene.objects
    )
    return [obj for obj in candidates if obj.type == "MESH"]


def assign_category_ids(config: CategoryIdConfig) -> Tuple[int, int]:
    pattern = re.compile(config.id_pattern)
    updated_count = 0
    skipped_count = 0

    for obj in iter_target_meshes(config.selected_objects_only):
        if assign_category_id_for_object(obj, pattern, config.attribute_name):
            updated_count += 1
        else:
            skipped_count += 1

    print(f"[DONE] Updated {updated_count} mesh objects, skipped {skipped_count}.")
    return updated_count, skipped_count


def main() -> None:
    config = CategoryIdConfig(
        attribute_name="category_id",
        id_pattern=r"(\d+)$",
        selected_objects_only=False,
    )
    assign_category_ids(config)


if __name__ == "__main__":
    main()
