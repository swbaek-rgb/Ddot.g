import bpy, json, os
OUT=os.path.dirname(os.path.abspath(__file__))
for path in [os.path.join(OUT,'shrew_draft_v04.blend'),'/private/var/folders/m8/dlm_n4fd1ldfrx4khfy2jkzh0000gn/T/shrew_draft_v04_10968_autosave.blend']:
    bpy.ops.wm.open_mainfile(filepath=path)
    print('SCENE',path)
    print(json.dumps([{'name':o.name,'type':o.type,'matrix':[list(r) for r in o.matrix_world],'verts':len(o.data.vertices) if o.type=='MESH' else 0,'materials':[m.name if m else None for m in o.data.materials] if hasattr(o.data,'materials') else [],'bounds':[list(c) for c in o.bound_box] if o.type=='MESH' else []} for o in bpy.data.objects if o.type=='MESH'],ensure_ascii=False))
