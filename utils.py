import bpy
import time
#region group create

def get_node(node_tree : bpy.types.NodeTree, node_type : str) -> bpy.types.Node:
    found = None
    for node in node_tree.nodes:
        if node.type == node_type:
            found = node
            break
    return found

def get_node_by_label(node_tree : bpy.types.NodeTree, label : str) -> bpy.types.Node:
    found = None
    for node in node_tree.nodes:
        if node.label == label:
            found = node
            break
    return found

def copy_attributes(attributes, old_node, new_node):
    """copies the list of attributes from the old to the new node if the attribute exists"""

    #check if the attribute exists and copy it
    for attr in attributes:
        if hasattr(new_node, attr):
            try:
                setattr(new_node, attr, getattr(old_node, attr))
            except:
                pass

def get_node_attributes(node):
    """returns a list of all propertie identifiers if they shoulnd't be ignored"""

    #all attributes that shouldn't be copied
    ignore_attributes = ( "rna_type", "type", "dimensions", "inputs", "outputs", "internal_links", "select")

    attributes = []
    for attr in node.bl_rna.properties:
        #check if the attribute should be copied and add it to the list of attributes to copy
        if not attr.identifier in ignore_attributes and not attr.identifier.split("_")[0] == "bl":
            attributes.append(attr.identifier)
    return attributes

def copy_nodes(nodes, group):
    """copies all nodes from the given list into the group with their attributes
    -nodes : nodes to copy in group
    -group : group node_tree"""

    #the attributes that should be copied for every link
    input_attributes = ( "default_value", "name" )
    output_attributes = ( "default_value", "name" )

    for node in nodes:
        #create a new node in the group and find and copy its attributes
        new_node = group.nodes.new( node.bl_idname )
        node_attributes = get_node_attributes( node )
        copy_attributes( node_attributes, node, new_node )

        #copy the attributes for all inputs
        for i, inp in enumerate(node.inputs):
            copy_attributes( input_attributes, inp, new_node.inputs[i] )

        #copy the attributes for all outputs
        for i, out in enumerate(node.outputs):
            copy_attributes( output_attributes, out, new_node.outputs[i] )

def copy_links(nodes, group):
    """copies all links between the nodes in the list to the nodes in the group
    -nodes : nodes to copy links
    -group : group node_tree"""

    for node in nodes:
        #find the corresponding node in the created group
        new_node = group.nodes[ node.name ]

        #enumerate over every link in the nodes inputs
        for i, inp in enumerate( node.inputs ):
            for link in inp.links:
                #find the connected node for the link in the group
                connected_node = group.nodes[ link.from_node.name ]
                #connect the group nodes
                group.links.new( connected_node.outputs[ link.from_socket.name ], new_node.inputs[i] )

def create_node_group(nodes, grp_name, target_tree, group_tree=None):
    """create a node group in the target_tree
    -nodes : nodes to add in the group
    -grp_name : name of the new node group
    -target_tree : tree where the new node group should be create
    -group_tree : specifie a node group to use
    """
    if not group_tree:
        group_tree = bpy.data.node_groups.new(grp_name, 'ShaderNodeTree')
    
    group = target_tree.nodes.new('ShaderNodeGroup')
    group.node_tree = group_tree
    #copy all nodes from the list to the created group with all their attributes
    copy_nodes(nodes, group_tree)
    #copy the links between the nodes to the created groups nodes
    copy_links(nodes, group_tree)
    return group
#endregion

def create_nodes_decals():
    path_nodes_blend = os.path.join(os.path.dirname(__file__), 'decalsnodes.blend')
    if 'Decals_base' not in bpy.data.node_groups:
        ngroups_from_file(path_nodes_blend)
    decal_node = node_tree.nodes.new('ShaderNodeGroup')
    decal_node.name = 'aname'
    decal_node.node_tree = bpy.data.node_groups['Decals_base']


def ngroups_from_file(filepath : str) -> list: 
    names = None
    for name in groups_name:
        if not name in bpy.data.node_groups:
            with bpy.data.libraries.load(filepath, link = False) as (data_from, data_to):
                data_to.node_groups = data_from.node_groups
                names = [grp.name for grp in data_from.node_groups]
    return names


