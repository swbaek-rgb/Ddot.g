import bpy, os, json, hashlib
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'shrew_user_saved_before_v05.blend'))
scene=bpy.context.scene
body=bpy.data.objects['Body + head • one continuous surface']
legs=[bpy.data.objects[n] for n in ['Cylinder','Cylinder.001']]

def geometry_signature():
    dg=bpy.context.evaluated_depsgraph_get()
    data={}
    for ob in bpy.data.objects:
        rec={'type':ob.type,'matrix':[list(r) for r in ob.matrix_world]}
        if ob.type=='MESH':
            ev=ob.evaluated_get(dg); me=ev.to_mesh()
            rec['vertices']=[list(v.co) for v in me.vertices]
            rec['faces']=[list(p.vertices) for p in me.polygons]
            ev.to_mesh_clear()
            rec['base_vertices']=[list(v.co) for v in ob.data.vertices]
            rec['mods']=[(m.name,m.type,m.show_viewport,m.show_render) for m in ob.modifiers]
        elif ob.type=='CURVE':
            rec['splines']=[[(list(p.co),list(p.handle_left),list(p.handle_right),p.radius) for p in s.bezier_points] for s in ob.data.splines]
            rec['bevel']=ob.data.bevel_depth
        data[ob.name]=rec
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

before=geometry_signature()
BROWN=(.145,.058,.022,1)
DARK=(.021,.006,.0025,1)
LEG=(.115,.041,.016,1)

def material(name,color,texture=True):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=color
    nodes=m.node_tree.nodes; links=m.node_tree.links
    bs=nodes.get('Principled BSDF'); bs.location=(520,100)
    bs.inputs['Base Color'].default_value=color
    bs.inputs['Roughness'].default_value=.72
    bs.inputs['Specular IOR Level'].default_value=.28
    out=nodes.get('Material Output'); out.location=(800,100)
    coord=nodes.new('ShaderNodeTexCoord'); coord.name='Body-relative coordinates'; coord.object=body; coord.location=(-900,100)
    if texture:
        noise=nodes.new('ShaderNodeTexNoise'); noise.name='Fine skin grain'; noise.label='Fine grain — bump only'; noise.location=(-620,-200)
        noise.inputs['Scale'].default_value=105
        noise.inputs['Detail'].default_value=2
        noise.inputs['Roughness'].default_value=.62
        links.new(coord.outputs['Object'],noise.inputs['Vector'])
        bump=nodes.new('ShaderNodeBump'); bump.name='Subtle surface texture'; bump.location=(220,-120)
        bump.inputs['Strength'].default_value=.16; bump.inputs['Distance'].default_value=.006
        links.new(noise.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs['Normal'],bs.inputs['Normal'])
        rough=nodes.new('ShaderNodeMapRange'); rough.location=(-30,-310); rough.name='Matte grain roughness'
        rough.inputs['From Min'].default_value=0; rough.inputs['From Max'].default_value=1
        rough.inputs['To Min'].default_value=.64; rough.inputs['To Max'].default_value=.79
        links.new(noise.outputs['Fac'],rough.inputs['Value']); links.new(rough.outputs[0],bs.inputs['Roughness'])
    return m,coord,bs

m,coord,bs=material('Body • brown / dark nose gradient',BROWN)
nodes=m.node_tree.nodes; links=m.node_tree.links
sep=nodes.new('ShaderNodeSeparateXYZ'); sep.location=(-680,250); sep.name='Along muzzle X'
links.new(coord.outputs['Object'],sep.inputs[0])
amount=nodes.new('ShaderNodeMapRange'); amount.location=(-470,260)
amount.name='Muzzle-only gradient'; amount.label='Brown until X=1.10; dark nose at X=2.08'
amount.clamp=True; amount.interpolation_type='SMOOTHERSTEP'
amount.inputs['From Min'].default_value=1.10; amount.inputs['From Max'].default_value=2.08
amount.inputs['To Min'].default_value=0; amount.inputs['To Max'].default_value=1
links.new(sep.outputs['X'],amount.inputs['Value'])
mix=nodes.new('ShaderNodeMixRGB'); mix.location=(-130,180); mix.name='Brown to dark brown'; mix.blend_type='MIX'
mix.inputs[1].default_value=BROWN; mix.inputs[2].default_value=DARK
links.new(amount.outputs[0],mix.inputs[0]); links.new(mix.outputs[0],bs.inputs['Base Color'])
body.data.materials.clear(); body.data.materials.append(m)
body['color_notes']='Uniform brown through head and body. Gradient only along muzzle X=1.10..2.08, darkest at nose tip.'

legmat,_,_=material('Legs & feet • textured brown',LEG)
for ob in legs:
    ob.data.materials.clear(); ob.data.materials.append(legmat)
    ob['material_notes']='Procedural fine bump and roughness texture. Geometry and Mirror retained.'

# Match the fur-covered outer ear rim to the head; leave the inner ear material.
rim,_,_=material('Ear outer • matching brown',BROWN)
for ob in bpy.data.objects:
    if ob.name.startswith('Ear.') and hasattr(ob.data,'materials'):
        for i,mat in enumerate(ob.data.materials):
            if mat and mat.name=='Fur • warm grey brown': ob.data.materials[i]=rim

assert geometry_signature()==before,'Geometry changed during material-only revision'
report={'geometry_unchanged':True,'geometry_signature':before,
        'legs':{o.name:{'base_vertices':len(o.data.vertices),'modifiers':[mod.type for mod in o.modifiers],'material':legmat.name} for o in legs},
        'gradient_range_x':[1.1,2.08],'head_body_base_color_linear':BROWN,'nose_color_linear':DARK}
with open(os.path.join(OUT,'v05_validation.json'),'w') as f: json.dump(report,f,indent=2)

scene['draft_version']='v05'
notes=bpy.data.texts.new('README • Shrew draft v05')
notes.write('Material-only revision from the latest user-saved v04. All object geometry, transforms, curve control points and evaluated mesh shapes were compared and preserved. Legs and feet use brown with procedural fine grain in bump and roughness. Body base color is constant brown up to local X=1.10, then smoothly transitions to dark brown at the nose tip X=2.08. No belly or head-to-body color gradient. Ear rim matches brown; inner ear unchanged. No external texture files required.\n')

# Open with material preview so the shader gradient is visible immediately.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='CONSOLE':area.type='VIEW_3D'
        if area.type=='VIEW_3D':
            space=next((s for s in area.spaces if s.type=='VIEW_3D'),None)
            if space:
                space.shading.type='MATERIAL'
                space.shading.use_scene_world=False; space.shading.use_scene_lights=False
scene.render.filepath=os.path.join(OUT,'shrew_draft_v05.png')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_draft_v05.blend'))
bpy.ops.render.render(write_still=True)
cam=scene.camera
cam.location=(2,-9,3.5); target=Vector((.35,0,1.6))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=4.65
scene.render.filepath=os.path.join(OUT,'shrew_draft_v05_color_detail.png')
bpy.ops.render.render(write_still=True)
print('V05_VERIFIED',json.dumps(report))
