import bpy, math, os, json
from mathutils import Vector

OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'shrew_draft_v01.blend'))
scene=bpy.context.scene
form=bpy.data.collections['01 • Body & head']
legs=bpy.data.collections['03 • Legs & toes']
studio=bpy.data.collections['90 • Studio']
skin=bpy.data.materials['Feet & tail • muted taupe']
bodymat=bpy.data.materials['Body • soft underside color']

for ob in list(form.objects)+list(legs.objects):
    bpy.data.objects.remove(ob,do_unlink=True)

# Single low-resolution, continuous quad surface from rump to nose.
# The widest Y radius grows from 0.73 to 1.02, preserving the height.
rings=[(-1.79,1.52,.065,.075),(-1.73,1.54,.30,.34),
       (-1.55,1.56,.63,.63),(-1.29,1.57,.85,.80),
       (-.96,1.56,.985,.895),(-.60,1.55,1.02,.92),
       (-.25,1.56,.955,.885),(.05,1.60,.80,.80),
       (.29,1.65,.665,.72),(.49,1.68,.595,.65),
       (.76,1.64,.53,.58),(1.04,1.51,.40,.42),
       (1.29,1.36,.25,.26),(1.51,1.23,.13,.14),
       (1.73,1.15,.078,.079),(1.96,1.105,.058,.055),
       (2.08,1.105,.045,.042)]
n=24
verts=[(x,ry*math.cos(2*math.pi*i/n),z+rz*math.sin(2*math.pi*i/n)) for x,z,ry,rz in rings for i in range(n)]
faces=[]
for j in range(len(rings)-1):
    for i in range(n):
        a=j*n+i; b=j*n+(i+1)%n
        faces.append((a,b,b+n,a+n))
faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
mesh=bpy.data.meshes.new('Continuous body-head • editable quad ring cage')
mesh.from_pydata(verts,[],faces); mesh.update()
body=bpy.data.objects.new('Body + head • one continuous surface',mesh)
form.objects.link(body); mesh.materials.append(bodymat)
for p in mesh.polygons: p.use_smooth=True
sub=body.modifiers.new('Smooth silhouette • editable cage','SUBSURF')
sub.levels=2; sub.render_levels=2
body['revision']='v02: wider Y silhouette; connected body and head'
for s,side in [(-1,'L'),(1,'R')]:
    for ob in bpy.data.collections['02 • Ears & face'].objects:
        if ob.name.startswith('Ear.'+side):
            ob.location+=Vector((.06,s*.12,.04))

def move_to(ob,col):
    for c in list(ob.users_collection): c.objects.unlink(ob)
    col.objects.link(ob)

def ellipsoid(name,location,scale,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=location)
    ob=bpy.context.object; ob.name=name; ob.scale=scale
    move_to(ob,legs); ob.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in ob.data.polygons: p.use_smooth=True
    return ob

def tube(name,coords,radii,material):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'
    cu.resolution_u=12; cu.bevel_depth=1; cu.bevel_resolution=3; cu.use_fill_caps=True
    spline=cu.splines.new('BEZIER'); spline.bezier_points.add(len(coords)-1)
    for p,co,r in zip(spline.bezier_points,coords,radii):
        p.co=co; p.radius=r; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'
    ob=bpy.data.objects.new(name,cu); legs.objects.link(ob); cu.materials.append(material)
    return ob

claw=skin.copy(); claw.name='Claws • subdued horn'
claw.diffuse_color=(.22,.18,.13,1)
claw.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=claw.diffuse_color

for s,side in [(-1,'L'),(1,'R')]:
    for hind in [True,False]:
        label=('Hind' if hind else 'Front')+'.'+side
        if hind:
            # Fur hides the proximal knee; visible shank returns to a low hock.
            pts=[(-1.03,s*.66,1.32),(-.82,s*.79,.95),(-1.02,s*.85,.43),(-.91,s*.88,.16),(-.79,s*.90,.085)]
            radii=[.125,.087,.052,.044,.048]
            palm=Vector((-.73,s*.905,.078)); spread=.19; lengths=[.24,.35,.32,.22]
        else:
            pts=[(.42,s*.46,1.48),(.40,s*.555,1.10),(.36,s*.62,.75),(.49,s*.64,.48),(.66,s*.655,.16),(.77,s*.68,.085)]
            radii=[.105,.084,.067,.048,.037,.043]
            palm=Vector((.81,s*.69,.076)); spread=.175; lengths=[.20,.29,.275,.205]
        parts=[tube(label+' • articulated leg',pts,radii,skin)]
        parts.append(ellipsoid(label+' • low palm',palm,(.105,.073,.045),skin))
        # Four long, distinct toes: unequal lengths, splayed with low knuckles.
        for i in range(4):
            t=(i-1.5)/1.5
            root=palm+Vector((.04,t*.046,0))
            end=palm+Vector((lengths[i],t*spread+s*.035,-.041))
            joint=root.lerp(end,.50)+Vector((0,0,.011))
            distal=root.lerp(end,.84)+Vector((0,0,-.006))
            parts.append(tube(label+' • toe '+str(i+1),[root,joint,distal,end],[.028,.024,.018,.011],skin))
            direction=(end-distal).normalized()
            tip=end+Vector((.044,direction.y*.035,-.015))
            tube(label+' • claw '+str(i+1),[end,end.lerp(tip,.55)+Vector((0,0,.007)),tip],[.012,.009,.0015],claw)
        # Fuse the ankle, palm and toe roots so there are no stuck-on pads or gaps.
        bpy.ops.object.select_all(action='DESELECT')
        for ob in parts: ob.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.join()
        ob=bpy.context.object; ob.name=label+' • continuous leg & foot'
        remesh=ob.modifiers.new('Fuse foot and ankle','REMESH')
        remesh.mode='VOXEL'; remesh.voxel_size=.009
        bpy.ops.object.modifier_apply(modifier=remesh.name)
        smooth=ob.modifiers.new('Soften joints','SMOOTH'); smooth.factor=.55; smooth.iterations=3
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        decimate=ob.modifiers.new('Simple editable leg mesh','DECIMATE'); decimate.ratio=.38
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        for p in ob.data.polygons: p.use_smooth=True
        sub=ob.modifiers.new('Gentle finish','SUBSURF'); sub.levels=1; sub.render_levels=1

def aim(ob,target):
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

cam=scene.camera
cam.location=(5.1,-10,4.4); aim(cam,(-.45,0,1.15))
cam.data.ortho_scale=6.7
bpy.ops.object.camera_add(location=(-.52,0,10))
top=bpy.context.object; top.name='Camera • Top / Y-width check'
move_to(top,studio); top.rotation_euler=(0,0,0); top.data.type='ORTHO'; top.data.ortho_scale=6.6
top.hide_set(True)
scene.camera=cam
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
            area.spaces.active.region_3d.view_location=Vector((-.5,0,1.22))
            area.spaces.active.region_3d.view_distance=8
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); bpy.context.view_layer.objects.active=body
for text in list(bpy.data.texts): bpy.data.texts.remove(text)
notes=bpy.data.texts.new('README • Shrew draft v02')
notes.write('v02\nBody Y radius increased from 0.73 to 1.02 before subdivision. Body, head and snout now form ONE connected, closed mesh with an editable quad ring cage and unapplied subdivision.\nLegs now have knee/elbow and hock/wrist transitions. Each leg, palm and four splayed toes is a continuous mesh. Claws remain separate.\nTop camera provided for width review. Reference photo remains packed. v01 is preserved. No fur or rig.\n')
scene['draft_version']='v02'
scene['model_notes']='Broader body in Y, continuous body/head, articulated legs and low splayed toes.'
scene.render.filepath=os.path.join(OUT,'shrew_draft_v02.png')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_draft_v02.blend'))
bpy.ops.render.render(write_still=True)
scene.camera=top
scene.render.filepath=os.path.join(OUT,'shrew_draft_v02_top.png')
bpy.ops.render.render(write_still=True)

# Count connected components and open edges in the actual saved model topology.
def topology(ob):
    me=ob.data; neighbors=[[] for v in me.vertices]
    for e in me.edges:
        a,b=e.vertices; neighbors[a].append(b); neighbors[b].append(a)
    seen=set(); count=0
    for v in range(len(neighbors)):
        if v in seen: continue
        count+=1; stack=[v]; seen.add(v)
        while stack:
            for other in neighbors[stack.pop()]:
                if other not in seen: seen.add(other); stack.append(other)
    import bmesh
    bm=bmesh.new(); bm.from_mesh(me)
    nonmanifold=sum(not e.is_manifold for e in bm.edges); bm.free()
    return {'components':count,'nonmanifold_edges':nonmanifold,'vertices':len(me.vertices)}
report={ob.name:topology(ob) for ob in [body]+[o for o in legs.objects if 'continuous leg' in o.name]}
assert all(v['components']==1 and v['nonmanifold_edges']==0 for v in report.values()),report
with open(os.path.join(OUT,'v02_validation.json'),'w') as f: json.dump(report,f,indent=2)
print('SHREW_V02_VERIFIED',report)
