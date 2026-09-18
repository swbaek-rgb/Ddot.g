import bpy, math, os, json
from mathutils import Vector, Matrix
OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'shrew_before_rig_v06.blend'))
scene=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
animal=[o for o in bpy.data.objects if o.type in {'MESH','CURVE'} and o.name!='Studio floor']
body=bpy.data.objects['Body + head • one continuous surface']
tail=next(o for o in animal if o.name.startswith('Tail'))

def world_vertices(ob):
    bpy.context.view_layer.update()
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh()
    vs=[ev.matrix_world@v.co for v in me.vertices]; ev.to_mesh_clear(); return vs
before={o.name:world_vertices(o) for o in animal}

def active(ob):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob

# Keep the displayed user geometry exactly, while making both sides independent.
# Legs use their existing evaluated subdivision surface as the deformation mesh.
for ob in animal:
    if ob.type!='MESH':continue
    active(ob)
    if ob.name.startswith('Cylinder'):
        for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    else:
        for mod in list(ob.modifiers):
            if mod.type=='MIRROR':
                bpy.ops.object.modifier_move_to_index(modifier=mod.name,index=0)
                bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

def newcol(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
rigcol=newcol('00 • SHREW RIG — select controls')
widgets=newcol('98 • Rig widgets'); widgets.hide_render=True
arm=bpy.data.armatures.new('Shrew animation skeleton')
rig=bpy.data.objects.new('SHREW_RIG • Pose Mode',arm);rigcol.objects.link(rig)
rig.show_in_front=True;arm.display_type='OCTAHEDRAL'
active(rig);bpy.ops.object.mode_set(mode='EDIT')

def bone(name,head,tail,parent=None,deform=True,connect=False):
    b=arm.edit_bones.new(name);b.head=head;b.tail=tail;b.use_deform=deform
    if parent:b.parent=arm.edit_bones[parent];b.use_connect=connect
    return b

bone('ROOT',(0,0,0),(0,0,.32),deform=False)
bone('BODY',(-.85,0,1.35),(-.30,0,1.35),'ROOT')
bone('SPINE',(-.80,0,1.63),(-.10,0,1.66),'BODY')
bone('HEAD',(-.10,0,1.66),(1.08,0,1.46),'SPINE')
for s,side in [(-1,'L'),(1,'R')]:
    bone('EAR.'+side,(.16,s*.65,1.99),(.16,s*.73,2.53),'HEAD')

tailpts=[tail.matrix_world@p.co for p in tail.data.splines[0].bezier_points]
for i in range(len(tailpts)-1):
    bone('TAIL.'+str(i+1).zfill(2),tailpts[i],tailpts[i+1],'BODY' if i==0 else 'TAIL.'+str(i).zfill(2),True,i>0)

legdefs={}
for kind,x,ay,kx,kz in [('front',-.3065383,.23317322,-.353,.535),('hind',-1.32895958,.309847,-1.382788,.49423945)]:
    for s,side in [(-1,'L'),(1,'R')]:
        key=kind+'.'+side
        hip=Vector((x,s*ay,.96014774));knee=Vector((kx,s*ay,kz));ankle=Vector((x,s*ay,.11170089));toe=ankle+Vector((.16,0,-.055))
        upper='DEF_upper_'+key;lower='DEF_lower_'+key;foot='DEF_foot_'+key;ctrl='FOOT_IK_'+key;pole='KNEE_'+key
        bone(upper,hip,knee,'SPINE' if kind=='front' else 'BODY')
        bone(lower,knee,ankle,upper,True,True)
        bone(foot,ankle,toe,lower,True,True)
        bone(ctrl,ankle,toe,'ROOT',False)
        polepos=knee+Vector((-.70,0,0))
        bone(pole,polepos,polepos+Vector((0,0,.13)),'ROOT',False)
        legdefs[key]={'hip':hip,'knee':knee,'ankle':ankle,'upper':upper,'lower':lower,'foot':foot,'ctrl':ctrl,'pole':pole}
bpy.ops.object.mode_set(mode='OBJECT')

main=arm.collections.new('01 • Body / head / ears / tail')
feet=arm.collections.new('02 • Foot IK controls')
poles=arm.collections.new('03 • Knee direction controls')
deform=arm.collections.new('90 • Leg deformation bones')
for b in arm.bones:
    c=deform if b.name.startswith('DEF_') else feet if b.name.startswith('FOOT_') else poles if b.name.startswith('KNEE_') else main
    c.assign(b)
    b.color.palette='THEME03' if b.name.endswith('.L') else 'THEME01' if b.name.endswith('.R') else 'THEME04'
deform.is_visible=False

for pb in rig.pose.bones:
    pb.rotation_mode='XYZ';pb.lock_scale=(True,True,True)
    if pb.name not in ['ROOT','BODY'] and not pb.name.startswith(('FOOT_','KNEE_')):pb.lock_location=(True,True,True)
    if pb.name.startswith('KNEE_'):pb.lock_rotation=(True,True,True)
    if hasattr(pb,'ik_stretch'):pb.ik_stretch=0
for key,d in legdefs.items():
    pb=rig.pose.bones[d['lower']]
    ik=pb.constraints.new('IK');ik.name='Two-bone leg IK • no stretch'
    ik.target=rig;ik.subtarget=d['ctrl'];ik.chain_count=2
    ik.pole_target=rig;ik.pole_subtarget=d['pole'];ik.use_stretch=False;ik.iterations=128
    # Choose the pole angle which reproduces the resting knee direction.
    def error(a):
        ik.pole_angle=a;bpy.context.view_layer.update()
        return (rig.pose.bones[d['upper']].tail-d['knee']).length
    choices=[(-math.pi+2*math.pi*i/72) for i in range(73)]
    best=min(choices,key=error)
    lo=best-math.pi/36;hi=best+math.pi/36
    for _ in range(18):
        a=lo+(hi-lo)/3;b=hi-(hi-lo)/3
        if error(a)<error(b):hi=b
        else:lo=a
    ik.pole_angle=(lo+hi)/2
    con=rig.pose.bones[d['foot']].constraints.new('COPY_ROTATION');con.name='Follow foot IK orientation'
    con.target=rig;con.subtarget=d['ctrl'];con.target_space='WORLD';con.owner_space='WORLD'

def group(ob,name):return ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
def smoothstep(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def assign(ob,idx,weights):
    for name,w in weights.items():
        if w>1e-8:group(ob,name).add([idx],w,'REPLACE')
def armature(ob,first=True):
    mod=ob.modifiers.new('Shrew skin • animator controls','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
    if first:
        active(ob);bpy.ops.object.modifier_move_to_index(modifier=mod.name,index=0)
    world=ob.matrix_world.copy();ob.parent=rig;ob.matrix_world=world

for ob in animal:
    if ob.type!='MESH':continue
    for vg in list(ob.vertex_groups):ob.vertex_groups.remove(vg)
    for v in ob.data.vertices:
        x,y,z=v.co
        if ob==body:
            h=smoothstep(-.35,.38,x);sp=smoothstep(-1.10,-.25,x)*(1-h)
            assign(ob,v.index,{'HEAD':h,'SPINE':sp,'BODY':1-h-sp})
        elif ob.name.startswith('Cylinder'):
            kind='front' if ob.name=='Cylinder' else 'hind';side='L' if y<0 else 'R';d=legdefs[kind+'.'+side]
            # Smooth weights across elbow/knee and ankle; feet remain stable.
            upper=smoothstep(d['knee'].z-.115,d['knee'].z+.115,z)
            f=1-smoothstep(.08,.19,z)
            assign(ob,v.index,{d['upper']:upper*(1-f),d['lower']:(1-upper)*(1-f),d['foot']:f})
        elif ob.name.startswith('Ear.'):
            earweight=smoothstep(2.10,2.43,z)
            assign(ob,v.index,{'EAR.L' if y<0 else 'EAR.R':earweight,'HEAD':1-earweight})
        else:assign(ob,v.index,{'HEAD':1})
    armature(ob)

# Keep the original Bezier tail editable, with each control point hooked to a bone.
for i,p in enumerate(tail.data.splines[0].bezier_points):
    target='TAIL.'+str(min(i+1,len(tailpts)-1)).zfill(2)
    hook=tail.modifiers.new('Tail point '+str(i+1)+' → '+target,'HOOK')
    hook.object=rig;hook.subtarget=target
    hook.vertex_indices_set([3*i,3*i+1,3*i+2])
    hook.matrix_inverse=(rig.matrix_world@arm.bones[target].matrix_local).inverted()@tail.matrix_world
    hook.strength=1;hook.falloff_type='NONE'
world=tail.matrix_world.copy();tail.parent=rig;tail.matrix_world=world
for ob in animal:
    if ob.type=='CURVE' and ob!=tail:
        con=ob.constraints.new('CHILD_OF');con.target=rig;con.subtarget='HEAD'
        con.inverse_matrix=(rig.matrix_world@arm.bones['HEAD'].matrix_local).inverted()

# Rest coordinates keep the nose color gradient attached while the head bends.
for ob in animal:
    if ob.type!='MESH':continue
    attr=ob.data.attributes.get('shrew_rest_position') or ob.data.attributes.new('shrew_rest_position','FLOAT_VECTOR','POINT')
    for v,item in zip(ob.data.vertices,attr.data):item.vector=v.co
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    nt=mat.node_tree
    for n in list(nt.nodes):
        if n.type=='TEX_COORD' and n.object==body:
            a=nt.nodes.new('ShaderNodeAttribute');a.attribute_name='shrew_rest_position';a.label='Bound rest coordinates';a.location=n.location
            for link in list(n.outputs['Object'].links):nt.links.new(a.outputs['Vector'],link.to_socket)

def widget(name,shape):
    vs=[];es=[]
    if shape=='box':
        vs=[(x,y,z) for x in [-1,1] for y in [-1,1] for z in [-1,1]]
        es=[(i,j) for i,a in enumerate(vs) for j,b in enumerate(vs) if j>i and sum(a[k]!=b[k] for k in range(3))==1]
    else:
        axes=[0,1,2] if shape=='sphere' else [1]
        for axis in axes:
            start=len(vs)
            for i in range(32):
                p=[math.cos(i*math.tau/32),math.sin(i*math.tau/32)];v=[0,0,0]
                ids=[k for k in range(3) if k!=axis];v[ids[0]]=p[0];v[ids[1]]=p[1];vs.append(v)
                es.append((start+i,start+(i+1)%32))
    me=bpy.data.meshes.new(name);me.from_pydata(vs,es,[])
    ob=bpy.data.objects.new(name,me);widgets.objects.link(ob);ob.hide_render=True;ob.hide_set(True)
    return ob
shapes={s:widget('WGT_'+s,s) for s in ['box','sphere','ring']}
for pb in rig.pose.bones:
    if pb.name.startswith('DEF_'):continue
    pb.use_custom_shape_bone_size=False
    if pb.name=='ROOT':shape='ring';scale=(2.05,2.05,2.05)
    elif pb.name.startswith('FOOT_'):shape='box';scale=(.14,.20,.055)
    elif pb.name.startswith('KNEE_'):shape='sphere';scale=(.06,.06,.06)
    elif pb.name=='BODY':shape='sphere';scale=(.43,.43,.43)
    elif pb.name in ['SPINE','HEAD']:shape='sphere';scale=(.26,.26,.26)
    elif pb.name.startswith('EAR'):shape='ring';scale=(.17,.17,.17)
    else:shape='ring';scale=(.115,.115,.115)
    pb.custom_shape=shapes[shape];pb.custom_shape_scale_xyz=scale

bpy.context.view_layer.update()
# Rest-pose vertex distances are matched by nearest surface vertex, independent
# of index ordering introduced by baking the paired mirror geometry.
from mathutils.kdtree import KDTree
report={'bones':len(arm.bones),'controls':sum(not b.name.startswith('DEF_') for b in arm.bones),'rest_error':{},'ik_tests':{}}
for ob in animal:
    old=before[ob.name];now=world_vertices(ob);tree=KDTree(len(old))
    for i,v in enumerate(old):tree.insert(v,i)
    tree.balance()
    err=max(tree.find(v)[2] for v in now)
    report['rest_error'][ob.name]=err
    assert err<.006,(ob.name,err)

def reset():
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
for key,d in legdefs.items():
    reset();p=rig.pose.bones[d['ctrl']]
    delta=Vector((.055,0,.09));p.location=arm.bones[p.name].matrix_local.to_3x3().inverted()@delta
    bpy.context.view_layer.update()
    error=(rig.pose.bones[d['lower']].tail-rig.pose.bones[d['ctrl']].head).length
    report['ik_tests'][key]={'foot_target_error':error}
    assert error<.003,(key,error)
reset()
# Body lowering with all feet planted is the most useful IK sanity check.
p=rig.pose.bones['BODY'];p.location=p.bone.matrix_local.to_3x3().inverted()@Vector((0,0,-.10))
bpy.context.view_layer.update()
report['crouch_max_foot_error']=max((rig.pose.bones[d['lower']].tail-rig.pose.bones[d['ctrl']].head).length for d in legdefs.values())
assert report['crouch_max_foot_error']<.004,report
reset()

readme='''땃쥐 리그 v06

SHREW_RIG 선택 → Pose Mode에서 조작합니다.
ROOT: 캐릭터 전체 위치/회전
BODY: 몸통 높이, 이동, 전체 몸통 기울기 (발은 IK 위치 유지)
SPINE: 등과 가슴 기울기
HEAD: 고개 숙이기, 좌우 보기
FOOT_IK_front.L/R, FOOT_IK_hind.L/R: G로 발 이동, R로 발 방향
KNEE_front/hind.L/R: 무릎/팔꿈치 굽힘 방향
EAR.L/R: 양쪽 귀 회전
TAIL.01~05: 꼬리 회전, 뿌리부터 끝 순서

조작 예: 프레임 1에서 컨트롤 선택 후 I → Location & Rotation. 프레임 12로 이동하여 발을 G로 조금 들고, HEAD를 R로 돌린 뒤 다시 키프레임을 넣습니다.
초기 자세: Pose Mode에서 컨트롤 전체 선택, Alt+G와 Alt+R (키프레임이 있는 경우 해당 프레임에서 다시 키를 넣어야 유지됩니다).

다리는 기존 Subdivision/Mirror 결과를 동일한 모양의 변형용 메시로 고정하여 좌우 독립 IK에 연결했습니다. 원본 모델링 메시와 Mirror는 shrew_before_rig_v06.blend에 보존했습니다. 몸통과 귀의 Subdivision은 유지했습니다. 꼬리는 원래 Bezier curve와 제어점을 유지합니다.
코 그라데이션과 표면 질감은 rest 좌표에 연결되어 머리 움직임을 따라갑니다.
단순 캐릭터용 기본 리그이며 완성된 걷기 애니메이션은 아직 없습니다. 기본 자세로 저장되어 바로 키프레임 작업을 시작할 수 있습니다.
'''
txt=bpy.data.texts.new('START HERE • 리그 사용법');txt.write(readme)
with open(os.path.join(OUT,'리그_사용법_v06.txt'),'w') as f:f.write(readme)
rig['rig_version']='v06';rig['help']='See START HERE • 리그 사용법 text. FOOT_IK: move feet; BODY: crouch; HEAD/EAR/TAIL: rotate.'
scene.frame_start=1;scene.frame_end=120;scene.render.fps=24;scene.frame_set(1)
scene['draft_version']='v06_rigged'
active(rig);bpy.ops.object.mode_set(mode='POSE')
for p in rig.pose.bones:p.select=False
rig.pose.bones['BODY'].select=True;arm.bones.active=arm.bones['BODY']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='CONSOLE':area.type='VIEW_3D'
        if area.type=='VIEW_3D':
            sp=next((s for s in area.spaces if s.type=='VIEW_3D'),None)
            if sp:
                sp.overlay.show_overlays=True;sp.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
                sp.region_3d.view_location=Vector((-.60,0,1.15));sp.region_3d.view_distance=7.8
                sp.region_3d.view_perspective='ORTHO'
scene.render.filepath=os.path.join(OUT,'shrew_rig_v06_rest.png')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'shrew_rig_v06.blend'))
bpy.ops.render.render(write_still=True)
# Demonstration pose is rendered only; the delivered file stays in a clean rest pose.
rig.pose.bones['BODY'].location=arm.bones['BODY'].matrix_local.to_3x3().inverted()@Vector((0,0,-.065))
rig.pose.bones['HEAD'].rotation_euler[0]=math.radians(-7)
rig.pose.bones['HEAD'].rotation_euler[2]=math.radians(7)
rig.pose.bones['EAR.L'].rotation_euler[1]=math.radians(12)
rig.pose.bones['EAR.R'].rotation_euler[1]=math.radians(-8)
for i in range(1,6):rig.pose.bones['TAIL.'+str(i).zfill(2)].rotation_euler[0]=math.radians(6)
d=legdefs['front.L'];p=rig.pose.bones[d['ctrl']]
p.location=p.bone.matrix_local.to_3x3().inverted()@Vector((.12,0,.14))
bpy.context.view_layer.update()
scene.render.filepath=os.path.join(OUT,'shrew_rig_v06_pose_test.png')
bpy.ops.render.render(write_still=True)
report['pose_test_render']='shrew_rig_v06_pose_test.png'
with open(os.path.join(OUT,'rig_v06_validation.json'),'w') as f:json.dump(report,f,indent=2)
print('RIG_V06_VALIDATED',json.dumps(report))
