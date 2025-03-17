import bpy
import json
import mathutils
from mathutils import Euler
import math
import os
import concurrent.futures

base_dir = "E:\\Desktop\\Assets" # Your resource path
if not base_dir.endswith('\\'):
    base_dir += '\\'

# Level JSON file (UMAP) path
map_json = [
    'example_1.json',
    'example_2.json',
]

# Import settings
import_static = True
import_lights = False  # import lights

# Supported types
static_mesh_types = ['StaticMeshComponent']
light_types = ['SpotLightComponent', 'AnimatedLightComponent', 'PointLightComponent']


def split_object_path(object_path):
    path_parts = object_path.split(".")
    return path_parts[0] if len(path_parts) > 1 else object_path


class StaticMesh:
    def __init__(self, json_entity, base_dir):
        self.entity_name = json_entity.get("Outer", 'Error')
        self.import_path = ""
        self.pos = [0, 0, 0]
        self.rot = [0, 0, 0]
        self.scale = [1, 1, 1]  # **Ensure the default scale exists.**

        props = json_entity.get("Properties", None)
        if not props or not props.get("StaticMesh"):
            self.invalid = True
            return
        
        object_path = props.get("StaticMesh").get("ObjectPath", None)
        if not object_path or 'BasicShapes' in object_path:
            self.invalid = True
            return

        objpath = split_object_path(object_path)
        self.import_path = base_dir + objpath.replace('/', '\\') + ".gltf"
        self.invalid = not os.path.exists(self.import_path)

        if props.get("RelativeLocation"):
            pos = props["RelativeLocation"]
            self.pos = [pos["X"] / 100, pos["Y"] / -100, pos["Z"] / 100]
        
        if props.get("RelativeRotation"):
            rot = props["RelativeRotation"]
            self.rot = [rot["Roll"], rot["Pitch"] * -1, rot["Yaw"] * -1]
        
        if props.get("RelativeScale3D"):
            scale = props["RelativeScale3D"]
            self.scale = [scale.get("X", 1), scale.get("Y", 1), scale.get("Z", 1)]
    
    def import_staticmesh(self, collection):
        """Asynchronous meshes import."""
        if self.invalid:
            return
        def import_task():
            try:
                bpy.ops.import_scene.gltf(filepath=self.import_path)
                imported_obj = bpy.context.object
                if imported_obj is None:
                    print(f"Object not found.: {self.entity_name}")
                    return
                
                imported_obj.name = self.entity_name
                imported_obj.scale = self.scale
                imported_obj.location = self.pos
                imported_obj.rotation_mode = 'XYZ'
                imported_obj.rotation_euler = Euler(
                    (math.radians(self.rot[0]), math.radians(self.rot[1]), math.radians(self.rot[2])), 'XYZ'
                )
                collection.objects.link(imported_obj)
                bpy.context.scene.collection.objects.unlink(imported_obj)
                print(f"Import successful: {self.entity_name}")
            except Exception as e:
                print(f"Import failed: {self.entity_name}: {e}")
        
        pending_tasks.append(import_task)


def process_json_file(map_file):   
    if not os.path.exists(map_file):
        print(f"File not found, skipping.: {map_file}")
        return
    
    json_filename = os.path.basename(map_file)
    import_collection = bpy.data.collections.new(json_filename)
    bpy.context.scene.collection.children.link(import_collection)

    with open(map_file) as file:
        json_object = json.load(file)

        for entity in json_object:
            if entity.get('Type') in static_mesh_types:
                static_mesh = StaticMesh(entity, base_dir)
                if not static_mesh.invalid:
                    static_mesh.import_staticmesh(import_collection)

# **Scheduled task, load objects step by step every 0.01 seconds.**
def incremental_load():
    global pending_tasks
    if pending_tasks:
        task = pending_tasks.pop(0)
        task() 
        return 0.01
    return None

pending_tasks = []
for map_file in map_json:
    process_json_file(map_file)

bpy.app.timers.register(incremental_load)
print("Dynamic import task has started.")
