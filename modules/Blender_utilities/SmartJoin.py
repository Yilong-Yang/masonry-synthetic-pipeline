"""Merge two collections and rebuild Subsurf/Displace modifiers on the result.

Workflow:
1. Read Subsurf + Displace settings from one representative object in each group.
2. Ensure each object has a full-coverage vertex group and a predictable UV map name.
3. Join all mesh objects from both collections.
4. Recreate one shared Subsurf and two Displace modifiers on the merged object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Set, Tuple

import bpy


@dataclass(frozen=True)
class MergeConfig:
    collection_a_name: str = "Collection1"
    collection_b_name: str = "Collection2"
    vertex_group_a: str = "A_All"
    vertex_group_b: str = "B_All"
    uv_map_a: str = "UV_A"
    uv_map_b: str = "UV_B"


@dataclass(frozen=True)
class SubsurfParams:
    subdivision_type: str
    levels_view: int
    levels_render: int


@dataclass(frozen=True)
class DisplaceParams:
    texture: bpy.types.Texture | None
    strength: float
    mid_level: float
    direction: str
    space: str
    texture_coords: str


@dataclass(frozen=True)
class ModifierTemplate:
    subsurf: SubsurfParams
    displace: DisplaceParams


def get_collection_or_raise(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        raise RuntimeError(f'Collection "{name}" not found.')
    return collection


def _collect_mesh_objects_recursive(
    collection: bpy.types.Collection,
    seen: Set[int],
    output: List[bpy.types.Object],
) -> None:
    for obj in collection.objects:
        pointer = obj.as_pointer()
        if obj.type == "MESH" and pointer not in seen:
            output.append(obj)
            seen.add(pointer)

    for child in collection.children:
        _collect_mesh_objects_recursive(child, seen, output)


def mesh_objects_in_collection(collection: bpy.types.Collection) -> List[bpy.types.Object]:
    output: List[bpy.types.Object] = []
    _collect_mesh_objects_recursive(collection, seen=set(), output=output)
    return output


def find_subsurf_and_displace(
    obj: bpy.types.Object,
) -> Tuple[bpy.types.SubsurfModifier | None, bpy.types.DisplaceModifier | None]:
    subsurf: bpy.types.SubsurfModifier | None = None
    displace: bpy.types.DisplaceModifier | None = None

    for modifier in obj.modifiers:
        if modifier.type == "SUBSURF" and subsurf is None:
            subsurf = modifier  # type: ignore[assignment]
        elif modifier.type == "DISPLACE" and displace is None:
            displace = modifier  # type: ignore[assignment]

    return subsurf, displace


def capture_template(objects: Sequence[bpy.types.Object], label: str) -> ModifierTemplate:
    for obj in objects:
        subsurf, displace = find_subsurf_and_displace(obj)
        if subsurf is None or displace is None:
            continue

        return ModifierTemplate(
            subsurf=SubsurfParams(
                subdivision_type=getattr(subsurf, "subdivision_type", "CATMULL_CLARK"),
                levels_view=getattr(subsurf, "levels", 1),
                levels_render=getattr(subsurf, "render_levels", getattr(subsurf, "levels", 1)),
            ),
            displace=DisplaceParams(
                texture=displace.texture,
                strength=displace.strength,
                mid_level=displace.mid_level,
                direction=displace.direction,
                space=displace.space,
                texture_coords=displace.texture_coords,
            ),
        )

    raise RuntimeError(
        f'No object with both Subsurf and Displace modifiers found in "{label}".'
    )


def ensure_full_vertex_group(obj: bpy.types.Object, group_name: str) -> None:
    group = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)
    vertex_indices = [vertex.index for vertex in obj.data.vertices]
    if vertex_indices:
        group.add(vertex_indices, 1.0, "REPLACE")


def ensure_primary_uv_name(obj: bpy.types.Object, uv_name: str) -> None:
    uv_layers = obj.data.uv_layers
    if not uv_layers:
        uv_layers.new(name=uv_name)
        return
    uv_layers[0].name = uv_name


def prepare_group(
    objects: Sequence[bpy.types.Object],
    vertex_group: str,
    uv_name: str,
) -> None:
    for obj in objects:
        ensure_full_vertex_group(obj, vertex_group)
        ensure_primary_uv_name(obj, uv_name)


def select_for_join(objects: Sequence[bpy.types.Object], active_obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active_obj


def remove_modifiers_by_type(obj: bpy.types.Object, modifier_types: Set[str]) -> None:
    for modifier in list(obj.modifiers):
        if modifier.type in modifier_types:
            obj.modifiers.remove(modifier)


def add_subsurf_modifier(obj: bpy.types.Object, params: SubsurfParams) -> None:
    modifier = obj.modifiers.new(name="Subsurf", type="SUBSURF")
    modifier.subdivision_type = params.subdivision_type
    modifier.levels = params.levels_view
    modifier.render_levels = params.levels_render


def add_displace_modifier(
    obj: bpy.types.Object,
    name: str,
    params: DisplaceParams,
    vertex_group: str,
    uv_name: str,
) -> None:
    modifier = obj.modifiers.new(name=name, type="DISPLACE")
    modifier.texture = params.texture
    modifier.strength = params.strength
    modifier.mid_level = params.mid_level
    modifier.direction = params.direction
    modifier.space = params.space
    modifier.texture_coords = params.texture_coords
    modifier.vertex_group = vertex_group
    if modifier.texture_coords == "UV":
        modifier.uv_layer = uv_name


def merge_collections(config: MergeConfig) -> bpy.types.Object:
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")

    collection_a = get_collection_or_raise(config.collection_a_name)
    collection_b = get_collection_or_raise(config.collection_b_name)

    objects_a = mesh_objects_in_collection(collection_a)
    objects_b = mesh_objects_in_collection(collection_b)

    if not objects_a:
        raise RuntimeError(f'No mesh objects in "{config.collection_a_name}".')
    if not objects_b:
        raise RuntimeError(f'No mesh objects in "{config.collection_b_name}".')

    template_a = capture_template(objects_a, config.collection_a_name)
    template_b = capture_template(objects_b, config.collection_b_name)

    prepare_group(objects_a, config.vertex_group_a, config.uv_map_a)
    prepare_group(objects_b, config.vertex_group_b, config.uv_map_b)

    active_obj = (
        objects_a[0]
        if template_a.subsurf.levels_view >= template_b.subsurf.levels_view
        else objects_b[0]
    )
    all_objects = [obj for obj in [*objects_a, *objects_b] if obj.type == "MESH"]
    if not all_objects:
        raise RuntimeError("Nothing to join.")

    select_for_join(all_objects, active_obj)
    bpy.ops.object.join()

    merged = bpy.context.view_layer.objects.active
    if merged is None or merged.type != "MESH":
        raise RuntimeError("Join failed or active object is not a mesh.")

    remove_modifiers_by_type(merged, {"SUBSURF", "DISPLACE"})

    top_template = (
        template_a if template_a.subsurf.levels_view >= template_b.subsurf.levels_view else template_b
    )
    max_subsurf = SubsurfParams(
        subdivision_type=top_template.subsurf.subdivision_type,
        levels_view=max(template_a.subsurf.levels_view, template_b.subsurf.levels_view),
        levels_render=max(template_a.subsurf.levels_render, template_b.subsurf.levels_render),
    )
    add_subsurf_modifier(merged, max_subsurf)
    add_displace_modifier(
        merged,
        name="Displace_A",
        params=template_a.displace,
        vertex_group=config.vertex_group_a,
        uv_name=config.uv_map_a,
    )
    add_displace_modifier(
        merged,
        name="Displace_B",
        params=template_b.displace,
        vertex_group=config.vertex_group_b,
        uv_name=config.uv_map_b,
    )

    print(
        f"[DONE] Merged {len(all_objects)} objects into '{merged.name}'. "
        f"Subsurf levels: view={max_subsurf.levels_view}, render={max_subsurf.levels_render}."
    )
    return merged


def main() -> None:
    config = MergeConfig(
        collection_a_name="Collection1",
        collection_b_name="Collection2",
        vertex_group_a="A_All",
        vertex_group_b="B_All",
        uv_map_a="UV_A",
        uv_map_b="UV_B",
    )
    merge_collections(config)


if __name__ == "__main__":
    main()
