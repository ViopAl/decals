import bpy

class DECALSTOOL_PT_MainPanel(bpy.types.Panel):
    bl_idname = "decals_tool.main_panel"
    bl_label = "Main panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Misc"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.template_icon_view(scene.decals_tool, "decals_thmb", show_labels=True)
        #operator
        layout.operator('decals_tool.add_decal', text='Add decal')
        layout.operator('decals_tool.create_decal', text='Create decal')
        node = context.active_object.decal_node.node
        if node:
            for inp in node.inputs:
                if hasattr(inp, 'default_value'):
                    layout.prop(inp, 'default_value', text=inp.name)

        