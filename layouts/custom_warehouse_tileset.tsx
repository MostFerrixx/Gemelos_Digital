<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.11.2" name="custom_warehouse_tileset" tilewidth="32" tileheight="32" tilecount="8" columns="4" tilerendersize="grid">
 <image source="custom_warehouse_tileset.png" width="128" height="64"/>
 <tile id="0">
  <properties>
   <property name="custom_texture" value="floor.png"/>
   <property name="description" value="Suelo normal por donde pueden caminar los operarios"/>
   <property name="name" value="Suelo navegable"/>
   <property name="type" value="floor"/>
   <property name="walkable" value="true"/>
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="custom_texture" value="rack.png"/>
   <property name="description" value="Racks de almacén (obstáculos)"/>
   <property name="name" value="Racks/Estantes"/>
   <property name="type" value="rack"/>
   <property name="walkable" value="false"/>
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="custom_texture" value="PickLocation.png"/>
   <property name="description" value="Ubicaciones de picking frente a racks"/>
   <property name="name" value="Puntos de picking"/>
   <property name="type" value="MultiLevelPickingPoint"/>
   <property name="walkable" value="true"/>
  </properties>
  <objectgroup draworder="index" id="2">
   <object id="1" x="0" y="0" width="32" height="32"/>
  </objectgroup>
 </tile>
 <tile id="3">
  <properties>
   <property name="custom_texture" value="ParckingLot.png"/>
   <property name="description" value="Zona donde aparecen los operarios al inicio"/>
   <property name="name" value="Zona estacionamiento/inicio"/>
   <property name="type" value="parking"/>
   <property name="walkable" value="true"/>
  </properties>
 </tile>
 <tile id="4">
  <properties>
   <property name="custom_texture" value="OutboundStage.png"/>
   <property name="description" value="Zona donde se depositan los productos pickeados"/>
   <property name="name" value="Zona depot/depósito"/>
   <property name="type" value="depot"/>
   <property name="walkable" value="true"/>
  </properties>
 </tile>
 <tile id="5">
  <properties>
   <property name="custom_texture" value="InboundStage.png"/>
   <property name="description" value="Zona de entrada de mercancía"/>
   <property name="name" value="Zona entrada/recepción"/>
   <property name="type" value="inbound"/>
   <property name="walkable" value="true"/>
  </properties>
 </tile>
</tileset>
