import sys, os
import glob
from PyQt5.QtCore import QVariant
import processing
from qgis.core import *
from datetime import datetime
import traceback
import csv

now = datetime.now()
print("Start: " + now.strftime("%y/%m/%d/%H:%M:%S"))

## DE: Change region line 19; Check line 36 for correct GHSL-layer

## Input:
worksp = 'D:/tarox7_user2/SUBDENSE/250430_compdense_workflow_V4/01_data_preparation/cci/'
umkreis = 20000
count_nearest_destinations = '50perc'
region_name = "str"
grid_space = 1000 # Rasterweite festlegen

## Output:
output_folder = worksp + 'output/'+ region_name +'_'+ str(count_nearest_destinations)+'_'+ now.strftime('%y_%m_%d')+'/'
matrix_folder = output_folder+'Matrizen/'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    os.makedirs(matrix_folder)# Ordner für aktuelle Berechnung erstellen

point_path = worksp + 'output/osmpoints_mitEWsum_'+str(grid_space)+'mgrid_'+region_name+'.shp' #Datei mit Punkteraster muss existieren
region = worksp + 'input/csr/'+region_name+'.shp'
region_buffer = worksp + 'input/csr/buffer/buffer_'+region_name+'.shp'
points_ew_out = output_folder +region_name+'_new.shp' # Outputdatei mit Punkten aus Zensusraster
destins_out =  output_folder+'destination_points_'+str(grid_space)+'mgrid_'+region_name+ str(count_nearest_destinations) +'.shp'

## Einwohnerpunkte erneut laden für reduzierte Punktmenge:
zensus = 'D:/tarox7_user2/SUBDENSE/250430_compdense_workflow_V4/01_data_preparation/GHS_POP_E2020_europe.tif' #einwohner_zensus2011_ohne_0.tif
layer = iface.addRasterLayer(zensus,"Zensus")
# muss evtl. noch reprojiziert werden
raster_region = processing.runAndLoadResults("gdal:cliprasterbymasklayer", {'INPUT':zensus,'MASK':region_buffer,'SOURCE_CRS':None,'TARGET_CRS':None,'TARGET_EXTENT':None,'NODATA':None,'ALPHA_BAND':False,'CROP_TO_CUTLINE':True,'KEEP_RESOLUTION':False,'SET_RESOLUTION':False,'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':False,'OPTIONS':'','DATA_TYPE':0,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'})
layer = iface.activeLayer()
raster_extent = str(layer.extent().xMinimum()) + ','+ str(layer.extent().xMaximum())+ ','+ str(layer.extent().yMinimum())+ ','+ str(layer.extent().yMaximum()) + ' ['+str(layer.crs().authid())+']'

## Zensusraster in Punkte umwandeln:
ew_points = processing.run("qgis:regularpoints", {'EXTENT':raster_extent,'SPACING':100,'INSET':50,'RANDOMIZE':False,'IS_SPACING':True,'CRS':QgsCoordinateReferenceSystem('EPSG:3035'),'OUTPUT':'TEMPORARY_OUTPUT'})
ew_points = processing.run("native:rastersampling", {'INPUT':ew_points['OUTPUT'],'RASTERCOPY': raster_region['OUTPUT'],'COLUMN_PREFIX':'EW','OUTPUT':'TEMPORARY_OUTPUT'})
ew_points = processing.run("qgis:selectbyexpression", {'INPUT': ew_points['OUTPUT'],'EXPRESSION':' "EW1"  IS NOT NULL','METHOD':0})
ew_points = processing.runAndLoadResults("native:saveselectedfeatures", {'INPUT':ew_points['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})

## Straßenpunkte auf 50% einschränken (zufällig):
extract = processing.run("native:randomextract", {'INPUT':point_path,'METHOD':1,'NUMBER':50,'OUTPUT':'TEMPORARY_OUTPUT'})
extract = processing.runAndLoadResults("native:deleteduplicategeometries", {'INPUT':extract['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})

## Einwohnerdaten auf Punkte summieren:
voronoi = processing.runAndLoadResults("qgis:voronoipolygons", {'INPUT':extract['OUTPUT'],'BUFFER':2,'OUTPUT':'TEMPORARY_OUTPUT'})
voronoi_einw = processing.runAndLoadResults("qgis:joinbylocationsummary", {'INPUT':voronoi['OUTPUT'],'PREDICATE':[1],'JOIN':ew_points['OUTPUT'],'JOIN_FIELDS':['EW1'],'SUMMARIES':[5],'DISCARD_NONMATCHING':False,'OUTPUT':'TEMPORARY_OUTPUT'})
origin_einw = processing.runAndLoadResults("native:joinattributestable", {'INPUT':extract['OUTPUT'],'FIELD':'id','INPUT_2':voronoi_einw['OUTPUT'],'FIELD_2':'id','FIELDS_TO_COPY':['EW1_sum_2'],'METHOD':1,'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT': 'TEMPORARY_OUTPUT'})
points = processing.runAndLoadResults("native:fieldcalculator", {'INPUT':origin_einw['OUTPUT'],'FIELD_NAME':'EW_10','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':3,'FORMULA':' if("EW1_sum_2" < 1,0, "EW1_sum_2" )','OUTPUT':output_folder+region_name+'10perc_ew.shp'})

region_points = iface.activeLayer()

## Zielpunkte auswählen, zu denen Routen berechnet werden: nur Punkte mit mehr als 5 Einwohnern als Zielpunkte:
destinations_all = processing.runAndLoadResults("native:extractbyexpression", {'INPUT':points['OUTPUT'],'EXPRESSION':' "EW_10" >= 5','OUTPUT':destins_out})

## Matrizenberechnung:
print('Matrizenberechnung startet')

l = []
err = [] #Liste mit Punkten bei denen ORS eine Fehlermeldung auswirft
for point in region_points.getFeatures():
    point_id = int(point['id'])
    processing.run("qgis:selectbyattribute", {'INPUT':region_points,'FIELD':'id','OPERATOR':0,'VALUE':point_id,'METHOD':0})
    origin = processing.run("native:saveselectedfeatures", {'INPUT':region_points,'OUTPUT':'TEMPORARY_OUTPUT'})# speichern des Startpunktes als Layer
    #print(origin['OUTPUT'].featureCount())
    #nearest_destins = processing.run("qgis:distancematrix", {'INPUT':origin['OUTPUT'],'INPUT_FIELD':'id','TARGET':destinations_all['OUTPUT'],'TARGET_FIELD':'id','MATRIX_TYPE':0,'NEAREST_POINTS':count_nearest_destinations,'OUTPUT':'TEMPORARY_OUTPUT'})
    #nearest_destins = processing.run("native:multiparttosingleparts", {'INPUT':nearest_destins['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})
    #nearest_destins = processing.run("native:deleteduplicategeometries", {'INPUT':nearest_destins['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})
    matrix_out = matrix_folder +'matrix_' +region_name +'_'+str(grid_space)+'mgrid_'+ str(point_id) + ".csv"
    l.append(matrix_out)

    try:
        processing.run("ORS Tools:matrix_from_layers", {'INPUT_PROVIDER':1,'INPUT_PROFILE':0,'INPUT_START_LAYER':origin['OUTPUT'],'INPUT_START_FIELD':'id','INPUT_END_LAYER':destinations_all['OUTPUT'],'INPUT_END_FIELD':'id','OUTPUT':matrix_out})
          
         
    except Exception:
        traceback.print_exc()
        err.append(point_id)
        
t = datetime.now()
print("ORS-Berechnung fertig: " + t.strftime("%y/%m/%d/%H:%M:%S"))
print('Anzahl fehlerhafte Punkte: ' + str(len(err)))
print('Erneute ORS-Berechnung für Fehlerpunkte')

## Für mögliche Fehlerpunkte erneute Berechnung (Workaround wegen unbekanntem Kapazitätsfehler) - teilweise manuell:
errfile = output_folder+'err_points.csv'
if len(err)>0:
    with open(errfile, 'w') as f:
        write = csv.writer(f)
        write.writerow(['ID'])
        for i in err:
            write.writerow([i])
    
    uri = "file:///"+errfile
    err_layer=QgsVectorLayer(uri,"err-data","delimitedtext")
    QgsProject.instance().addMapLayer(err_layer)
    err_float = processing.run("native:refactorfields", {'INPUT':err_layer,'FIELDS_MAPPING':[{'expression': '"ID"','length': 0,'name': 'ID','precision': 0,'sub_type': 0,'type': 6,'type_name': 'double precision'}],'OUTPUT':'TEMPORARY_OUTPUT'})
    errpoints = processing.runAndLoadResults("native:joinattributestable", {'INPUT':points['OUTPUT'],'FIELD':'id','INPUT_2':err_float['OUTPUT'],'FIELD_2':'ID','FIELDS_TO_COPY':[],'METHOD':1,'DISCARD_NONMATCHING':True,'PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})
    
    # Achtung: nächster Schritt noch nicht erprobt
    # processing.run("ORS Tools:matrix_from_layers", {'INPUT_PROVIDER':1,'INPUT_PROFILE':0,'INPUT_START_LAYER':errpoints['OUTPUT'], selectedFeaturesOnly=False, featureLimit=-1, flags=QgsProcessingFeatureSourceDefinition.FlagCreateIndividualOutputPerInputFeature, geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid),'INPUT_START_FIELD':'id','INPUT_END_LAYER': destinations_all['OUTPUT'],'INPUT_END_FIELD':'id','OUTPUT':matrix_folder +'matrix_' +region_name +'_err.csv'})
