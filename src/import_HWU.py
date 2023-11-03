#this script assumes the vehicles folder fromthe HotWheels unleashed(HWU) game is in the same directory as this blend folder
#containing the exprted assets from umodel with texures in a png format and meshes exported in a gltf format from the directory game/assets/graphics/vehicles)
#this script expects all assets to be exported, however select models with their folders in the cars/bikes can be independently imported along with the matching glass folders(HWU2)
#this script was designed for Blender 4.0

import bpy
import os
import json
import math
from os.path import exists

filepath = bpy.data.filepath
directory = os.path.dirname(filepath)
C = bpy.context

dir = os.path.join(directory, "vehicles")
if not os.path.isdir(dir):
    raise Exception("vehicles folder not present in directory for blend file, aborting")

cars = os.path.join(dir, "cars")
glasses = os.path.join(dir, "Glasses")
bikes = os.path.join(dir, "Bikes")

#spacing params for import
ySpacing =2.5
xSpacing =6
RowCount = 20
car = 0
col = 0
row = 0

AO_Strength = 0.5

ext ='.gltf'
matExt ='.props.txt'
texure_ext ='.png'


#fix for incorrectly exported material ids
expectedMaterialList =['MI_Chassis','MI_B_Wheel','MI_Livery','MI_Exterior','MI_Extra','MI_F_Wheel','MI_Interior','MI_Glass']

flakes_T = os.path.join(dir,'Shared','Textures','T_Flakes_N'+texure_ext)

def getChildren(myObject): 
    children = [] 
    for ob in bpy.data.objects: 
        if ob.parent == myObject: 
            children.append(ob) 
    return children 

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def is_bool(string):
    try:
        if string.lower() =='true':
            return [True,True]
        elif string.lower() =='false':
            return [True,False]
        else:
            return [False,None]
    except:
        return [False,None]
        
def readMatProps(filePath): #read from umodel mat.props.txt to json
    file = open(filePath, "r")
    text = file.read()
    file.close()
    split = text.split('{')
    splitArr =[]
    for item in split:
        subSplit = item.strip().split('\n')
        for item2 in subSplit:
            subSplit2 =  item2.strip().split('}')
            for item3 in subSplit2:
                if item3 !='':
                    splitArr.append(item3)
    
    matProperties=[]
    nameKey =''
    for item in splitArr:
        key = item.split('=')[0].strip()
        if len(item.split('=')[1])>0:
            itemDict =  item.replace("'",'').replace('MaterialInstanceConstant','').replace('Texture2D','').replace(' ','')
            dictValues = itemDict.replace(',','=').split('=')
            key = dictValues[0].strip()
            value = dictValues[1].strip()
            if is_float(value):
                value = float(value)
            isBool = is_bool(value)
            if isBool[0]:
                value = isBool[1]
            if key =='Name':
                nameKey = dictValues[1].strip()
            else:
                if len(dictValues)>2:
                    value ={}
                    for i in range(0,math.floor(len(dictValues)/2)):
                        val = dictValues[2*i+1]
                        if is_float(val):
                            val =float(val)
                        isBool = is_bool(val)
                        if isBool[0]:
                            value = isBool[1]
                        value[dictValues[2*i]]=val
                    matProperties.append({nameKey:value})
                elif key =='ParameterValue':
                    matProperties.append({nameKey:value})
                else:
                    if value !='None':
                        matProperties.append({key:value})
   
    return json.loads(json.dumps(matProperties, indent=4))

def loadTexture(materialInstance,texureFile,colorSpace):#set up texture
    if exists(texureFile):
        materialInstance.image = bpy.data.images.load(texureFile)
        materialInstance.image.colorspace_settings.name=colorSpace
        return True
    else:
        print('Texure not found:'+ texureFile)
        return False

def materialExists(material):
    materialList = bpy.data.materials
    name = material.name.split('.')[0]
    for mat in materialList:
        if mat.name == name:
            return True,mat
    return False, material

def uniqueItems(array):
    unique =[]
    for item in array:
        if not item in unique:
            unique.append(item)
    return unique

def setRGBA(shader,colors):
    for i,c in enumerate(colors):
        if c>1:
            shader.outputs['Color'].default_value[i]= 1
        else:
            shader.outputs['Color'].default_value[i]=c
    
def cleanNodeTree(material):
    nodes = material.node_tree.nodes
    for node in nodes:
        nodes.remove(node)

def buildMaterial(object,material,parameters):#set up node tree and map textures
    global AO_Strength
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new('ShaderNodeOutputMaterial')
    BDSF = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(BDSF.outputs['BSDF'], output.inputs['Surface'])

    output.location =[500,0]
    BDSF.location =[250,0]
    
    transmissionMult = nodes.new('ShaderNodeMath') 
    transmissionMult.label ='TransmissionMult'
    transmissionMult.operation = 'MULTIPLY'
    transmissionMult.inputs[0].default_value = 0
    transmissionMult.inputs[1].default_value = 0

    transmissionMult.location =[0,250]
    links.new(transmissionMult.outputs['Value'], BDSF.inputs['Transmission'])

    hasClearCoat = False
    
    AO_mix = nodes.new('ShaderNodeMix') 
    AO_mix.label ='AO mix'
    AO_mix.data_type = 'RGBA'
    AO_mix.blend_type = 'MULTIPLY'
    AO_mix.inputs['Factor'].default_value = 0
    links.new(AO_mix.outputs[2], BDSF.inputs['Base Color'])

    AO_mix.location =[0,-250]
    
    TC = nodes.new('ShaderNodeTexCoord')
    TC.location =[-1500,0]
    if 'AmbientOcclusion-Map'  in parameters.keys():
        AO = nodes.new('ShaderNodeTexImage')
        AO.label = 'AO'
        success = loadTexture(AO,parameters['AmbientOcclusion-Map'],'sRGB')    
        AO.location =[-1000,500]
        AO_mult = nodes.new('ShaderNodeMix') 
        AO_mult.label ='AO multiply'
        AO_mult.data_type = 'RGBA'
        AO_mult.inputs['Factor'].default_value = 1
        
        AO_mix.inputs['Factor'].default_value = AO_Strength
        AO_mult.location =[-250,250]
        links.new(AO.outputs['Color'],AO_mult.inputs[6])
        links.new(AO_mult.outputs[2], AO_mix.inputs[7])
        links.new(TC.outputs['UV'], AO.inputs['Vector'])

    bcModulationEnabled = False
    texureEnabled = False
    bc1OutputNode=AO_mix.inputs[6]
    bc2OutputNode = AO_mix.inputs[6]
    baseColor_mix = None
    norm = None
    
    if 'BaseColor-Map' in parameters.keys() or 'BaseColor-Modulation' in parameters.keys():
        matSplit = material.name.lower().replace('mi_','').replace('b_','').replace('f_','').split('_')
        if len(matSplit)>1 and 'BaseColor-Map' in parameters.keys():
            matId = matSplit[1]
            idMatch = parameters['BaseColor-Map'].lower().find(matId)>-1
            matName = matSplit[0]
            if matName =='livery':
                matName = 'body'
            matTypeMatch = parameters['BaseColor-Map'].lower().find(matName)>-1
        else:
            idMatch = True
            matTypeMatch = True

        texureEnabled = 'BaseColor-Map' in parameters.keys() and matTypeMatch and idMatch
        bcModulationEnabled =  'BaseColor-Modulation' in parameters.keys()
    
        if texureEnabled and bcModulationEnabled:
            baseColor_mix = nodes.new('ShaderNodeMix') 
            baseColor_mix.label ='Base color mult'
            baseColor_mix.data_type = 'RGBA'
            baseColor_mix.blend_type = 'MULTIPLY'
            baseColor_mix.inputs['Factor'].default_value = 0
            bc1OutputNode=baseColor_mix.inputs[7]
            bc2OutputNode=baseColor_mix.inputs[6]
            links.new(baseColor_mix.outputs[2],AO_mix.inputs[6])
    
        if bcModulationEnabled:
            colorRGB = nodes.new('ShaderNodeRGB')
            colorRGB.label ='basecolor'
            colorRGB.location =[-750,100]
            colors =[parameters['BaseColor-Modulation']['R'],parameters['BaseColor-Modulation']['G'],parameters['BaseColor-Modulation']['B'],parameters['BaseColor-Modulation']['A']]
            setRGBA(colorRGB,colors)
            links.new(bc1OutputNode,colorRGB.outputs['Color'])
            transmissionMult.inputs[0].default_value = 1
            
        if texureEnabled:
            colorT = nodes.new('ShaderNodeTexImage')
            colorT.label = 'basecolor'
            colorT.location =[-1000,0]
            success = loadTexture(colorT,parameters['BaseColor-Map'],'sRGB')
            invert = nodes.new('ShaderNodeInvert')
            invert.location =[-500,250]
            
            links.new(invert.inputs['Color'], colorT.outputs['Alpha'])
            links.new(transmissionMult.inputs[0], invert.outputs['Color'])
            links.new(TC.outputs['UV'], colorT.inputs['Vector'])
            links.new(bc2OutputNode,colorT.outputs['Color'])
            
        if material.name.lower().find('glass')>-1:
            transmissionMult.inputs[1].default_value = 1
            #set up EEVEE stuff
            material.blend_method = 'BLEND'
            material.shadow_method = 'HASHED'
            material.use_screen_refraction = True
            if baseColor_mix:
                baseColor_mix.inputs['Factor'].default_value = 1
        
    if 'ClearCoat-Map'  in parameters.keys():
        hasClearCoat = True
        CC = nodes.new('ShaderNodeTexImage')
        CC.label = 'clearcoat'
        success =  loadTexture(CC,parameters['ClearCoat-Map'],'sRGB')
        seperateRGBCC = nodes.new('ShaderNodeSeparateColor')
        links.new(seperateRGBCC.inputs['Color'], CC.outputs['Color'])
        invertCC = nodes.new('ShaderNodeInvert')
        links.new(invertCC.inputs['Color'], seperateRGBCC.outputs['Blue'])
        links.new(BDSF.inputs['Clearcoat'], invertCC.outputs['Color'])
        links.new(TC.outputs['UV'], CC.inputs['Vector'])
        CC.location =[-1000,250]
        invertCC.location =[-250,0]
        seperateRGBCC.location =[-500,0]
        
    if 'Normal-Map'  in parameters.keys():
        norm = nodes.new('ShaderNodeTexImage')
        norm.label = 'normal'
        success = loadTexture(norm,parameters['Normal-Map'],'Non-Color')
        normMap = nodes.new('ShaderNodeNormalMap')    
        links.new(normMap.inputs['Color'], norm.outputs['Color'])
        links.new(TC.outputs['UV'], norm.inputs['Vector'])
        norm.location =[-1000,-250]
        normMap.location =[0,-250]
        
    if 'Pbr-Map'  in parameters.keys():
        pbr = nodes.new('ShaderNodeTexImage')
        pbr.label = 'pbr'
        success = loadTexture(pbr,parameters['Pbr-Map' ],'sRGB')
        seperateRGB = nodes.new('ShaderNodeSeparateColor')
        links.new(seperateRGB.inputs['Color'], pbr.outputs['Color'])
        if 'AmbientOcclusion-Map'  in parameters.keys():
            links.new(AO_mult.inputs[7], seperateRGB.outputs['Red'])
        links.new(BDSF.inputs['Roughness'], seperateRGB.outputs['Green'])
        links.new(BDSF.inputs['Metallic'], seperateRGB.outputs['Blue'])
        links.new(TC.outputs['UV'], pbr.inputs['Vector'])
        pbr.location =[-1000,-500]
        seperateRGB.location =[-500,-500]
        
    if'Flakes-Size'in parameters.keys():
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value[0] = parameters['Flakes-Size']
        mapping.inputs['Scale'].default_value[1] = parameters['Flakes-Size']
        mapping.inputs['Scale'].default_value[2] = parameters['Flakes-Size']

        mapping.location =[-1250,-500]
        fNorm = nodes.new('ShaderNodeTexImage')
        fNorm.label = 'flakes_normal'
        success = loadTexture(fNorm,flakes_T,'Non-Color')
        fNorm.location =[-1000,-750]
        
        fNormMap = nodes.new('ShaderNodeNormalMap')
        fNormMap.location =[-500,-750]
        
        mathNode = nodes.new('ShaderNodeMath')
        mathNode.operation = 'MULTIPLY'
        mathNode.label ='flake intensity'
        mathNode.location =[-750,-600]
        
        mathNode.inputs[0].default_value = 1
        mathNode.inputs[1].default_value = 1
        links.new(fNormMap.inputs['Strength'], mathNode.outputs[0])
        if 'Flakes-NormalIntensity' in parameters.keys():
            mathNode.inputs[0].default_value =parameters['Flakes-NormalIntensity']
        if hasClearCoat:
            links.new(mathNode.inputs[1], CC.outputs['Color'])
            
        links.new(fNorm.inputs['Vector'], mapping.outputs['Vector'])
        links.new(BDSF.inputs['Normal'], fNormMap.outputs['Normal'])
        links.new(fNormMap.inputs['Color'], fNorm.outputs['Color'])
        links.new(mapping.inputs['Vector'], TC.outputs['UV'])
        if norm:
            vectMath = nodes.new('ShaderNodeVectorMath')
            vectMath.location =[0,-500]
            vectMath.operation = 'ADD'
            links.new(vectMath.inputs[0], normMap.outputs[0])
            links.new(vectMath.inputs[1], fNormMap.outputs[0])
            links.new(BDSF.inputs['Normal'], vectMath.outputs[0])
    else:
        if norm:
            links.new(BDSF.inputs['Normal'], normMap.outputs['Normal'])
        
    

def getMaterialInfo(object,material,materialDir):
    global matExt,texure_ext
    materialName = material.name.split('.')[0]
    if os.path.isdir(materialDir):
        matFile = os.path.join(materialDir,materialName+matExt)
        
        if exists(matFile):
            propsDict ={}
            matProps = readMatProps(matFile)
            for prop in matProps:
                key = list(prop.keys())[0]
                if key.find('Map')>-1:
                    if prop[key] != 'None' and isinstance(prop[key], str):
                        if prop[key].find('vehicles')>-1:
                            propsDict[key] = os.path.join(dir,*prop[key].split('.')[0].split('vehicles')[1].split('/')).replace("/","\\")+texure_ext
                else:
                    propsDict[key] = prop[key]
            buildMaterial(object,material,propsDict)
        else:
            print('material file not found for:'+matFile)

def importModel(carName,carFolder):
    global glasses,expectedMaterialList
    setUpMaterials =[]
    carID = carName.split('_')[1]
    meshFolder = os.path.join(carFolder,"SkelMesh")
    skelMesh = os.listdir(meshFolder)
    objMaterials = []
    if os.path.isdir(os.path.join(carFolder,"MatInst")):
        objMaterials = os.listdir(os.path.join(carFolder,"MatInst"))
    
    if os.path.isdir(glasses):#handle edge case with glassses folder
        glassFolder = os.path.join(glasses,"Glass_"+str(carID))
        glassExists =False
        if os.path.isdir(glassFolder):
            glassExists = True
            skelMesh += os.listdir(os.path.join(glassFolder,"SkelMesh"))
            objMaterials += os.listdir(os.path.join(glassFolder,'MatInst'))
    
    if not carName in bpy.data.collections:#set up collection
        collection = bpy.data.collections.new(carName)
        bpy.context.scene.collection.children.link(collection)
    else:
        collection = bpy.data.collections[carName]
    
    for mesh in skelMesh: 
        MeshName = mesh.split('.')
        if MeshName[1] == 'gltf':
            print('importing: '+MeshName[0])
            if MeshName[0].lower().find('glass')>-1 and os.path.isdir(glasses):
                folder = os.path.join(glassFolder,"SkelMesh")
            else:
                folder = meshFolder
            gltf = os.path.join(folder,mesh)
            print('Loaded '+ mesh)
            bpy.ops.import_scene.gltf(filepath=gltf)
            obj = bpy.context.active_object
            obj.location = (-row*xSpacing,-col*ySpacing,0)
            for coll in obj.users_collection:
                    coll.objects.unlink(obj)
            collection.objects.link(obj)
            for child in getChildren(obj):#assumes children will be meshes
                for coll in child.users_collection:
                    coll.objects.unlink(child)
                collection.objects.link(child)
                
                if child.parent.type =='ARMATURE':
                    child.parent.show_in_front = False
                    child.parent.data.show_bone_custom_shapes = False
                material_slots = child.material_slots
                materialsTrunc =[]
                for m in material_slots:
                    name = m.material.name.split('.')[0]
                    if not name in materialsTrunc:
                        materialsTrunc.append(name)
                uniqueVals = uniqueItems(materialsTrunc)
                
                #fix incorrect material id exports
                if len(material_slots) != len(uniqueVals):
                    print('Error: Issue with material slots assigned to mesh (attempting to fix): '+ child.name.split('.')[0])
                    currentMatid = 0
                    for matBaseName in expectedMaterialList:
                        matName = matBaseName+'_'+carID
                        matFile = matName + '.mat'
                        if matFile in objMaterials:
                            if currentMatid >=len(material_slots):
                                break
                            newMat = bpy.data.materials.new(name=matName)
                            newMat.use_nodes = True
                            child.data.materials[currentMatid] = newMat 
                            currentMatid+=1
                
                material_slots = child.material_slots                 
                for m in material_slots:#instance/set up materials
                    matExists,objMat = materialExists(m.material)
                    if matExists:
                        m.material = objMat
                    if m.material.name not in setUpMaterials:
                        cleanNodeTree(m.material)
                        if m.material.name.lower().find('glass')>-1 and os.path.isdir(glasses):
                            folder = os.path.join(glassFolder,"MatInst")
                        else:
                            folder = os.path.join(carFolder,"MatInst")
                        getMaterialInfo(carName,m.material,folder)


#main   
#load cars
for carModel in os.listdir(cars):
    if carModel !='CarShared':
        modelFolder =os.path.join(cars,carModel)
        importModel(carModel,modelFolder)
        car = car + 1
        col = col + 1
        if car%RowCount == 0:
            row = row + 1
            col = 0
            
#load bikes
if os.path.isdir(bikes):
    for bikeModel in os.listdir(bikes):
        modelFolder = os.path.join(bikes,bikeModel)
        importModel(bikeModel,modelFolder)
        car = car + 1
        col = col + 1
        if car%RowCount == 0:
            row = row + 1
            col = 0

print('Done! loaded:'+str(car)+' cars')