<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.5" name="warehouse_tileset" tilewidth="32" tileheight="32" tilecount="12" columns="4">
 <image source="warehouse_tileset.png" width="128" height="96"/>
 <tile id="0">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="floor"/>
   <property name="speed_modifier" value="1.0"/>
   <property name="name" value="Floor_Walkable"/>
   <property name="description" value="Suelo navegable normal"/>
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="walkable" value="false"/>
   <property name="type" value="rack"/>
   <property name="height" value="3"/>
   <property name="name" value="Rack_Obstacle"/>
   <property name="description" value="Rack de almacén (obstáculo)"/>
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="picking"/>
   <property name="priority" value="high"/>
   <property name="name" value="Picking_Point"/>
   <property name="description" value="Punto de picking"/>
  </properties>
 </tile>
 <tile id="3">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="depot"/>
   <property name="capacity" value="10"/>
   <property name="name" value="Depot_Zone"/>
   <property name="description" value="Zona de depot/estacionamiento"/>
  </properties>
 </tile>
 <tile id="4">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="inbound"/>
   <property name="dock_count" value="2"/>
   <property name="name" value="Inbound_Zone"/>
   <property name="description" value="Zona de entrada/inbound"/>
  </properties>
 </tile>
 <tile id="5">
  <properties>
   <property name="walkable" value="false"/>
   <property name="type" value="wall"/>
   <property name="blocking" value="true"/>
   <property name="name" value="Wall_Blocked"/>
   <property name="description" value="Muro/zona prohibida"/>
  </properties>
 </tile>
 <tile id="6">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="corridor"/>
   <property name="speed_modifier" value="1.2"/>
   <property name="name" value="Corridor_Main"/>
   <property name="description" value="Pasillo principal (más rápido)"/>
  </properties>
 </tile>
 <tile id="7">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="workstation"/>
   <property name="equipment" value="scanner"/>
   <property name="name" value="Workstation"/>
   <property name="description" value="Estación de trabajo"/>
  </properties>
 </tile>
 <tile id="8">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="emergency"/>
   <property name="exit" value="true"/>
   <property name="name" value="Emergency_Exit"/>
   <property name="description" value="Salida de emergencia"/>
  </properties>
 </tile>
 <tile id="9">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="loading"/>
   <property name="truck_capacity" value="1"/>
   <property name="name" value="Loading_Dock"/>
   <property name="description" value="Muelle de carga"/>
  </properties>
 </tile>
 <tile id="10">
  <properties>
   <property name="walkable" value="false"/>
   <property name="type" value="office"/>
   <property name="restricted" value="true"/>
   <property name="name" value="Office_Area"/>
   <property name="description" value="Área de oficinas"/>
  </properties>
 </tile>
 <tile id="11">
  <properties>
   <property name="walkable" value="false"/>
   <property name="type" value="reserved"/>
   <property name="future_use" value="true"/>
   <property name="name" value="Reserved_Future"/>
   <property name="description" value="Reservado para uso futuro"/>
  </properties>
 </tile>
</tileset>
