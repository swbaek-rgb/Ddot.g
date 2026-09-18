import bpy, math, os, json, hashlib, bmesh
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'shrew_user_saved_before_v04.blend'))
scene=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
face=bpy.data.collections['02 • Ears & face']
whisk=bpy.data.collections['05 • Whiskers']
fur=bpy.data.materials['Fur • warm grey brown']
inner=bpy.data.materials['Ear inner • warm clay']
hair=bpy.data.materials['Whiskers • dark taupe']

def protected_signature(ob):
    data={'name':ob.name,'type':ob.type,'matrix':[list(r) for r in ob.matrix_world],
          'hide':[ob.hide_viewport,ob.hide_render,ob.hide_get()],
          'collections':[c.name for c in ob.users_collection]}
    if ob.type=='MESH':
        data['vertices']=[list(v.co) for v in ob.data.vertices]
        data['faces']=[list(p.vertices) for p in ob.data.polygons]
        data['materials']=[m.name if m else None for m in ob.data.materials]
        data['modifiers']=[]
        for m in ob.modifiers:
            item={'name':m.name,'type':m.type,'show_viewport':m.show_viewport,'show_render':m.show_render}
            for prop in ['use_axis','use_clip','use_mirror_merge','merge_threshold','levels','render_levels']:
                if hasattr(m,prop):
                    v=getattr(m,prop); item[prop]=list(v) if hasattr(v,'__len__') and not isinstance(v,str) else v
            if hasattr(m,'mirror_object'): item['mirror_object']=m.mirror_object.name if m.mirror_object else None
            data['modifiers'].append(item)
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

targets=[o for o in bpy.data.objects if o.name.startswith('Ear.') or o.name.startswith('Whisker.') or o in list(whisk.objects)]
protected={o.name:protected_signature(o) for o in bpy.data.objects if o not in targets}
ear_matrices={s:bpy.data.objects['Ear.'+s+' • outer'].matrix_world.copy() for s in ['L','R']}
old_whiskers=[o.name for o in whisk.objects]
for ob in targets: bpy.data.objects.remove(ob,do_unlink=True)

def curve(name,points,radii,width,material,col):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'
    cu.resolution_u=24; cu.render_resolution_u=32; cu.bevel_depth=width; cu.bevel_resolution=3; cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(points)-1)
    for p,co,r in zip(sp.bezier_points,points,radii):
        p.co=co; p.radius=r; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'
    ob=bpy.data.objects.new(name,cu); col.objects.link(ob); cu.materials.append(material)
    return ob

def ear_outline(theta,r):
    # Broad rounded crown, narrower asymmetrical root, slight outward lean.
    z=math.cos(theta)
    x=math.sin(theta)*(1+.16*z)+.105*(z+.15)
    return x*r,z*r

for side in ['L','R']:
    matrix=ear_matrices[side]
    normal=matrix.to_quaternion()@Vector((0,1,0))
    matrix.translation+=normal*.13+Vector((0,0,.065))
    n=40
    verts=[]; faces=[]; mats=[]
    # Cross section rolls over the rim into a recessed, curved ear cup.
    front=[(.12,-.38),(.30,-.35),(.53,-.12),(.73,.30),(.86,.74),(.94,.92),(1.0,.70)]
    back=[(.12,-.98),(.34,-.91),(.60,-.75),(.84,-.42),(1.0,.27)]
    profiles=front+list(reversed(back))
    for r,depth in profiles:
        for i in range(n):
            theta=2*math.pi*i/n
            x,z=ear_outline(theta,r)
            # A soft notch where the shell meets the lower ear root.
            notch=.085*math.exp(-((theta-math.pi)/.38)**2)*r*r
            verts.append((x,depth-.14*math.sin(theta)*r,z+notch))
    for j in range(len(profiles)-1):
        for i in range(n):
            a=j*n+i; b=j*n+(i+1)%n
            faces.append((a,b,b+n,a+n)); mats.append(1 if j<4 else 0)
    faces.extend([tuple(reversed(range(n))),tuple((len(profiles)-1)*n+i for i in range(n))]); mats.extend([1,0])
    me=bpy.data.meshes.new('Ear.'+side+' • rolled rim and recessed cup')
    me.from_pydata(verts,[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new('Ear.'+side+' • detailed shell',me); face.objects.link(ob)
    ob.matrix_world=matrix; me.materials.append(fur); me.materials.append(inner)
    for p,material in zip(me.polygons,mats): p.use_smooth=True; p.material_index=material
    sub=ob.modifiers.new('Soft ear cartilage','SUBSURF'); sub.levels=2; sub.render_levels=2
    ob['notes']='Closed cup-shaped ear shell with rolled rim. Editable quad rings and subdivision.'
    # Short low relief cartilage fold; no full second outline inside the ear.
    fold=[(-.11,.27,-.66),(-.34,.20,-.37),(-.40,.18,-.01),(-.32,.36,.28)]
    curve('Ear.'+side+' • inner cartilage fold',[matrix@Vector(p) for p in fold],[1,.95,.65,.06],.015,inner,face)
    # Small rounded root fold, attached to the cup instead of a flat inset disc.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=10)
    root=bpy.context.object; root.name='Ear.'+side+' • root fold'
    for c in list(root.users_collection): c.objects.unlink(root)
    face.objects.link(root); root.data.materials.append(inner)
    root.location=matrix@Vector((.36,.39,-.57))
    root.rotation_mode='QUATERNION'; root.rotation_quaternion=matrix.to_quaternion()
    root.scale=(.040,.035,.077)
    for p in root.data.polygons:p.use_smooth=True

# Each whisker is a separately editable Bezier curve with a tapered tip.
# Spread in elevation and front/back sweep; slight left/right differences.
body=bpy.data.objects['Body + head • one continuous surface']
bodymatrix=body.matrix_world.copy()
specs=[(1.38,1.325,-.30,.86,.40),(1.43,1.29,-.09,.96,.24),
       (1.49,1.255,.17,1.02,.06),(1.44,1.235,.38,.84,-.17),
       (1.35,1.285,-.45,.72,-.055)]
new_whiskers=[]
for s,side in [(-1,'L'),(1,'R')]:
    for i,(x,z,sweep,reach,rise) in enumerate(specs):
        # Curve roots sit just inside the muzzle surface, never float above it.
        y=.183 if x<1.4 else (.15 if x<1.46 else .115)
        root=Vector((x,s*y,z))
        asym=1 if s==-1 else (.96+.018*i)
        end=Vector((x+sweep,s*(y+reach*asym),z+rise*asym))
        p1=root.lerp(end,.23)+Vector((-.018,0,.025))
        p2=root.lerp(end,.64)+Vector((-.045,0,.055 if rise>=0 else .02))
        ob=curve('Whiskers.Bezier.'+side+'.'+str(i+1).zfill(2),[bodymatrix@p for p in [root,p1,p2,end]], [1,.82,.44,.025],.0054 if i<3 else .0046,hair,whisk)
        ob['notes']='Four Bezier control points, auto handles, radius tapers to tip.'
        new_whiskers.append(ob)

after={name:protected_signature(bpy.data.objects[name]) for name in protected}
assert after==protected,'An object outside the ears/whiskers was modified'
assert len(new_whiskers)==10 and all(o.type=='CURVE' and all(s.type=='BEZIER' for s in o.data.splines) for o in new_whiskers)
assert not any(name in bpy.data.objects for name in old_whiskers)
for side in ['L','R']:
    bm=bmesh.new(); bm.from_mesh(bpy.data.objects['Ear.'+side+' • detailed shell'].data)
    assert all(e.is_manifold for e in bm.edges); bm.free()
report={'preserved_objects':list(protected),'unchanged':after==protected,'removed_whiskers':old_whiskers,'new_bezier_whiskers':len(new_whiskers),
        'user_legs':{n:len(bpy.data.objects[n].data.vertices) for n in ['Cylinder','Cylinder.001']}}
with open(os.path.join(OUT,'v04_validation.json'),'w') as f:json.dump(report,f,ensure_ascii=False,indent=2)

bpy.ops.object.select_all(action='DESELECT')
ear=bpy.data.objects['Ear.L • detailed shell']; ear.select_set(True); bpy.context.view_layer.objects.active=ear
scene['draft_version']='v04'
notes=bpy.data.texts.new('README • Shrew draft v04')
notes.write('v04: Replaced old oval ear meshes with cupped shells, rolled rims, inner cartilage and small root folds. Replaced all six old whiskers with ten tapered Bezier curves, five per side. All other objects including user-made Cylinder and Cylinder.001 legs and their Mirror modifiers were preserved and verified unchanged. Source is the latest user-saved v03 file.\n')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='CONSOLE':area.type='VIEW_3D'
        if area.type=='VIEW_3D':
            space=next((s for s in area.spaces if s.type=='VIEW_3D'),None)
            if space is None:continue
            space.shading.type='SOLID'; space.shading.color_type='MATERIAL'
            space.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
            space.region_3d.view_location=Vector((-.2,0,1.3)); space.region_3d.view_distance=6.7
            space.region_3d.view_perspective='ORTHO'
scene.render.filepath=os.path.join(OUT,'shrew_draft_v04.png')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_draft_v04.blend'))
bpy.ops.render.render(write_still=True)
# Extra face detail for inspection, leaving the saved main camera unchanged.
cam=scene.camera; cam.location=(4.6,-8,4.7)
cam.rotation_euler=(Vector((.65,-.10,1.85))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=3.35
scene.render.filepath=os.path.join(OUT,'shrew_draft_v04_detail.png')
bpy.ops.render.render(write_still=True)
print('V04_VERIFIED',json.dumps(report,ensure_ascii=False))
