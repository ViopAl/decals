bl_info = {
    "name": "Decals",
    "author": "Flores Arnaud",
    "version": (1, 0),
    "blender": (2, 92, 0),
    'category': 'SpaceView3D',
    }

import bpy
from . import operators, panels
from bpy.props import IntProperty, StringProperty, BoolProperty, EnumProperty, PointerProperty

class DecalsProperties(bpy.types.PropertyGroup):
    decals_thmb: EnumProperty(items=operators.update_images)
    previews_img: StringProperty(name='imgs_names')

class NodeContainer(bpy.types.PropertyGroup):
    material: bpy.props.PointerProperty(
        name="Material",
        type=bpy.types.Material,
    )
    node_name: bpy.props.StringProperty(
        default="",
        name="Node",
        description="Name of the node"
    )

    @property
    def node(self):
        mat = self.material
        if mat:
            return mat.node_tree.nodes.get(self.node_name)
        else:
            return None

classes = (panels.DECALSTOOL_PT_MainPanel, DecalsProperties, NodeContainer, operators.DECALSTOOL_OT_AddDecal, operators.DECALSTOOL_OT_CreateDecal)

def register():

    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.decals_tool = PointerProperty(type=DecalsProperties)
    bpy.types.Object.decal_node = PointerProperty(type=NodeContainer)
    bpy.types.ShaderNodeTree.already_setup = BoolProperty(default=False)
    bpy.types.Image.true_filepath = StringProperty(default='')

def unregister():
    
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.decals_tool
    del bpy.types.Object.decal_node
    del bpy.types.ShaderNodeTree.already_setup
    del bpy.types.Image.true_filepath