import bpy
import random
import struct
from bpy_extras import view3d_utils
from . import utils
from .utils import get_node, get_node_by_label
from . import node_wrangler
from mathutils import Vector
from bpy_extras.io_utils import ImportHelper
import bpy.utils.previews

preview_coll = {}
def reload_prevs():
    global preview_coll
    preview_coll['main'] = bpy.utils.previews.new()
    previews_img = bpy.context.scene.decals_tool.previews_img.split(',')
    for img_name in previews_img:
        if img_name in bpy.data.images:
            prev = preview_coll['main'].load(img_name, bpy.data.images[img_name].true_filepath, 'IMAGE')
    #return preview_coll

def update_images(cls, context):
    global preview_coll 
    items = []
    if context.scene.decals_tool.previews_img:
        if not preview_coll:
            reload_prevs()
        img_names = context.scene.decals_tool.previews_img.split(',')
        for idx, img_name in enumerate(img_names):
            if img_name and img_name in preview_coll['main']:
                img = preview_coll['main'][img_name]
                item = (img_name, img_name, img_name, img.icon_id, idx)
                items.append(item)
    return items


class DECALSTOOL_OT_AddDecal(bpy.types.Operator, ImportHelper):
    bl_idname = "decals_tool.add_decal"
    bl_label = "add decal"
    bl_options = {'UNDO', 'REGISTER'}
    files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement,
                                         options={'HIDDEN', 'SKIP_SAVE'})
    directory: bpy.props.StringProperty(name='Directory',
                                        subtype='DIR_PATH',
                                        default='',
                                        description='Folder to search in for image files')
    relative_path: bpy.props.BoolProperty(name='Relative Path', 
                                description='Select the file relative to the blend file',
                                default=True)
    order = ["filepath","files",]

    @classmethod
    def poll(cls, context : bpy.types.Context) -> bool:
        return True
    
    def execute(self, context):
        # Check if everything is ok
        if not self.directory:
            self.report({'INFO'}, 'No Folder Selected')
            return {'CANCELLED'}
        if not self.files[:]:
            self.report({'INFO'}, 'No Files Selected')
            return {'CANCELLED'}
        
        #init preview_coll
        global preview_coll
        if not preview_coll:
            preview_coll['main'] = bpy.utils.previews.new()
        group_tree = bpy.data.node_groups.new('Decal', 'ShaderNodeTree')
        principled = group_tree.nodes.new('ShaderNodeBsdfPrincipled')
        #add maps to material
        if principled:
            preview = node_wrangler.nw(self, context, principled, group_tree)
        if preview:
            #get preview and add id to diplsayed ids
            print(preview.true_filepath)
            preview_coll['main'].load(preview.name, preview.true_filepath, 'IMAGE')
            group_tree.name = preview.name
            previews_img = context.scene.decals_tool.previews_img.split(',')
            previews_img.append(preview.name)
            context.scene.decals_tool.previews_img = ','.join(previews_img)
            context.scene.decals_tool.decals_thmb = preview.name
        return {'FINISHED'}

class DECALSTOOL_OT_CreateDecal(bpy.types.Operator):
    bl_idname = "decals_tool.create_decal"
    bl_label = "create decal"
    bl_options = {'UNDO', 'REGISTER'}
    clicked = False

    @classmethod
    def poll(cls, context : bpy.types.Context) -> bool:
        return True
    
    def setup_base_group(self, node_tree : bpy.types.NodeTree,
                               curr_node : bpy.types.Node) -> None:
        """Setup the base decal group wich contain all maps info and the mix shader.
        The node tree sent should be already setup by the node wrangler"""
        grp_in = node_tree.nodes.new('NodeGroupInput')
        grp_out = node_tree.nodes.new('NodeGroupOutput')
        mix = node_tree.nodes.new('ShaderNodeMixShader')
        principled = get_node(node_tree, 'BSDF_PRINCIPLED')
        hue = get_node(node_tree, 'HUE_SAT')
        mapping = get_node(node_tree, 'MAPPING')
        normal_map = get_node(node_tree, 'NORMAL_MAP')
        coord = get_node(node_tree, 'TEX_COORD')
        mat_out = get_node(node_tree, 'OUTPUT_MATERIAL')
        alpha = get_node_by_label(node_tree, 'Alpha')

        #remove useless nodes
        if coord:
            node_tree.nodes.remove(coord)
        if mat_out:
            node_tree.nodes.remove(mat_out)        
        
        #create links and postion nodes
        curr_node.inputs.new(mix.inputs['Shader'].bl_idname, 'Shader')
        curr_node.outputs.new(mix.outputs['Shader'].bl_idname, 'Shader')
        node_tree.links.new(mix.inputs['Shader'], grp_in.outputs[0])
        node_tree.links.new(grp_out.inputs[0], mix.outputs[0])
        if principled:
            node_tree.links.new(mix.inputs[2], principled.outputs[0])
            mix.location = principled.location + Vector((300, 0))
            grp_out.location = mix.location + Vector((300, 0))
        if hue:
            curr_node.inputs.new(hue.inputs['Hue'].bl_idname, 'Hue')
            curr_node.inputs.new(hue.inputs['Saturation'].bl_idname, 'Saturation')
            curr_node.inputs.new(hue.inputs['Value'].bl_idname, 'Value')
            node_tree.links.new(hue.inputs['Hue'], grp_in.outputs['Hue'])
            node_tree.links.new(hue.inputs['Saturation'], grp_in.outputs['Saturation'])
            node_tree.links.new(hue.inputs['Value'], grp_in.outputs['Value'])
        if mapping:
            node_tree.links.new(mapping.inputs['Vector'], grp_in.outputs[4])
            grp_in.location = mapping.location + Vector((-300, 0))
        if normal_map:
            node_tree.links.new(normal_map.inputs['Strength'],
                                grp_in.outputs[5])
        if alpha:
            node_tree.links.new(mix.inputs[0], alpha.outputs['Color'])
        node_tree.already_setup = True

    def setup_intermediate_group(self, node, node_tree, empty):
        """Add texture coordinate, input and output to a group wich
        contain only a base_group node"""
        #need group node tou create output and input or crash.. do no crash in the setup base group
        base_group = get_node(node_tree, 'GROUP')
        grp_in = node_tree.nodes.new('NodeGroupInput')
        grp_out = node_tree.nodes.new('NodeGroupOutput')
        tex_coord = node_tree.nodes.new('ShaderNodeTexCoord')
        tex_coord.object = empty
        if base_group:
            node_tree.outputs.new(base_group.outputs['Shader'].bl_idname, 'Shader')
            node_tree.links.new(grp_out.inputs['Shader'], base_group.outputs['Shader'])
            node_tree.links.new(base_group.inputs['Vector'], tex_coord.outputs['Object'])
            for idx, inpu in enumerate(base_group.inputs.keys()):
                if inpu != 'Vector':
                    try:
                        inp = node.inputs.new(base_group.inputs[idx].bl_idname, base_group.inputs[idx].name)
                        node_tree.links.new(base_group.inputs[idx], grp_in.outputs[base_group.inputs[idx].name])
                    except:
                        pass
            grp_in.location = base_group.location + Vector((-600, 0))
            tex_coord.location = base_group.location + Vector((-300, -200))
            grp_out.location = base_group.location + Vector((300, 0))

    def get_clicked_obj(self, context):
        origin = view3d_utils.region_2d_to_origin_3d(context.region,
                                                     context.space_data.region_3d,
                                                     self.coord, clamp=None)
        vector = context.scene.cursor.location - origin
        graph = context.evaluated_depsgraph_get()
        result, location, normal, index, obj, matrix = context.scene.ray_cast(graph, origin, vector)
        if obj:
            return obj
        return None

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.clicked = True
            self.coord = (event.mouse_x, event.mouse_y)
            return {'PASS_THROUGH'}
        if self.clicked:
            obj = self.get_clicked_obj(context)
            self.clicked = False
            if obj:
                #add empty and create decal nodes setup
                decal = bpy.data.node_groups[context.scene.decals_tool.decals_thmb]
                empt = bpy.data.objects.new(decal.name, None)
                context.collection.objects.link(empt)
                empt.location = context.scene.cursor.location
                empt.rotation_euler = context.scene.cursor.rotation_euler
                base_grp = utils.create_node_group([], decal.name, obj.active_material.node_tree, decal)
                #base_grp.node_tree.
                if not decal.already_setup:
                    self.setup_base_group(base_grp.node_tree, base_grp)
                #as we want a different empty, recreate intermediate grp each time
                intermed_grp = utils.create_node_group([base_grp], 'DECAL ' + decal.name, obj.active_material.node_tree)
                self.setup_intermediate_group(intermed_grp, intermed_grp.node_tree, empt)
                out_mat = get_node(obj.active_material.node_tree, 'OUTPUT_MATERIAL')
                previous = out_mat.inputs['Surface'].links[0].from_node
                obj.active_material.node_tree.links.new(out_mat.inputs['Surface'], intermed_grp.outputs[0])
                obj.active_material.node_tree.links.new(intermed_grp.inputs[0], previous.outputs[0])
                #setup default values
                values = [0.5, 1, 1, 1]
                for idx, inp in enumerate(intermed_grp.inputs):
                    if idx > 0:
                        inp.default_value = values[idx - 1]

                #store node information into empty
                empt.decal_node.material = obj.active_material
                empt.decal_node.node_name = intermed_grp.name
                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = empt
                empt.select_set(True)

                if base_grp.name in obj.active_material.node_tree.nodes:
                    obj.active_material.node_tree.nodes.remove(base_grp)
                #position nodes
                offset = Vector((previous.width + 50, 0))
                intermed_grp.location = previous.location + offset
                out_mat.location += offset

            bpy.ops.wm.tool_set_by_id(name='builtin.select_box')
            return {'FINISHED'}
        return {'PASS_THROUGH'}
        
    def invoke(self, context, event):
        #setup 3d cursor tool
        bpy.ops.wm.tool_set_by_id(name='builtin.cursor')
        tool = context.workspace.tools.from_space_view3d_mode(context.mode)
        props = tool.operator_properties('view3d.cursor3d')
        props['orientation'] = 3
        props['use_depth'] = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}