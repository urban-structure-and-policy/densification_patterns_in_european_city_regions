import sys, os
import glob
from PyQt5.QtCore import QVariant
import processing
from qgis.core import *
from datetime import datetime

now = datetime.now()
print("Start: " + now.strftime("%H:%M:%S"))

## DE: Change region line 15; Check line 66 for correct GHSL-layer

## Input:
worksp = 'D:/tarox7_user2/SUBDENSE/250430_compdense_workflow_V4/01_data_preparation/cci/'
region_name = 'str'# Bereich hier ändern
region = 'D:/tarox7_user2/SUBDENSE/250430_compdense_workflow_V4/01_data_preparation/cci/input/csr/'+region_name+'.shp'
umkreis = 20000 # Für Buffer um Region - 20km festgelegt
grid_space = 1000 # Rasterweite festlegen

## Output:
points_out = worksp + 'output/osmpoints_'+str(grid_space)+'mgrid_'+region_name+'.shp' # Outputdatei mit Punkten auf Straßennetz
points_ew_out = worksp + 'output/ew_points_'+region_name+'.shp' # Outputdatei mit Punkten aus Zensusraster
points_out_2 = worksp + 'output/osmpoints_mitEWsum_'+str(grid_space)+'mgrid_'+region_name+'.shp' # Outputdatei mit Punkten auf Straßennetz

## Datendownload von OSM:
#BBox festlegen: 
layer = iface.addVectorLayer(region, region_name, "ogr")
buffer = processing.run("native:buffer", {'INPUT':layer,'DISTANCE':umkreis,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':True,'OUTPUT':'TEMPORARY_OUTPUT'})
puffer = buffer['OUTPUT']
bbox = str(puffer.extent().xMinimum()) + ','+ str(puffer.extent().xMaximum())+ ','+ str(puffer.extent().yMinimum())+ ','+ str(puffer.extent().yMaximum()) + ' ['+str(puffer.crs().authid())+']'
print(bbox)

## Abfrage über OverpassAPI - für neue Region Kommentare entfernen:
alg_params = {
    'EXTENT': bbox,
    'KEY': 'highway',
    'SERVER': 'https://lz4.overpass-api.de/api/interpreter',
    'TIMEOUT': 300,
    'VALUE': ''
}
query = processing.run('quickosm:buildqueryextent', alg_params)
file = processing.run("native:filedownloader", {'URL':query['OUTPUT_URL'], 'OUTPUT':worksp +'input/OSM/'+region_name+'_roh.osm'}) # Speichert OSM-Daten
vlayer = iface.addVectorLayer(file['OUTPUT']+'|layername=lines', "highway", "ogr") 
vlayer = iface.addVectorLayer(worksp +'input/OSM/'+region_name+'_roh.osm'+'|layername=lines', "highway_OSM", "ogr")
#vlayer = iface.addVectorLayer(worksp +'input/OSM/'+region_name+'_OSM_lines.shp', "highway_OSM", "ogr") # Option, wenn schon Daten vorhanden sind und nur neues Raster generiert werden soll
vlayer.removeSelection()

## Straßen filtern:
#highway_list = ['motorway','trunk','primary','secondary','tertiary','unclassified','residential','motorway_link','trunk_link','primary_link','secondary_link','tertiary_link','living_street','service']
processing.run("qgis:selectbyexpression", {'INPUT':vlayer,'EXPRESSION':' "highway" IN (\'motorway\',\'trunk\',\'primary\',\'secondary\',\'tertiary\',\'unclassified\',\'residential\',\'motorway_link\',\'trunk_link\',\'primary_link\',\'secondary_link\',\'tertiary_link\',\'living_street\',\'service\') AND  "other_tags" NOT LIKE \'%"access"=>"private"%\'','METHOD':0})
highways = processing.run("native:saveselectedfeatures", {'INPUT':vlayer,'OUTPUT':'TEMPORARY_OUTPUT'})#worksp + 'highways_'+region_name+'.shp'})

## Rasterpunkte erzeugen und auf Straßennetz anpassen:
grid = processing.run("native:creategrid", {'TYPE':4,'EXTENT':bbox,'HSPACING':grid_space,'VSPACING':grid_space,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:25832'),'OUTPUT':'TEMPORARY_OUTPUT'})
points = processing.run("native:centroids", {'INPUT':grid['OUTPUT'],'ALL_PARTS':False,'OUTPUT':'TEMPORARY_OUTPUT'})
join = processing.run("native:joinbynearest", {'INPUT':points['OUTPUT'],'INPUT_2':highways['OUTPUT'],'FIELDS_TO_COPY':[],'DISCARD_NONMATCHING':False,'PREFIX':'','NEIGHBORS':1,'MAX_DISTANCE':grid_space/2,'OUTPUT':'TEMPORARY_OUTPUT'})
pointsfromhighways = processing.run("native:geometrybyexpression", {'INPUT':join['OUTPUT'],'OUTPUT_GEOMETRY':2,'WITH_Z':False,'WITH_M':False,'EXPRESSION':'make_point( "nearest_x" , "nearest_y" )','OUTPUT':'TEMPORARY_OUTPUT'})#worksp + 'OSM_highways/Punktnetz/pointsfromhighways_2km_' +region_name+ '.shp'})
c = processing.run("native:clip", {'INPUT':pointsfromhighways['OUTPUT'],'OVERLAY':buffer['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})
points = processing.run("native:multiparttosingleparts", {'INPUT':c['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})
points_single = processing.run("native:deleteduplicategeometries", {'INPUT':points['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'}) # wichtig, da irgendwie doppelte Geometrien entstehen
processing.run("native:deletecolumn", {'INPUT':points_single['OUTPUT'],'COLUMN':['left','top','right','bottom','osm_id','name','highway','waterway','aerialway','barrier','man_made','railway','z_order','other_tags','n','distance','feature_x','feature_y','nearest_x','nearest_y'],'OUTPUT':points_out}) #überflüssige OSM-Spalten löschen
point_layer = iface.activeLayer()


## Einwohnerdaten hinzufügen:
zensus = 'D:/tarox7_user2/SUBDENSE/250430_compdense_workflow_V4/01_data_preparation/GHS_POP_E2020_europe.tif' #einwohner_zensus2011_ohne_0.tif
layer = iface.addRasterLayer(zensus,"Zensus")
# muss evtl. noch reprojiziert werden
raster_region = processing.runAndLoadResults("gdal:cliprasterbymasklayer", {'INPUT':zensus,'MASK':puffer,'SOURCE_CRS':None,'TARGET_CRS':None,'TARGET_EXTENT':None,'NODATA':None,'ALPHA_BAND':False,'CROP_TO_CUTLINE':True,'KEEP_RESOLUTION':False,'SET_RESOLUTION':False,'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':False,'OPTIONS':'','DATA_TYPE':0,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'})
layer = iface.activeLayer()
raster_extent = str(layer.extent().xMinimum()) + ','+ str(layer.extent().xMaximum())+ ','+ str(layer.extent().yMinimum())+ ','+ str(layer.extent().yMaximum()) + ' ['+str(layer.crs().authid())+']'

## Zensusraster in Punkte umwandeln:
ew_points = processing.run("qgis:regularpoints", {'EXTENT':raster_extent,'SPACING':100,'INSET':50,'RANDOMIZE':False,'IS_SPACING':True,'CRS':QgsCoordinateReferenceSystem('EPSG:3035'),'OUTPUT':'TEMPORARY_OUTPUT'})
ew_points = processing.run("native:rastersampling", {'INPUT':ew_points['OUTPUT'],'RASTERCOPY': raster_region['OUTPUT'],'COLUMN_PREFIX':'EW','OUTPUT':'TEMPORARY_OUTPUT'})
processing.run("qgis:selectbyexpression", {'INPUT': ew_points['OUTPUT'],'EXPRESSION':' "EW1"  IS NOT NULL','METHOD':0}) #nur Punkte wo einwohner Vorhanden
ew_points = processing.run("native:saveselectedfeatures", {'INPUT':ew_points['OUTPUT'],'OUTPUT':points_ew_out})

## Einwohnerdaten auf Straßenpunkte summieren:
voronoi = processing.run("qgis:voronoipolygons", {'INPUT':points_out,'BUFFER':2,'OUTPUT':'TEMPORARY_OUTPUT'})
voronoi_einw = processing.runAndLoadResults("qgis:joinbylocationsummary", {'INPUT': voronoi['OUTPUT'],'JOIN':points_ew_out,'PREDICATE':[1],'JOIN_FIELDS':[],'SUMMARIES':[5],'DISCARD_NONMATCHING':False,'OUTPUT':'TEMPORARY_OUTPUT'})
origin_einw = processing.runAndLoadResults("native:joinattributestable", {'INPUT':points_out,'FIELD':'id','INPUT_2':voronoi_einw['OUTPUT'],'FIELD_2':'id','FIELDS_TO_COPY':['EW1_sum'],'METHOD':1,'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT': 'TEMPORARY_OUTPUT'})
processing.runAndLoadResults("native:fieldcalculator", {'INPUT':origin_einw['OUTPUT'],'FIELD_NAME':'EW_2','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':3,'FORMULA':' if("EW1_sum" < 1,0, "EW1_sum" )','OUTPUT':points_out_2})
#processing.runAndLoadResults("native:extractbyexpression", {'INPUT':origin_einw['OUTPUT'],'EXPRESSION':' "EW1" >= 1','OUTPUT':points_out_2})

end = datetime.now()
print("Ende: " + end.strftime("%H:%M:%S"))