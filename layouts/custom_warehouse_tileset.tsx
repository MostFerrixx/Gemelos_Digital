<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.5" name="custom_warehouse_tileset" tilewidth="32" tileheight="32" tilecount="6" columns="4">
 <image source="custom_warehouse_tileset.png" width="128" height="64"/>
 <tile id="0">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="floor"/>
   <property name="name" value="Suelo navegable"/>
   <property name="description" value="Suelo normal por donde pueden caminar los operarios"/>
   <property name="custom_texture" value="floor.png"/>
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="walkable" value="false"/>
   <property name="type" value="rack"/>
   <property name="name" value="Racks/Estantes"/>
   <property name="description" value="Racks de almacén (obstáculos)"/>
   <property name="custom_texture" value="rack.png"/>
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="picking"/>
   <property name="name" value="Puntos de picking"/>
   <property name="description" value="Ubicaciones de picking frente a racks"/>
   <property name="custom_texture" value="PickLocation.png"/>
  </properties>
 </tile>
 <tile id="3">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="parking"/>
   <property name="name" value="Zona estacionamiento/inicio"/>
   <property name="description" value="Zona donde aparecen los operarios al inicio"/>
   <property name="custom_texture" value="ParckingLot.png"/>
  </properties>
 </tile>
 <tile id="4">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="depot"/>
   <property name="name" value="Zona depot/depósito"/>
   <property name="description" value="Zona donde se depositan los productos pickeados"/>
   <property name="custom_texture" value="OutboundStage.png"/>
  </properties>
 </tile>
 <tile id="5">
  <properties>
   <property name="walkable" value="true"/>
   <property name="type" value="inbound"/>
   <property name="name" value="Zona entrada/recepción"/>
   <property name="description" value="Zona de entrada de mercancía"/>
   <property name="custom_texture" value="InboundStage.png"/>
  </properties>
 </tile>
</tileset>
