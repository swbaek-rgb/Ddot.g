import bpy, math, os
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

form = collection('01 • Body & head')
face = collection('02 • Ears & face')
legs = collection('03 • Legs & toes')
tailcol = collection('04 • Tail')
whisk = collection('05 • Whiskers')
studio = collection('90 • Studio')
refs = collection('99 • Reference')

def mat(name, color, rough=.7):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    return m

fur = mat('Fur • warm grey brown', (.235,.195,.15))
belly = mat('Belly • soft sand', (.39,.335,.25))
skin = mat('Feet & tail • muted taupe', (.245,.192,.165))
inner = mat('Ear inner • warm clay', (.36,.265,.215))
eye = mat('Eyes • glossy black', (.007,.005,.004), .17)
nose = mat('Nose • charcoal brown', (.055,.03,.027), .38)
hair = mat('Whiskers • dark taupe', (.16,.135,.105))
ground = mat('Ground • warm ivory', (.68,.63,.54))

def assign(obj, name, material, col):
    obj.name = name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    if obj.type == 'MESH':
        for p in obj.data.polygons: p.use_smooth = True
    return obj

def uv(name, loc, scale, material, col, sub=1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc)
    ob = assign(bpy.context.object, name, material, col)
    ob.scale = scale
    if sub:
        mod = ob.modifiers.new('Soft form • editable subdivision', 'SUBSURF')
        mod.levels = sub
        mod.render_levels = sub
    return ob

def curve(name, points, radii, width, material, col):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 16
    cu.bevel_depth = width
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(points)-1)
    for p, co, radius in zip(sp.bezier_points, points, radii):
        p.co = co
        p.radius = radius
        p.handle_left_type = 'AUTO'
        p.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    col.objects.link(ob)
    cu.materials.append(material)
    return ob

body = uv('Body • rounded pear silhouette', (-.55,0,1.55), (1.24,.73,.92), fur, form)
body_mat = fur.copy(); body_mat.name = 'Body • soft underside color'
body.data.materials[0] = body_mat
nodes=body_mat.node_tree.nodes; links=body_mat.node_tree.links
tex=nodes.new('ShaderNodeTexCoord'); sep=nodes.new('ShaderNodeSeparateXYZ')
ramp=nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.17
ramp.color_ramp.elements[0].color=(*(.39,.335,.25),1)
ramp.color_ramp.elements[1].position=.44
ramp.color_ramp.elements[1].color=(*(.235,.195,.15),1)
links.new(tex.outputs['Generated'],sep.inputs[0]); links.new(sep.outputs['Z'],ramp.inputs[0])
links.new(ramp.outputs[0],nodes.get('Principled BSDF').inputs['Base Color'])

# A small ring cage makes the cheek-to-snout taper easy to revise.
rings = [(-.36,1.72,.10,.16),(-.22,1.76,.36,.44),(.10,1.77,.53,.61),
         (.45,1.72,.59,.66),(.76,1.64,.53,.58),(1.04,1.51,.40,.42),
         (1.29,1.36,.25,.26),(1.51,1.23,.13,.14),(1.73,1.15,.078,.079),
         (1.96,1.105,.058,.055),(2.08,1.105,.045,.042)]
n = 20
verts = [(x,ry*math.cos(i*2*math.pi/n),z+rz*math.sin(i*2*math.pi/n)) for x,z,ry,rz in rings for i in range(n)]
faces = []
for j in range(len(rings)-1):
    for i in range(n):
        k = j*n+i; ni=j*n+(i+1)%n
        faces.append((k,ni,ni+n,k+n))
faces += [tuple(reversed(range(n))), tuple((len(rings)-1)*n+i for i in range(n))]
me = bpy.data.meshes.new('Head • editable 20-sided profile rings')
me.from_pydata(verts, [], faces)
me.update()
head = bpy.data.objects.new('Head & long tapered snout', me)
form.objects.link(head)
assign(head, head.name, fur, form)
sub = head.modifiers.new('Smooth head • keep ring cage editable', 'SUBSURF')
sub.levels = 2; sub.render_levels = 2
uv('Nose • small rounded tip', (2.095,0,1.108), (.065,.062,.05), nose, face)

for s, side in [(-1,'L'),(1,'R')]:
    uv('Eye.'+side, (.965,s*.39,1.77), (.102,.061,.107), eye, face)
    # Ear opening faces outwards and slightly forward, like the reference.
    center = Vector((.11,s*.48,2.16))
    normal = Vector((.43,s*.90,.05)).normalized()
    rot = Vector((0,1,0)).rotation_difference(normal)
    ear = uv('Ear.'+side+' • outer', center, (.30,.105,.405), fur, face)
    ear.rotation_mode='QUATERNION'; ear.rotation_quaternion=rot
    inset = uv('Ear.'+side+' • inner', center + normal*.066 + Vector((0,0,.012)), (.236,.057,.322), inner, face)
    inset.rotation_mode='QUATERNION'; inset.rotation_quaternion=rot
    for rear in [True,False]:
        label = ('Hind' if rear else 'Front')+'.'+side
        y = s*(.49 if rear else .395)
        pts = [(-1.07,y,1.20),(-1.00,y*1.09,.64),(-.75,y*1.12,.16)] if rear else [(.48,y,1.10),(.40,y*1.10,.62),(.65,y*1.17,.145)]
        curve(label+' • leg', pts, [1.3,.84,.63], .065 if rear else .054, skin, legs)
        ankle=Vector(pts[-1]); ankle.z=.10
        uv(label+' • foot', ankle+Vector((.10,0,-.005)), (.19,.09,.055), skin, legs)
        for t in [-1,0,1]:
            start = ankle+Vector((.11,t*.045,-.01))
            end = ankle+Vector((.37-(.045 if t else 0),t*.115,-.055))
            curve(label+' • toe '+str(t+2), [start,(start+end)/2+Vector((0,0,.018)),end], [1,.75,.18], .023, skin, legs)
    for i in range(3):
        curve('Whisker.'+side+'.'+str(i+1), [(1.45,s*.13,1.29+i*.025),(1.54+i*.06,s*.40,1.34+i*.09),(1.39+i*.21,s*.79,1.31+i*.18)], [1,.65,.05], .007, hair, whisk)

curve('Tail • editable tapered curve', [(-1.60,.10,1.35),(-2.05,.18,1.10),(-2.50,.38,.82),(-2.96,.58,.69),(-3.32,.54,.72),(-3.51,.39,.82)], [1,.88,.66,.45,.23,.035], .09, skin, tailcol)

# Keep a packed photo in the file without cluttering the opening view.
reference = '/var/folders/m8/dlm_n4fd1ldfrx4khfy2jkzh0000gn/T/paseo-attachments-J7QoqI/c74a8756d361db913364ffca9113735d2d7847c9d12c5e711336417ffdb40be2.png'
if os.path.exists(reference):
    im=bpy.data.images.load(reference); im.pack()
    ob=bpy.data.objects.new('Photo reference • enable collection to view',None)
    refs.objects.link(ob); ob.empty_display_type='IMAGE'; ob.data=im
    ob.empty_display_size=5; ob.location=(0,2.5,1.8); ob.rotation_euler=(math.pi/2,0,0)
    ob.hide_render=True
    refs.hide_viewport=True

bpy.ops.mesh.primitive_plane_add(size=200)
floor=assign(bpy.context.object,'Studio floor',ground,studio)

def aim(ob, point):
    ob.rotation_euler=(Vector(point)-ob.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.object.camera_add(location=(6.5,-10,5.1))
cam=assign(bpy.context.object,'Camera • three-quarter',None,studio)
aim(cam,(-.48,0,1.18)); cam.data.type='ORTHO'; cam.data.ortho_scale=6.9
scene.camera=cam
for name, loc, power, size in [('Key', (0,-4,7),850,5),('Fill',(4,3,5),600,4),('Rim',(-4,2,6),950,3)]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    light=assign(bpy.context.object,name,None,studio)
    light.data.energy=power; light.data.shape='DISK'; light.data.size=size
    aim(light,(0,0,1))
scene.world=bpy.data.worlds.new('Studio world'); scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.59,.65,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.render.engine='CYCLES'; scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1050; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.join(OUT,'shrew_draft_v01.png')

for ob in studio.objects: ob.hide_set(True)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.shading.type='SOLID'; space.shading.color_type='MATERIAL'
            space.shading.light='STUDIO'; space.shading.show_shadows=True
            space.shading.show_cavity=True; space.shading.cavity_type='BOTH'
            space.overlay.show_floor=False
            space.overlay.show_axis_x=False; space.overlay.show_axis_y=False
            space.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
            space.region_3d.view_distance=8
            space.region_3d.view_location=Vector((-.5,0,1.25))
            space.region_3d.view_perspective='ORTHO'

notes=bpy.data.texts.new('README • Shrew draft v01')
notes.write('Simple reference-based shrew blockout.\nBody and head are separate editable meshes. Head and snout share a low-resolution ring cage with unapplied subdivision. Ears, eyes and feet are separate objects. Tail, legs, toes and whiskers are editable Bezier curves. No fur or rig at this draft stage.\nCollections 01–05 are the animal; 90 is the render studio; 99 contains the packed reference photo (hidden by default).\nFront is +X. Ground is Z=0.\n')
scene['draft_version']='v01'
scene['model_notes']='Reference-based simple shrew. Editable parts; no fur or rig.'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_draft_v01.blend'))
bpy.ops.render.render(write_still=True)
print('SHREW_DRAFT_COMPLETE', len([o for c in [form,face,legs,tailcol,whisk] for o in c.objects]))
