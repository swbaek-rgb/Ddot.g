import bpy, os, json, hashlib, math
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'shrew_rig_before_toon_v07.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['SHREW_RIG • Pose Mode']

def signature():
    data={}
    for ob in bpy.data.objects:
        if ob.type in {'LIGHT','CAMERA'}:continue
        d={'matrix':[list(r) for r in ob.matrix_world],'parent':ob.parent.name if ob.parent else None,
           'mods':[(m.name,m.type,m.show_viewport,m.show_render) for m in ob.modifiers]}
        if ob.type=='MESH':
            d['verts']=[list(v.co) for v in ob.data.vertices]
            d['faces']=[list(p.vertices) for p in ob.data.polygons]
            d['weights']=[[(g.group,g.weight) for g in v.groups] for v in ob.data.vertices]
        if ob.type=='ARMATURE':
            d['bones']=[(b.name,list(b.head_local),list(b.tail_local),b.parent.name if b.parent else None) for b in ob.data.bones]
            d['pose']=[(p.name,[list(r) for r in p.matrix_basis],[(c.name,c.type,c.influence) for c in p.constraints]) for p in ob.pose.bones]
        if ob.type=='CURVE':d['points']=[[(list(p.co),list(p.handle_left),list(p.handle_right),p.radius) for p in s.bezier_points] for s in ob.data.splines]
        data[ob.name]=d
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
before=signature()

# One editable shared node group controls the two light levels on every surface.
group=bpy.data.node_groups.new('TOON • Two light levels','ShaderNodeTree')
for name,typ,default in [('Base Color','NodeSocketColor',(.3,.12,.04,1)),('Threshold','NodeSocketFloat',.48),('Shadow Strength','NodeSocketFloat',.30),('Light Strength','NodeSocketFloat',1.65)]:
    sock=group.interface.new_socket(name=name,in_out='INPUT',socket_type=typ)
    sock.default_value=default
    if typ=='NodeSocketFloat':sock.min_value=0;sock.max_value=4 if name=='Light Strength' else 1
group.interface.new_socket(name='Shader',in_out='OUTPUT',socket_type='NodeSocketShader')
n=group.nodes;l=group.links
inp=n.new('NodeGroupInput');inp.location=(-680,140)
diff=n.new('ShaderNodeBsdfDiffuse');diff.location=(-680,-140);diff.inputs['Color'].default_value=(1,1,1,1)
diff.inputs['Roughness'].default_value=0;diff.label='Read the actual key / fill / rim lights'
rgb=n.new('ShaderNodeShaderToRGB');rgb.location=(-460,-120)
l.new(diff.outputs[0],rgb.inputs[0])
bw=n.new('ShaderNodeRGBToBW');bw.location=(-270,-120);l.new(rgb.outputs[0],bw.inputs[0])
step=n.new('ShaderNodeMath');step.operation='GREATER_THAN';step.location=(-80,-80);step.label='Hard two-tone boundary'
l.new(bw.outputs[0],step.inputs[0]);l.new(inp.outputs['Threshold'],step.inputs[1])
tone=n.new('ShaderNodeMixRGB');tone.blend_type='MIX';tone.location=(120,-40);tone.label='Exactly two illumination levels'
l.new(step.outputs[0],tone.inputs[0]);l.new(inp.outputs['Shadow Strength'],tone.inputs[1]);l.new(inp.outputs['Light Strength'],tone.inputs[2])
color=n.new('ShaderNodeMixRGB');color.blend_type='MULTIPLY';color.inputs[0].default_value=1;color.location=(330,150)
l.new(inp.outputs['Base Color'],color.inputs[1]);l.new(tone.outputs[0],color.inputs[2])
em=n.new('ShaderNodeEmission');em.location=(550,150);em.inputs['Strength'].default_value=1
l.new(color.outputs[0],em.inputs['Color'])
out=n.new('NodeGroupOutput');out.location=(750,150);l.new(em.outputs[0],out.inputs[0])

animal=[o for o in bpy.data.objects if o.type in {'MESH','CURVE'} and o.name!='Studio floor' and not o.name.startswith('WGT_')]
mapping={}
for ob in animal:
    for i,old in enumerate(ob.data.materials):
        if old is None or 'Eyes' in old.name:continue
        if old.name not in mapping:
            mat=old.copy();mat.name='TOON • '+old.name
            nt=mat.node_tree
            bs=next((x for x in nt.nodes if x.type=='BSDF_PRINCIPLED'),None)
            output=next((x for x in nt.nodes if x.type=='OUTPUT_MATERIAL'),None)
            if not output:output=nt.nodes.new('ShaderNodeOutputMaterial')
            toon=nt.nodes.new('ShaderNodeGroup');toon.node_tree=group;toon.name='TOON CONTROLS';toon.label='Two tones · Eevee · edit threshold';toon.location=(840,220)
            toon.inputs['Threshold'].default_value=.48
            toon.inputs['Shadow Strength'].default_value=.30
            toon.inputs['Light Strength'].default_value=1.65
            if bs:
                base=bs.inputs['Base Color']
                if base.is_linked:nt.links.new(base.links[0].from_socket,toon.inputs['Base Color'])
                else:toon.inputs['Base Color'].default_value=base.default_value
            else:toon.inputs['Base Color'].default_value=old.diffuse_color
            output.location=(1120,220)
            nt.links.new(toon.outputs[0],output.inputs['Surface'])
            mat['toon_help']='Eevee only. TOON CONTROLS: Threshold moves the hard boundary. Shadow/Light Strength change the two levels. Original nose gradient remains connected.'
            mapping[old.name]=mat
        ob.data.materials[i]=mapping[old.name]

lights=bpy.data.collections.new('91 • THREE POINT LIGHTS');scene.collection.children.link(lights)
lighting=[('Key','01 • KEY — main / left',(-3.0,-4.5,6.0),1050,3.0),
          ('Fill','02 • FILL — soft / right',(4.2,0.5,3.7),160,4.0),
          ('Rim','03 • RIM — back edge',(-2.5,3.5,4.7),1000,2.0)]
for oldname,name,loc,power,size in lighting:
    ob=bpy.data.objects[oldname];ob.name=name
    for col in list(ob.users_collection):col.objects.unlink(ob)
    lights.objects.link(ob)
    ob.location=loc;ob.rotation_euler=(Vector((-.55,0,1.3))-ob.location).to_track_quat('-Z','Y').to_euler()
    ob.data.type='AREA';ob.data.shape='DISK';ob.data.energy=power;ob.data.size=size;ob.data.color=(1,1,1)
    if hasattr(ob.data,'use_shadow_jitter'):ob.data.use_shadow_jitter=False
    ob.hide_render=False;ob.hide_set(False)
    ob['role']=oldname

scene.world=scene.world.copy();scene.world.name='TOON • low ambient studio'
bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.5,.55,.65,1);bg.inputs['Strength'].default_value=.04
scene.render.engine='BLENDER_EEVEE'
scene.eevee.taa_render_samples=128
scene.eevee.taa_samples=64
scene.eevee.use_shadow_jitter_viewport=False
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
scene.view_settings.exposure=0;scene.view_settings.gamma=1
if hasattr(scene.render,'film_transparent'):scene.render.film_transparent=False

# Keep the backdrop comfortably exposed under Standard display transform.
floor=bpy.data.objects['Studio floor']
ground=floor.data.materials[0].copy();ground.name='TOON studio • matte warm backdrop'
floor.data.materials[0]=ground
gbs=next(n for n in ground.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
gbs.inputs['Base Color'].default_value=(.09,.08,.065,1)
gbs.inputs['Roughness'].default_value=1
gbs.inputs['Specular IOR Level'].default_value=0
gbs.inputs['Emission Color'].default_value=(.26,.24,.21,1)
gbs.inputs['Emission Strength'].default_value=.6

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='CONSOLE':area.type='VIEW_3D'
        if area.type=='VIEW_3D':
            sp=next((s for s in area.spaces if s.type=='VIEW_3D'),None)
            if sp:
                sp.shading.type='RENDERED';sp.shading.use_scene_lights=True;sp.shading.use_scene_world=True
                sp.overlay.show_extras=False
                sp.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
                sp.region_3d.view_location=Vector((-.5,0,1.25));sp.region_3d.view_distance=7.8
                sp.region_3d.view_perspective='ORTHO'

assert signature()==before,'Model geometry, pose or rig changed'
assert len([o for o in scene.objects if o.type=='LIGHT'])==3
notes='''투톤 툰 셰이딩 / 3점 조명 — v07

렌더 엔진: Eevee. 파일을 열면 Rendered 미리보기로 설정되어 있습니다.
밝은 면과 그림자 면은 GREATER THAN 임계값으로 두 단계만 사용합니다.
코끝의 기존 갈색 그라데이션은 바탕색으로 유지합니다. 눈은 기존 검은색 광택을 유지합니다.

91 • THREE POINT LIGHTS 컬렉션
KEY: 주조명 / 1050 W
FILL: 보조조명 / 160 W
RIM: 뒤쪽 윤곽 조명 / 1000 W

재질의 TOON CONTROLS 노드:
Threshold: 높이면 그림자 영역이 넓어집니다.
Shadow Strength: 그림자 톤의 밝기.
Light Strength: 밝은 톤의 밝기.

기존 리그, 현재 포즈, 모델 메시, 가중치와 코 색 그라데이션을 보존했습니다.
색 경계를 보려면 Z → Rendered를 사용하세요. Solid 모드에서는 툰 효과가 보이지 않습니다.
Shader to RGB를 사용하므로 Cycles로 전환하면 이 툰 재질을 사용할 수 없습니다.
'''
txt=bpy.data.texts.new('START HERE • 투톤과 3점 조명');txt.write(notes)
with open(os.path.join(OUT,'투톤_조명_사용법_v07.txt'),'w') as f:f.write(notes)
scene['draft_version']='v07_toon';scene['toon_notes']='Two lighting levels; nose albedo gradient preserved; Eevee renderer.'
report={'geometry_and_rig_unchanged':True,'source_signature':before,'engine':scene.render.engine,
        'toon_materials':[m.name for m in mapping.values()],'lighting':[{'name':o.name,'power':o.data.energy,'location':list(o.location)} for o in lights.objects]}
with open(os.path.join(OUT,'toon_v07_validation.json'),'w') as f:json.dump(report,f,ensure_ascii=False,indent=2)
scene.render.filepath=os.path.join(OUT,'shrew_toon_v07.png')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_toon_v07.blend'))
bpy.ops.render.render(write_still=True)
print('TOON_V07_VERIFIED',json.dumps(report,ensure_ascii=False))
