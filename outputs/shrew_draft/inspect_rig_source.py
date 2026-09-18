import bpy, json, os
OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'shrew_draft_v05.blend'))
data=[]
for o in bpy.data.objects:
    d={'name':o.name,'type':o.type,'loc':list(o.location),'scale':list(o.scale),'hide':[o.hide_get(),o.hide_render],'parent':o.parent.name if o.parent else None,'mods':[(m.name,m.type) for m in o.modifiers]}
    if o.type=='MESH':
        d['vertices']=len(o.data.vertices)
        if o.name.startswith('Cylinder'):d['world_vertices']=[list(o.matrix_world@v.co) for v in o.data.vertices];d['faces']=[list(p.vertices) for p in o.data.polygons]
    if o.type=='CURVE':d['beziers']=[[list(o.matrix_world@p.co) for p in s.bezier_points] for s in o.data.splines]
    data.append(d)
with open(os.path.join(OUT,'rig_source.json'),'w') as f:json.dump(data,f,ensure_ascii=False,indent=2)
print(json.dumps(data,ensure_ascii=False))
