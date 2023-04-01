#script to quickly set up splatoon backgrounds
#version with normal map blue channel fixing, works on blender 3.4
#author: cetacylanol
import bpy
from bpy_extras.io_utils import ImportHelper
import os

#takes a material as input and adds textures to it, looking in the "textures" subfolder,
#blue fix decides if 1 should be added to the blue channel of a normal map
#texture list order["Alb", "Ao", "Mtl", "Rgh", "Emi", "Opa", "Nrm"]
def set_mat(mat, texs, pres, blue_fix = False, use_ao = True):
    #get parts of the node tree
    t_nodes = mat.node_tree.nodes
    #lets u use new link without having to write the whole thing every time?
    link = mat.node_tree.links.new

    pr_node = t_nodes.get('Principled BSDF')
    pr_node.inputs[7].default_value = 0.5
    mat.use_backface_culling = True
    mat.blend_method = 'OPAQUE'

    check_nodes(tree=mat.node_tree)

    #add textures to node tree and connect
    if(texs[0] != '0'):
        if(not pres[0]):
            alb_nd = add_img_node(t_nodes, texs[0], location=(-550,750))

            if(texs[1] != '0' and use_ao):
                #connect ao
                #some of the backgrounds use a separate UV map for ao... so this doesnt add that. I might add it later
                ao_nd = add_img_node(t_nodes, texs[1], location=(-550,500))
                mix_ao_nd = t_nodes.new('ShaderNodeMix')
                mix_ao_nd.location = (-450, 260)
                mix_ao_nd.data_type = 'RGBA'
                mix_ao_nd.blend_type = 'MULTIPLY'
                mix_ao_nd.inputs[0].default_value = 1

                link(alb_nd.outputs[0], mix_ao_nd.inputs[6])
                link(ao_nd.outputs[0], mix_ao_nd.inputs[7])
                link(mix_ao_nd.outputs[2], pr_node.inputs[0])
            else:
                link(alb_nd.outputs[0], pr_node.inputs[0])


    if(texs[2] != '0'):
        if(not pres[1]):
            #set metal
            mtl_nd = add_img_node(t_nodes, texs[2], location=(-300,250), cspace='Non-Color')
            link(mtl_nd.outputs[0], pr_node.inputs[6])
    if(texs[3] != '0'):
        if(not pres[2]):
            #set roughness
            rgh_nd = add_img_node(t_nodes, texs[3], location=(-300,0), cspace='Non-Color')
            link(rgh_nd.outputs[0], pr_node.inputs[9])
    if(texs[4] != '0' or texs[7] != '0'):
        if(not pres[3]):
            #set emi
            if(texs[4] == '0'):
                emi_nd = add_img_node(t_nodes, texs[7], location=(-300,-250))
            else:
                emi_nd = add_img_node(t_nodes, texs[4], location=(-300,-250))
            
            link(emi_nd.outputs[0], pr_node.inputs[19])
    if(texs[5] != '0'):
        if(not pres[4]):
            opa_nd = add_img_node(t_nodes, texs[5], location=(-300,-500), cspace='Non-Color')
            link(opa_nd.outputs[0], pr_node.inputs[21])
            mat.blend_method = 'CLIP'
    if(texs[6] != '0'):
        if(pres[5]):
            pr_node.inputs[22].links[0].from_node.inputs[0].default_value = 1
        else:
            nrm_nd = add_img_node(t_nodes, texs[6], location=(-500,-750), cspace='Non-Color')
            nrm_map = t_nodes.new('ShaderNodeNormalMap')
            nrm_map.location = (-250, -750)

            if(blue_fix):
                #add 1 to blue channel
                sep_col = t_nodes.new('ShaderNodeSeparateColor')
                sep_col.location = (-300,-800)
                comb_col = t_nodes.new('ShaderNodeCombineColor')
                comb_col.location = (-250,-800)
                comb_col.inputs[2].default_value = 1

                link(nrm_nd.outputs[0], sep_col.inputs[0])
                link(sep_col.outputs[0], comb_col.inputs[0])
                link(sep_col.outputs[1], comb_col.inputs[1])
                link(comb_col.outputs[0], nrm_map.inputs[1])
            else:
                link(nrm_nd.outputs[0], nrm_map.inputs[1])

            link(nrm_map.outputs[0], pr_node.inputs[22])
    
#checks if there are textures linked already
def check_nodes(tree):
    #["Alb", "Ao", "Mtl", "Rgh", "Emi", "Opa", "Nrm"]
    presents = [False, False, False, False, False, False]
    in_socks = ["Base Color", "Metalic", "Roughness", "Emission", "Alpha", "Normal"]
    ls = tree.links

    for l in ls:
        nnm = l.to_node.name
        snm = l.to_socket.name

        if(nnm == "Principled BSDF"):
            for i, s in enumerate(in_socks):
                if(snm == s):
                    presents[i] = True

    return presents

#adds image node to tree, Nodes is nodes in tree, image is path to image texture, 
#location is a tuple containing location, cspace is colour space for image
#returns image node
def add_img_node(nodes, image, location = (0,0), cspace = 'sRGB'):
    nd = nodes.new('ShaderNodeTexImage')
    tx = bpy.data.images.load(image)
    tx.colorspace_settings.name = cspace

    nd.image = tx
    nd.location = location

    return nd


#takes material name and texture directory as input, outputs array of present textures. If a map its path is returned as 0
def get_attr(mname, txdir):
    attr = []
    suffixes = ["Alb", "Ao", "Mtl", "Rgh", "Emi", "Opa", "Nrm", "Emm"]
    namebase = mname.split('.')[0]

    for s in suffixes:
        td = txdir + '\\' + namebase + '_' +s+ '.png'
        #baketd = txdir + '\\' + mname + 'Bake_' +s+ '.png'
        if (os.path.exists(td)):
            attr.append(td)
        else:
            attr.append('0')

    return attr

#gets list of materials on selected objects without duplicates
def get_mats(objs):
    mats = []
    for o in objs:
        mslots = o.material_slots
        for m in mslots:
            if m.material not in mats:
                mats.append(m.material)
    return mats

#runner for main quick mats function
def setup_mats(self, context):
    mats = get_mats(context.selected_objects)
    #path to folder with the textures in
    txdir = os.path.dirname(self.properties.filepath)

    if(mats == []):
        print("none of the selected objects have materials assigned")
    else:
        for m in mats:
            attr = get_attr(m.name, txdir)
            pres = check_nodes(m.node_tree)
            set_mat(m, attr, pres, context.scene.splat_tex_settings.blue_channel_fix, context.scene.splat_tex_settings.use_ao_tex)



class OT_quick_mats(bpy.types.Operator, ImportHelper):
    bl_idname = 'object.quick_mats'
    bl_label = 'setup materials quickly'

    def execute(self, context):
        setup_mats(self, context)
        #print(os.path.dirname(self.properties.filepath))
        return {'FINISHED'}


class VIEW3D_PT_Splatoon_Quick_Mats(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splatoon Tools"
    bl_label = "Quick Materials"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row1 = layout.row()
        row1.operator("object.quick_mats")
        row2 = layout.row()
        row2.prop(scene.splat_tex_settings, 'blue_channel_fix')
        row3 = layout.row()
        row3.prop(scene.splat_tex_settings, 'use_ao_tex')

class SplatTexSettings(bpy.types.PropertyGroup):
    blue_channel_fix : bpy.props.BoolProperty(name='add 1 to normal map blue channel')
    use_ao_tex : bpy.props.BoolProperty(name='use ambient occlusion textures', default = True)

def register():
    bpy.utils.register_class(VIEW3D_PT_Splatoon_Quick_Mats)
    bpy.utils.register_class(OT_quick_mats)
    bpy.utils.register_class(SplatTexSettings)
    bpy.types.Scene.splat_tex_settings = bpy.props.PointerProperty(type=SplatTexSettings)
    

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_Splatoon_Quick_Mats)
    bpy.utils.unregister_class(OT_quick_mats)
    bpy.utils.unregister_class(SplatTexSettings)

    del bpy.types.Scene.splat_tex_settings

if __name__ == '__main__':
    register()