#script to quickly set up splatoon backgrounds
#v1.2
#Emm textures now used as emission strength rather than emission, works on blender 3.4
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

    if(pr_node is not None):
        pr_node.inputs[7].default_value = 0.5
        pr_node.inputs[6].default_value = 0
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
                mtl_nd = add_img_node(t_nodes, texs[2], location=(-300,200), cspace='Non-Color')
                link(mtl_nd.outputs[0], pr_node.inputs[6])
        if(texs[3] != '0'):
            if(not pres[2]):
                #set roughness
                rgh_nd = add_img_node(t_nodes, texs[3], location=(-300,0), cspace='Non-Color')
                link(rgh_nd.outputs[0], pr_node.inputs[9])
        if(texs[4] != '0'):
            if(not pres[3]):
                #set emission
                emi_nd = add_img_node(t_nodes, texs[4], location=(-300,-250))
                
                link(emi_nd.outputs[0], pr_node.inputs[19])
        if(texs[7] !='0'):
            if(not pres[3]):
                emm_nd = add_img_node(t_nodes, texs[7], location=(-300,-400))
                link(emm_nd.outputs[0], pr_node.inputs[20])
        if(texs[5] != '0'):
            #set opacity
            if(not pres[4]):
                opa_nd = add_img_node(t_nodes, texs[5], location=(-300,-500), cspace='Non-Color')
                link(opa_nd.outputs[0], pr_node.inputs[21])
                mat.blend_method = 'CLIP'
        if(texs[6] != '0'):
            #set normal
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

def set_mat_adv(mat, texs, scene):
    tx_to_add = []
    t_nodes = mat.node_tree.nodes
    link = mat.node_tree.links.new

    tex_transforms = []
    shade_nodes = []
    for s in scene.splat_shade_templates:
        #get the tex transform info so we can use them later
        if not s.s_is_shader:
            tex_transforms.append(s)
        else:
            shade_nodes.append(s)

        for t in s.s_textures:
            tx_to_add.append(t.texture_kind)

    #SET of textures we need to add
    tx_to_add = list(set(tx_to_add))

    #changes image textures that we need into sockets to connect later.
    init_img_sockets(mat, tx_to_add, texs, scene.splat_tex_settings.blue_channel_fix)

    #sort into placement order :)
    tex_transforms.sort(key= lambda tt: tt.s_order)
    #do texture transforms!
    for st in tex_transforms:
        trnode = ''
        
        if required_textures_present(st, texs):
            #create transform node
            if st.s_node in bpy.data.node_groups:
                trnode = t_nodes.new('ShaderNodeGroup')
                trnode.node_tree = bpy.data.node_groups[st.s_node]
            else:
                trnode = t_nodes.new(st.s_node)

            #plugging in textures
            for stt in st.s_textures:
                if(stt.texture_kind in texs and texs[stt.texture_kind] != '0'):
                    link(texs[stt.texture_kind], trnode.inputs[int(stt.s_input)])
            
            #setting output socket as new texture
            if(st.out_socket == 'sock_default'):
                texs[st.out_texture_kind] = trnode.outputs[0]
            else:
                texs[st.out_texture_kind] = trnode.outputs[int(st.out_socket)]


    shade_nodes.sort(key= lambda tt: tt.s_order)
    sock_out = None 

    for snd in shade_nodes:
        trnode = ''
        if required_textures_present(snd, texs):
            #create shader node
            if snd.s_node in bpy.data.node_groups:
                trnode = t_nodes.new('ShaderNodeGroup')
                trnode.node_tree = bpy.data.node_groups[snd.s_node]
            else:
                trnode = t_nodes.new(snd.s_node)

            for sntx in snd.s_textures:
                link(texs[sntx.texture_kind], trnode.inputs[int(sntx.s_input)])


            


#checks that all required textures have values in the texture dictionary
#returns bool
def required_textures_present(ninfo, texs):
    addit = True
    p = 0
    #checking if required textures are here
    while(addit and p < len(ninfo.s_textures)):
        if ninfo.s_textures[p].s_req:
            #is there something in this required textures location?
            if(ninfo.s_textures[p].texture_kind in texs and texs[ninfo.s_textures[p].texture_kind] == '0'):
                addit = False
        p += 1

    return addit

#checks if there are textures linked already
def check_nodes(tree):
    #["Alb", "Ao", "Mtl", "Rgh", "Emi", "Opa", "Nrm", "Emm"]
    presents = [False, False, False, False, False, False, False]
    in_socks = ["Base Color", "Metalic", "Roughness", "Emission", "Alpha", "Normal", 'Emission Strength']
    ls = tree.links

    for l in ls:
        nnm = l.to_node.name
        snm = l.to_socket.name

        if(nnm == "Principled BSDF"):
            for i, s in enumerate(in_socks):
                if(snm == s):
                    presents[i] = True

    return presents

#deletes all the nodes in a tree except for material output
def clean_tree(nodes):
    for n in nodes:
        if(n.bl_idname != 'ShaderNodeOutputMaterial'):
           nodes.remove(n)

def init_img_sockets(mat, tex_to_add, texs, blue_fix):
    link = mat.node_tree.links.new
    nodes = mat.node_tree.nodes

    #setting up starting texture sockets.
    for tx in tex_to_add:
        if texs[tx] != '0':
            if(tx == 'Alb' or tx == 'Emi' or tx == 'Trm'):
                tn = add_img_node(nodes, texs[tx])
            else:
                tn = add_img_node(nodes, texs[tx], cspace='Non-Color')
            texs[tx] = tn.outputs[0]

            #setting up normal map node...
            if(tx == 'Nrm'):
                nrm_map = nodes.new('ShaderNodeNormalMap')
                
                if(blue_fix):
                    #add 1 to blue channel
                    sep_col = nodes.new('ShaderNodeSeparateColor')
                    sep_col.location = (-300,-800)
                    comb_col = nodes.new('ShaderNodeCombineColor')
                    comb_col.location = (-250,-800)
                    comb_col.inputs[2].default_value = 1

                    link(tn.outputs[0], sep_col.inputs[0])
                    link(sep_col.outputs[0], comb_col.inputs[0])
                    link(sep_col.outputs[1], comb_col.inputs[1])
                    link(comb_col.outputs[0], nrm_map.inputs[1])
                else:
                    link(tn.outputs[0], nrm_map.inputs[1])

                texs[tx] = nrm_map.outputs[0]


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
    suffixes = [p[0] for p in texture_types if p[3] < 11]
    namebase = mname.split('.')[0]

    for s in suffixes:
        td = txdir + '\\' + namebase + '_' +s+ '.png'
        #baketd = txdir + '\\' + mname + 'Bake_' +s+ '.png'
        if (os.path.exists(td)):
            attr.append(td)
        else:
            attr.append('0')

    return attr

#takes material name and texture directory as input, outputs array of present textures. If a map its path is returned as 0
def get_attr_dict(mname, txdir):
    attr = {}
    suffixes = [p[0] for p in texture_types if p[3] < 14]
    namebase = mname.split('.')[0]

    for s in suffixes:
        td = txdir + '\\' + namebase + '_' +s+ '.png'
        #baketd = txdir + '\\' + mname + 'Bake_' +s+ '.png'
        if (os.path.exists(td)):
            attr[s] = td
        else:
            attr[s] = '0'

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

#runner for main quick mats function
def setup_mats_adv(self, context):
    mats = get_mats(context.selected_objects)
    #path to folder with the textures in
    txdir = os.path.dirname(self.properties.filepath)

    if(mats == []):
        print("none of the selected objects have materials assigned")
    else:
        for m in mats:
            attr = get_attr_dict(m.name, txdir)
            clean_tree(m.node_tree.nodes)
            
            set_mat_adv(m, attr, context.scene)
            #set_mat(m, attr, pres, context.scene.splat_tex_settings.blue_channel_fix, context.scene.splat_tex_settings.use_ao_tex)

#add item to collection
def add_node_template(coll):
    new_hand = coll.add()
    return new_hand

def del_node_template(coll, ind):
    coll.remove(ind)

class SplatTexSettings(bpy.types.PropertyGroup):
    blue_channel_fix : bpy.props.BoolProperty(name='add 1 to normal map blue channel')
    use_ao_tex : bpy.props.BoolProperty(name='use ambient occlusion textures', default = True)

#--------------------
#area for templating
#--------------------

#texture type enums
#["Alb", "Ao", "Mtl", "Rgh", "Emi", "Opa", "Nrm", "Emm"]
texture_types = [('None', 'value', '', 14),
                ('Alb', 'base colour', '', 0),
                ('Ao', 'ambient occlusion', '', 1),
                ('Mtl', 'metalness', '', 2),
                ('Rgh', 'roughness', '', 3),
                ('Emi', 'emission colour', '', 4),
                ('Opa', 'opacity', '', 5),
                ('Nrm', 'normal', '', 6),
                ('Emm', 'emission mask', '', 7),
                ('Tcl', 'team colour mask', '', 8),
                ('Thc', 'thickness', '', 9),
                ('Trm', 'transmission', '', 10),
                ('Alp', 'alpha ink colour', '', 11),
                ('Bet', 'bravo ink colour', '', 12),
                ('Nut', 'neutral ink colour', '', 13)]

bsdf_dict_vals = {}

#bsdf node inputs saved to a group for selection in ui later
def node_input_lookup():
    #getting shader nodes we want to check
    nds = bpy.types.ShaderNode.__subclasses__()
    allowed_nodes = [npp.__name__ for npp in nds if 'ShaderNodeBsdf' in npp.__name__]
    allowed_nodes += ['ShaderNodeEmission']

    if('splat_mat_nodes_checker' not in bpy.data.materials):
        bpy.data.materials.new('splat_mat_nodes_checker')
    
    mat_check = bpy.data.materials['splat_mat_nodes_checker']
    mat_check.use_nodes = True
    
    for an in allowed_nodes:
        cn = mat_check.node_tree.nodes.new(an)
        
        ninputs = [nin.name for nin in cn.inputs]
        ninputs.pop()

        bsdf_dict_vals[an] = ninputs

    #unlink material <3 
    bpy.data.materials.remove(mat_check)
    
#template enum options callback, has scene and context because it's a callback
def template_node_enum_items(self, context):
    nds = bpy.types.ShaderNode.__subclasses__()

    #get all shader nodes
    allowed_nodes = [npp.__name__[14:] for npp in nds if 'ShaderNodeBsdf' in npp.__name__]
    #add other stuff it missed
    allowed_nodes += ['Emission']

    allowed_nodes_class = [npp.__name__ for npp in nds if 'ShaderNodeBsdf' in npp.__name__]
    allowed_nodes_class += ['ShaderNodeEmission']
    #add node groups
    allowed_nodes += [nd.name for nd in context.blend_data.node_groups]
    allowed_nodes_class += [nd.name for nd in context.blend_data.node_groups]

    #NOTHING
    allowed_nodes.append('Nothing')
    allowed_nodes_class.append('None')

    #add to a list that fits the enum format
    items = []
    for i, al in enumerate(allowed_nodes):
        items.append((allowed_nodes_class[i], al, '', i))
    
    return items


#gets input sockets of node
def texture_into_items(self, context):
    #get path to this items container
    shnd = self.id_data.path_resolve(self.path_from_id().split('.')[0])

    node_in_vals = []
    if shnd.s_node in bsdf_dict_vals:
        node_in_vals = bsdf_dict_vals[shnd.s_node]
    elif shnd.s_node in context.blend_data.node_groups:
        node_in_vals = [nv.name for nv in context.blend_data.node_groups[shnd.s_node].inputs]

    items = []


    for i,niv in enumerate(node_in_vals):
        items.append((str(i),niv, '',i))

    return items

#gets outputs of node, defaults to 0. Used for texture transforms
#TODO number is 1 more than its actual place! if not default you need to decrease number by one to get the real socket

#could update the special dict to get outputs too 
#but as we're only using bsdfs rn it doesn't matter too much cuz they only have one output
def nodegroup_output_items(self, context):
    #get path to this items container
    shnd = self

    node_in_vals = []
    if shnd.s_node in context.blend_data.node_groups:
        node_in_vals = [nv.name for nv in context.blend_data.node_groups[shnd.s_node].outputs]

    items = [('sock_default', 'default', 'output socket 0', 0)]

    
    for i,niv in enumerate(node_in_vals):
        items.append((str(i),niv, '',i + 1))

    return items

class SplatTexInfo(bpy.types.PropertyGroup):
    s_req : bpy.props.BoolProperty(name='required?', default= False)
    s_value : bpy.props.FloatProperty(name='default value', description='value to use when no texture found', default=0.5, min=0, max =1)
    s_input : bpy.props.EnumProperty(items= texture_into_items, name= 'into')
    texture_kind : bpy.props.EnumProperty(items = texture_types, name = 'texture type')

class SplatNodeTemplate(bpy.types.PropertyGroup):
    s_node : bpy.props.EnumProperty(items= template_node_enum_items,name='Template')
    s_order : bpy.props.IntProperty(name='placement', min=0)
    s_is_shader : bpy.props.BoolProperty(name='Shader node?', default= True)
    s_is_add : bpy.props.BoolProperty(name='Add not mix?', default= False)
    mix_tex : bpy.props.PointerProperty(type=SplatTexInfo)
    #list of texture types used by this node
    s_textures : bpy.props.CollectionProperty(type=SplatTexInfo)

    #texture transform special
    out_texture_kind : bpy.props.EnumProperty(items = texture_types, name = 'output texture')
    out_socket : bpy.props.EnumProperty(items = nodegroup_output_items, name = 'output socket')

#------Operators + pannels------

class OT_quick_mats(bpy.types.Operator, ImportHelper):
    bl_idname = 'object.quick_mats'
    bl_label = 'setup materials quickly'

    def execute(self, context):
        setup_mats(self, context)
        return {'FINISHED'}


class OT_quick_mats_advance(bpy.types.Operator, ImportHelper):
    bl_idname = 'object.quick_mats_advance'
    bl_label = 'setup custom materials quickly'

    def execute(self, context):
        setup_mats_adv(self, context)
        return {'FINISHED'}
    
#class for adding texture processers and shader groups for auto set up
class OT_add_tex_handle(bpy.types.Operator):
    bl_idname = 'scene.add_tex_handle'
    bl_label = 'add node to automatic template'

    def execute(self, context):
        add_node_template(context.scene.splat_shade_templates)
        
        return {'FINISHED'}
    
class OT_del_tex_handle(bpy.types.Operator):
    bl_idname = 'scene.del_tex_handle'
    bl_label = 'remove node'

    v : bpy.props.IntProperty(name='delme')
    def execute(self, context):
        del_node_template(context.scene.splat_shade_templates, self.v)

        return {'FINISHED'}

class OT_add_tex(bpy.types.Operator):
    bl_idname = 'scene.add_tex'
    bl_label = 'add texture'


    v : bpy.props.IntProperty(name='addme')
    def execute(self, context):
        add_node_template(context.scene.splat_shade_templates[self.v].s_textures)

        return {'FINISHED'}

class OT_del_tex(bpy.types.Operator):
    bl_idname = 'scene.del_tex'
    bl_label = 'remove'

    v : bpy.props.IntProperty(name='delme')
    t : bpy.props.IntProperty(name='delmetoo')
    def execute(self, context):
        del_node_template(context.scene.splat_shade_templates[self.v].s_textures, self.t)
        
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

class VIEW3D_PT_Splatoon_Quick_Mats_Advance(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splatoon Tools"
    bl_label = "Quick Materials Advanced"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.operator("object.quick_mats_advance")

        row = layout.row()
        row.operator('scene.add_tex_handle')
        
        for i,p in enumerate(scene.splat_shade_templates):
            layout.separator()
            box = layout.box()
            row = box.row()
            row.prop(p, 's_node')
            pdel = row.operator('scene.del_tex_handle')
            pdel.v = i

            row = box.row()
            if(not p.s_is_shader):
                row.prop(p, 'out_socket')
                row.prop(p, 'out_texture_kind', text='as')
            else:
                if(not p.s_is_add):
                    row.prop(p.mix_tex, 's_req', text='require mix texture')
            row.alignment= 'RIGHT'
            row.prop(p, 's_order')

            col = box.column()
            crow = col.row()
            crow.prop(p, 's_is_shader')
            if(p.s_is_shader):
                crow.prop(p, 's_is_add')
                if(not p.s_is_add):
                    crow.prop(p.mix_tex, 'texture_kind', text='Mix mask')
                    crow.prop(p.mix_tex, 's_value')


            
            #texture handle zone
            ptx_add = crow.operator('scene.add_tex')
            ptx_add.v = i
            for e,t in enumerate(p.s_textures):
                box2 = box.box()
                row = box2.row()
                row.prop(t, 'texture_kind')
                row.prop(t, 's_input')
                
                row = box2.row()
                rsp = row.split(factor=0.75)
                #rspf = rsp.column_flow(columns=2)

                rsp.prop(t, 's_value')
                rsp.prop(t, 's_req')
                #row.alignment = 'RIGHT'
                rsp2 = row.column()
                rsp2.alignment = 'RIGHT'
                deltex = rsp2.operator('scene.del_tex')
                deltex.v = i
                deltex.t = e



                

def register():
    bpy.utils.register_class(VIEW3D_PT_Splatoon_Quick_Mats)
    bpy.utils.register_class(VIEW3D_PT_Splatoon_Quick_Mats_Advance)

    bpy.utils.register_class(OT_quick_mats)
    bpy.utils.register_class(OT_quick_mats_advance)
    bpy.utils.register_class(OT_add_tex_handle)
    bpy.utils.register_class(OT_del_tex_handle)
    bpy.utils.register_class(OT_add_tex)
    bpy.utils.register_class(OT_del_tex)

    bpy.utils.register_class(SplatTexSettings)
    bpy.utils.register_class(SplatTexInfo)
    bpy.utils.register_class(SplatNodeTemplate)

    bpy.types.Scene.splat_tex_settings = bpy.props.PointerProperty(type=SplatTexSettings)
    bpy.types.Scene.splat_shade_templates = bpy.props.CollectionProperty(type=SplatNodeTemplate)
    
    node_input_lookup()

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_Splatoon_Quick_Mats)
    bpy.utils.unregister_class(VIEW3D_PT_Splatoon_Quick_Mats_Advance)

    bpy.utils.unregister_class(OT_quick_mats)
    bpy.utils.unregister_class(OT_quick_mats_advance)
    bpy.utils.unregister_class(OT_add_tex_handle)
    bpy.utils.unregister_class(OT_del_tex_handle)
    bpy.utils.unregister_class(OT_add_tex)
    bpy.utils.unregister_class(OT_del_tex)

    bpy.utils.unregister_class(SplatTexSettings)
    bpy.utils.unregister_class(SplatTexInfo)  
    bpy.utils.unregister_class(SplatNodeTemplate)

    del bpy.types.Scene.splat_tex_settings
    del bpy.types.Scene.splat_shade_templates

if __name__ == '__main__':
    register()