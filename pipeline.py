# Extract the data from the .gml file

import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

#tree = ET.parse('/Users/home/Documents/projects/nextgencities/data/SO06_2013.gml')
tree = ET.parse('/Users/home/Downloads/vm012013/VM01_2013.gml')
root = tree.getroot()

ns = {'bldg': "http://www.opengis.net/citygml/building/1.0",
       'gml': "http://www.opengis.net/gml"}

len(root.findall(".//{http://www.opengis.net/citygml/1.0}cityObjectMember"))
# This is the total number of the buildings in this file.

buildingList = [[[], [], []] for i in range(666)];
buildingCount = 0;

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

for buildingElement in root.findall(".//{http://www.opengis.net/citygml/1.0}cityObjectMember", ns):
  for surfaceElement in buildingElement.findall(".//{http://www.opengis.net/citygml/building/1.0}GroundSurface", ns):
    for polygon in surfaceElement.findall(".//{http://www.opengis.net/gml}posList", ns):
      buildingList[buildingCount][0].append(list(chunker(tuple(map(float, polygon.text.split())), 3)))
  buildingCount += 1

buildingCount = 0;
for buildingElement in root.findall(".//{http://www.opengis.net/citygml/1.0}cityObjectMember", ns):
  for surfaceElement in buildingElement.findall(".//{http://www.opengis.net/citygml/building/1.0}WallSurface", ns):
    for polygon in surfaceElement.findall(".//{http://www.opengis.net/gml}posList", ns):
      buildingList[buildingCount][1].append(list(chunker(tuple(map(float, polygon.text.split())), 3)))
  buildingCount += 1

buildingCount = 0;
for buildingElement in root.findall(".//{http://www.opengis.net/citygml/1.0}cityObjectMember", ns):
  for surfaceElement in buildingElement.findall(".//{http://www.opengis.net/citygml/building/1.0}RoofSurface", ns):
    for polygon in surfaceElement.findall(".//{http://www.opengis.net/gml}posList", ns):
      buildingList[buildingCount][2].append(list(chunker(tuple(map(float, polygon.text.split())), 3)))
  buildingCount += 1

# Convert each polygon float list into a pandas Data frame, containing n by d matrices, n being the geo-coordinates, and d being the number of dimension (3, in this case)
# newList = [pd.DataFrame(np.array(polygon).reshape(-1, 3), columns= list("xyz")) for polygon in newList]
# The above line is NOT APPLICABLE AS OF NOW!
  


import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.colors import ListedColormap
import shapely
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import cascaded_union, unary_union

for building in buildingList:
        for surfaceElement in building:
                for polygon in surfaceElement:
                        if (len(polygon) < 3):
                          print ("DIRTY DATA!\n")
                          surfaceElement.remove(polygon)
                          

for building in buildingList:
        for surfaceElement in building:
          for i in range(len(surfaceElement)):
            surfaceElement[i] = Polygon(surfaceElement[i])
            

def extract_poly_coords(geom):
    if geom.type == 'Polygon':
        exterior_coords = geom.exterior.coords[:]
        interior_coords = []
        for interior in geom.interiors:
            interior_coords += interior.coords[:]
    elif geom.type == 'MultiPolygon':
        exterior_coords = []
        interior_coords = []
        for part in geom:
            epc = extract_poly_coords(part)  # Recursive call
            exterior_coords += epc['exterior_coords']
            interior_coords += epc['interior_coords']
    else:
        raise ValueError('Unhandled geometry type: ' + repr(geom.type))
    return {'exterior_coords': exterior_coords,
            'interior_coords': interior_coords}
    

roofSurfaceMaximumZCoordinatePerPolygonList = list()
for building in buildingList:
  temporaryZCoordinateForOnePolygonList = list()
  for t in extract_poly_coords(unary_union(building[2]))['exterior_coords']:
    temporaryZCoordinateForOnePolygonList.append(t[2])
  zMax = max(temporaryZCoordinateForOnePolygonList)
  roofSurfaceMaximumZCoordinatePerPolygonList.append(zMax)
  
groundSurfaceMinimumZCoordinatePerPolygonList = list()
for building in buildingList:
  temporaryZCoordinateForOnePolygonList = list()
  for t in extract_poly_coords(unary_union(building[0]))['exterior_coords']:
    temporaryZCoordinateForOnePolygonList.append(t[2])
  zMin = min(temporaryZCoordinateForOnePolygonList)
  groundSurfaceMinimumZCoordinatePerPolygonList.append(zMin)
  
differenceList = list()
for i in range(len(groundSurfaceMinimumZCoordinatePerPolygonList)):
  differenceList.append(roofSurfaceMaximumZCoordinatePerPolygonList[i] - groundSurfaceMinimumZCoordinatePerPolygonList[i])
  

groundSurfaceCoordinatesList = list()
for building in buildingList:
  groundSurfaceCoordinatesList.append(extract_poly_coords(unary_union(building[0]))['exterior_coords'])
  

finalGroundSurfaceCoordinatesList = list()
for groundSurface in groundSurfaceCoordinatesList:
  finalGroundSurfaceCoordinatesList.append([(x[0]-300950, x[1]-5037400) for x in (groundSurface)])
  
from geomeppy import IDF 
IDF.setiddname('/Applications/EnergyPlus-9-2-0/Energy+.idd')
idf = IDF('/Applications/EnergyPlus-9-2-0/ExampleFiles/Minimal.idf')
idf.epw = '/Applications/EnergyPlus-9-2-0/WeatherData/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'

#for i in range(len(finalGroundSurfaceCoordinatesList)):
for i in range(300, 500):
    idf.add_block(name='Block'+str(i), coordinates=finalGroundSurfaceCoordinatesList[i], height=differenceList[i])


idf.set_wwr(0.6)
idf.view_model()
idf.intersect_match()
idf.translate_to_origin()
idf.set_default_constructions()

 
# Heating and cooling system
stat = idf.newidfobject( "HVACTEMPLATE:THERMOSTAT", Name="Zone Stat", Constant_Heating_Setpoint=20, Constant_Cooling_Setpoint=25, ) 
for zone in idf.idfobjects["ZONE"]: idf.newidfobject( "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM", Zone_Name=zone.Name, Template_Thermostat_Name=stat.Name, )

#Output
idf.newidfobject( "OUTPUT:VARIABLE", Variable_Name="Zone Ideal Loads Supply Air Total Heating Energy", Reporting_Frequency="Hourly", ) 
idf.newidfobject( "OUTPUT:VARIABLE", Variable_Name="Zone Ideal Loads Supply Air Total Cooling Energy", Reporting_Frequency="Hourly", )

#Run
idf.run()

