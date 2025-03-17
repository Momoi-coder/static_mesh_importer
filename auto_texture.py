import bpy
import os

def dedup_materials(material_name_to_replace, replacement_material_name):
    # Get the material to use as replacement
    replacement_material = bpy.data.materials.get(replacement_material_name)
    if not replacement_material:
        print(f"Error: Material '{replacement_material_name}' not found.")
        return

    # Iterate over all objects and replace materials
    for obj in bpy.context.scene.objects:
        for i, slot in enumerate(obj.material_slots):
            if slot.material and slot.material.name == material_name_to_replace:
                slot.material = replacement_material
                print(f"Replaced material in object '{obj.name}', slot {i}.")

def search_directory(root_dir, file_name):
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            if file == file_name:
                file_path = os.path.join(subdir, file)
                return file_path
    return None

mat_dir = "E:\\Desktop\\Assets\\"  # Set your material directory

materials = bpy.data.materials

for material in materials:
    if 'WorldGridMaterial' in material.name:
        bpy.data.materials.remove(material, do_unlink=True)
        continue
    
    # Disable Backface Culling
    material.use_backface_culling = False

    mat_name = material.name
    split_matname = mat_name.split('.')
    
    # Deduplicate material
    if len(split_matname) > 1:
        dedup_materials(material.name, split_matname[0])
        bpy.data.materials.remove(material, do_unlink=True)
        continue

    mat_name = split_matname[0]

    # Find .mat file
    found_file = search_directory(mat_dir, mat_name + '.mat')
    if not found_file:
        print(f'No material found for {mat_name}.')
        continue
    
    # Read .mat file to extract textures
    diffuse_texturename = ''
    normal_texturename = ''
    with open(found_file) as mat_file:
        lines = mat_file.readlines()
        for line in lines:
            if line.startswith('Diffuse') or line.startswith('Normal'):
                splitline = line.split("=")
                if len(splitline) > 1:
                    if splitline[0] == 'Diffuse':
                        diffuse_texturename = splitline[1].strip()
                    if splitline[0] == 'Normal':
                        normal_texturename = splitline[1].strip()

    if not diffuse_texturename and not normal_texturename:
        print(f'No textures found for material: {material.name}. Skipping.')
        continue

    diffuse_texture_path = None
    normal_texture_path = None
    if diffuse_texturename:
        diffuse_texture_path = search_directory(mat_dir, diffuse_texturename + '.tga')
    if normal_texturename:
        normal_texture_path = search_directory(mat_dir, normal_texturename + '.tga')

    # Create new Principled BSDF node
    shader_node = material.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")

    # Apply diffuse texture or default color
    if diffuse_texture_path and os.path.exists(diffuse_texture_path):
        diffuse_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
        diffuse_texture.image = bpy.data.images.load(diffuse_texture_path)
        material.node_tree.links.new(shader_node.inputs["Base Color"], diffuse_texture.outputs["Color"])
    else:
        # Default color if no diffuse texture
        shader_node.inputs["Base Color"].default_value = (1, 0, 0, 1)  # Red color (RGBA)

    # Apply normal map if found
    if normal_texture_path and os.path.exists(normal_texture_path):
        normal_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
        normal_texture.image = bpy.data.images.load(normal_texture_path)
        normal_map_node = material.node_tree.nodes.new(type="ShaderNodeNormalMap")
        normal_map_node.inputs["Strength"].default_value = 1.0
        material.node_tree.links.new(shader_node.inputs["Normal"], normal_map_node.outputs["Normal"])

        # Invert the green channel of the normal map
        separate_color = material.node_tree.nodes.new(type="ShaderNodeSeparateColor")
        invert_node = material.node_tree.nodes.new(type="ShaderNodeInvert")
        combine_color = material.node_tree.nodes.new(type="ShaderNodeCombineColor")

        material.node_tree.links.new(combine_color.inputs["Red"], separate_color.outputs["Red"])
        material.node_tree.links.new(combine_color.inputs["Blue"], separate_color.outputs["Blue"])
        material.node_tree.links.new(invert_node.inputs["Color"], separate_color.outputs["Green"])
        material.node_tree.links.new(combine_color.inputs["Green"], invert_node.outputs["Color"])

        material.node_tree.links.new(separate_color.inputs["Color"], normal_texture.outputs["Color"])
        material.node_tree.links.new(normal_map_node.inputs["Color"], combine_color.outputs["Color"])

    # Ensure the material output node exists and connect the BSDF
    material_output = None
    for node in material.node_tree.nodes:
        if node.type == "OUTPUT_MATERIAL":
            material_output = node
            break

    # If there's no Material Output node, we don't create a new one
    if material_output:
        # Connect the Principled BSDF node to the existing Material Output node's Surface input
        material.node_tree.links.new(shader_node.outputs["BSDF"], material_output.inputs["Surface"])
    else:
        print(f"Warning: No Material Output node found for material '{material.name}'.")

print('Done')

# Remove objects without materials
for obj in bpy.context.scene.objects:
    if len(obj.material_slots) > 0:
        if obj.material_slots[0].material is None:
            print(f"Object '{obj.name}' has no material assigned to the first slot.")
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        print(f"Object '{obj.name}' has no material slots.")
