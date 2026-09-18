import bpy, os, json, datetime, bmesh

OUT='/Users/admin/Documents/github/Ddot.g/outputs/shrew_draft'
scene=bpy.context.scene
assert 'shrew_draft_v02' in bpy.data.filepath, 'Expected the currently open v02 document'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_before_v03_'+stamp+'.blend'),copy=True)
col=bpy.data.collections['03 • Legs & toes']
report={}
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for ob in list(col.objects):
    if 'claw' in ob.name:
        bpy.data.objects.remove(ob,do_unlink=True)
        continue
    if ob.type!='MESH': continue
    old_vertices=len(ob.data.vertices)
    for modifier in list(ob.modifiers): ob.modifiers.remove(modifier)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active=ob
    tris=sum(len(p.vertices)-2 for p in ob.data.polygons)
    dec=ob.modifiers.new('Low-poly silhouette','DECIMATE')
    dec.ratio=min(1,460/tris)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    for p in ob.data.polygons: p.use_smooth=False
    ob.name=ob.name.replace('continuous leg & foot','low-poly leg & foot')
    bm=bmesh.new(); bm.from_mesh(ob.data)
    assert all(e.is_manifold for e in bm.edges),ob.name
    bm.free()
    report[ob.name]={'before_vertices':old_vertices,'after_vertices':len(ob.data.vertices),'faces':len(ob.data.polygons)}

bpy.ops.object.select_all(action='DESELECT')
body=bpy.data.objects.get('Body + head • one continuous surface')
body.select_set(True); bpy.context.view_layer.objects.active=body
scene['draft_version']='v03'
scene['model_notes']='v02 body preserved. Low-poly legs and feet; no leg subdivision or separate claws.'
notes=bpy.data.texts.new('README • Shrew draft v03')
notes.write('v03: Legs and feet reduced to approximately 460 triangles each, flat shading, no subdivision. Small separate claws removed. The connected wide body/head and other objects are preserved from the live v02 scene. The previous unsaved scene was backed up before editing.\n'+json.dumps(report,indent=2))
scene.render.filepath=os.path.join(OUT,'shrew_draft_v03.png')
with open(os.path.join(OUT,'v03_validation.json'),'w') as f: json.dump(report,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_draft_v03.blend'))
print('V03_LOW_POLY_COMPLETE',report)
