import bpy, os, json
OUT=os.path.dirname(os.path.abspath(__file__))
def read(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    result={}
    for name in ['Cylinder','Cylinder.001']:
        ob=bpy.data.objects.get(name)
        if ob is None:return None
        result[name]={'vertices':[list(v.co) for v in ob.data.vertices], 'faces':[list(p.vertices) for p in ob.data.polygons],
            'matrix':[list(r) for r in ob.matrix_world], 'materials':[m.name if m else None for m in ob.data.materials],
            'modifiers':[(m.type,list(m.use_axis),m.mirror_object.name if m.mirror_object else None) for m in ob.modifiers if m.type=='MIRROR']}
    return result
a=read(os.path.join(OUT,'shrew_draft_v03.blend'))
b=read(os.path.join(OUT,'shrew_draft_v04.blend'))
print('USER_SAVED_LEGS_MATCH_V04', a is not None and a==b)
assert a is not None and a==b,'Newly saved user legs differ from v04'
