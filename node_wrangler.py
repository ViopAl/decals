import bpy
import re
from os import path
from mathutils import Vector


names = {'Base Color': ['diffuse', 'diff', 'albedo', 'base', 'col', 'color'],
         'Subsurface Color' : ['sss', 'subsurface'],
         'Metallic' : ['metallic', 'metalness', 'metal', 'mtl'],
         'Specular' : ['specularity',  'specular',  'spec',  'spc'],
         'Normal' : ['normal', 'nor', 'nrm', 'nrml', 'norm'],
         'Bump' : ['bump', 'bmp'],
         'Roughness' : ['roughness', 'rough', 'rgh'],
         'Gloss' : ['gloss', 'glossy', 'glossiness'],
         'Displacement': ['displacement' ,'displace', 'disp', 'dsp', 'height', 'heightmap'],
         'Opacity': ['opac' ,'opacity', 'op'], 
         'Ambiant Oclusion' : ['ao', 'oclu'],
         'Preview' : ['preview', 'thmb', 'thumbnail', 'prev']
        }

def nw(self, context, principled, tree) -> bpy.types.Image:
    """Setup a node tree as the original node wrangler plus some things.
    return file should be used for preview"""

    nodes, links = tree.nodes, tree.links
    active_node = principled
    if not (active_node and active_node.bl_idname == 'ShaderNodeBsdfPrincipled'):
        self.report({'INFO'}, 'Select Principled BSDF')
        return {'CANCELLED'}

    # Helper_functions
    def split_into__components(fname):
        # Split filename into components
        # 'WallTexture_diff_2k.002.jpg' -> ['Wall', 'Texture', 'diff', 'k']
        # Remove extension
        fname = path.splitext(fname)[0]
        # Remove digits
        fname = ''.join(i for i in fname if not i.isdigit())
        # Separate CamelCase by space
        fname = re.sub("([a-z])([A-Z])","\g<1> \g<2>",fname)
        # Replace common separators with SPACE
        seperators = ['_', '.', '-', '__', '--', '#']
        for sep in seperators:
            fname = fname.replace(sep, ' ')

        components = fname.split(' ')
        components = [c.lower() for c in components]
        return components


    socketnames = [
    ['Displacement', names['Displacement'], None],
    ['Base Color', names['Base Color'], None],
    ['Subsurface Color', names['Subsurface Color'], None],
    ['Metallic', names['Metallic'], None],
    ['Specular', names['Specular'], None],
    ['Roughness', names['Roughness'] + names['Gloss'] , None],
    ['Normal', names['Normal'] + names['Bump'] , None],
    ['Alpha', names['Opacity'], None],
    ['IOR', names['Ambiant Oclusion'], None], # Just to match AO
    ['Emission Strength', names['Preview'], None]] # Just to match preview

    # Look through texture_types and set value as filename of first matched file
    def match_files_to_socket_names():
        for sname in socketnames:
            for file in self.files:
                fname = file.name
                filenamecomponents = split_into__components(fname)
                matches = set(sname[1]).intersection(set(filenamecomponents))
                # TODO: ignore basename (if texture is named "fancy_metal_nor", it will be detected as metallic map, not normal map)
                if matches:
                    sname[2] = fname
                    break

    match_files_to_socket_names()
    # Remove socketnames without found files
    socketnames = [s for s in socketnames if s[2]
                    and path.exists(self.directory+s[2])]
    if not socketnames:
        self.report({'INFO'}, 'No matching images found')
        print('No matching images found')
        return {'CANCELLED'}

    # Don't override path earlier as os.path is used to check the absolute path
    import_path = self.directory
    if self.relative_path:
        if bpy.data.filepath:
            import_path = bpy.path.relpath(self.directory)
        else:
            self.report({'WARNING'}, 'Relative paths cannot be used with unsaved scenes!')
            print('Relative paths cannot be used with unsaved scenes!')

    # Add found images
    print('\nMatched Textures:')
    texture_nodes = []
    disp_texture = None
    normal_node = None
    roughness_node = None
    hue_node = None
    mix_rgb_node = None
    prev_image = None
    for i, sname in enumerate(socketnames):
        print(i, sname[0], sname[2])

        # DISPLACEMENT NODES
        if sname[0] == 'Displacement':
            disp_texture = nodes.new(type='ShaderNodeTexImage')
            img = bpy.data.images.load(path.join(import_path, sname[2]))
            disp_texture.image = img
            disp_texture.label = 'Displacement'
            if disp_texture.image:
                #disp_texture.image.colorspace_settings.is_data = True
                disp_texture.image.colorspace_settings.name = 'Non-Color'


            # Add displacement offset nodes
            disp_node = nodes.new(type='ShaderNodeDisplacement')
            disp_node.location = active_node.location + Vector((0, -560))
            link = links.new(disp_node.inputs[0], disp_texture.outputs[0])

            # TODO Turn on true displacement in the material
            # Too complicated for now

            # Find output node
            output_node = [n for n in nodes if n.bl_idname == 'ShaderNodeOutputMaterial']
            if output_node:
                if not output_node[0].inputs[2].is_linked:
                    link = links.new(output_node[0].inputs[2], disp_node.outputs[0])

            continue

        if not active_node.inputs[sname[0]].is_linked:
            # No texture node connected -> add texture node with new image
            texture_node = nodes.new(type='ShaderNodeTexImage')
            img = bpy.data.images.load(path.join(import_path, sname[2]))
            img.true_filepath = path.join(self.directory, sname[2])
            texture_node.image = img
            texture_node.extension = 'CLIP'

            # NORMAL NODES
            if sname[0] == 'Normal':
                # Test if new texture node is normal or bump map
                fname_components = split_into__components(sname[2])
                match_normal = set(names['Normal']).intersection(set(fname_components))
                match_bump = set(names['Bump']).intersection(set(fname_components))
                if match_normal:
                    # If Normal add normal node in between
                    normal_node = nodes.new(type='ShaderNodeNormalMap')
                    link = links.new(normal_node.inputs[1], texture_node.outputs[0])
                elif match_bump:
                    # If Bump add bump node in between
                    normal_node = nodes.new(type='ShaderNodeBump')
                    link = links.new(normal_node.inputs[2], texture_node.outputs[0])

                link = links.new(active_node.inputs[sname[0]], normal_node.outputs[0])
                normal_node_texture = texture_node
            elif sname[0] == 'Base Color':
                if not hue_node:
                   hue_node = nodes.new(type='ShaderNodeHueSaturation')
                if not mix_rgb_node:
                    mix_rgb_node = nodes.new(type='ShaderNodeMixRGB')
                    mix_rgb_node.blend_type = 'MULTIPLY'
                if not prev_image:
                    prev_image = img
                links.new(hue_node.inputs['Color'], texture_node.outputs['Color'])
                links.new(mix_rgb_node.inputs['Color1'], hue_node.outputs['Color'])
                links.new(active_node.inputs[sname[0]], mix_rgb_node.outputs['Color'])
                base_node_texture = texture_node
                texture_node.image.colorspace_settings.is_data = True
                texture_node.image.colorspace_settings.name = 'sRGB'

            elif sname[0] == 'IOR': #ambiant ocllusion
                if not mix_rgb_node:
                    mix_rgb_node = nodes.new(type='ShaderNodeMixRGB')
                    mix_rgb_node.blend_type = 'MULTIPLY'
                links.new(mix_rgb_node.inputs['Color2'], texture_node.outputs['Color'])
            elif sname[0] == 'Emission Strength': #preview
                prev_image = img
                img.use_fake_user = True
                tree.nodes.remove(texture_node)
                texture_node = None
            elif sname[0] == 'Alpha':
                pass
            elif sname[0] == 'Roughness':
                # Test if glossy or roughness map
                fname_components = split_into__components(sname[2])
                match_rough = set(names['Roughness']).intersection(set(fname_components))
                match_gloss = set(names['Gloss']).intersection(set(fname_components))

                if match_rough:
                    # If Roughness nothing to to
                    link = links.new(active_node.inputs[sname[0]], texture_node.outputs[0])

                elif match_gloss:
                    # If Gloss Map add invert node
                    invert_node = nodes.new(type='ShaderNodeInvert')
                    link = links.new(invert_node.inputs[1], texture_node.outputs[0])

                    link = links.new(active_node.inputs[sname[0]], invert_node.outputs[0])
                    roughness_node = texture_node

            else:
                # This is a simple connection Texture --> Input slot
                link = links.new(active_node.inputs[sname[0]], texture_node.outputs[0])
        else:
            # If already texture connected. add to node list for alignment
            texture_node = active_node.inputs[sname[0]].links[0].from_node

        # This are all connected texture nodes
        if texture_node:
            texture_nodes.append(texture_node)
            texture_node.label = sname[0]

    if disp_texture:
        texture_nodes.append(disp_texture)

    # Alignment
    for i, texture_node in enumerate(texture_nodes):
        offset = Vector((-550, (i * -280) + 200))
        texture_node.location = active_node.location + offset

    if normal_node:
        # Extra alignment if normal node was added
        normal_node.location = normal_node_texture.location + Vector((300, 0))

    if hue_node:
        # Extra alignment if hue node was added
        hue_node.location = base_node_texture.location + Vector((300, 0))
        if mix_rgb_node:
            # Extra alignment if mix rgb node was added
            hue_node.location = base_node_texture.location + Vector((300, 0))



    if roughness_node:
        # Alignment of invert node if glossy map
        invert_node.location = roughness_node.location + Vector((300, 0))

    # Add texture input + mapping
    mapping = nodes.new(type='ShaderNodeMapping')
    mapping.inputs[1].default_value = (0.5,0.5,0)

    mapping.location = active_node.location + Vector((-1050, 0))
    if len(texture_nodes) > 1:
        # If more than one texture add reroute node in between
        reroute = nodes.new(type='NodeReroute')
        texture_nodes.append(reroute)
        tex_coords = Vector((texture_nodes[0].location.x, sum(n.location.y for n in texture_nodes)/len(texture_nodes)))
        reroute.location = tex_coords + Vector((-50, -120))
        for texture_node in texture_nodes:
            link = links.new(texture_node.inputs[0], reroute.outputs[0])
        link = links.new(reroute.inputs[0], mapping.outputs[0])
    else:
        link = links.new(texture_nodes[0].inputs[0], mapping.outputs[0])

    # Connect texture_coordiantes to mapping node
    texture_input = nodes.new(type='ShaderNodeTexCoord')
    texture_input.location = mapping.location + Vector((-200, 0))
    link = links.new(mapping.inputs[0], texture_input.outputs[2])

    # Create frame around tex coords and mapping
    frame = nodes.new(type='NodeFrame')
    frame.label = 'Mapping'
    mapping.parent = frame
    texture_input.parent = frame
    frame.update()

    # Create frame around texture nodes
    frame = nodes.new(type='NodeFrame')
    frame.label = 'Textures'
    for tnode in texture_nodes:
        tnode.parent = frame
    frame.update()

    # Just to be sure
    active_node.select = False
    nodes.update()
    links.update()
    #force_update(context)
    if prev_image:
        return prev_image
    else:
        return img