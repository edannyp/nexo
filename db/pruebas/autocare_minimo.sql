-- AutoCare MÍNIMO para probar db/ref/cargar_ref.py sin acceso real. Solo las tablas y columnas que lee la herramienta.
-- Datos SINTÉTICOS (no son de AutoCare), salvo los IDs de tipo de parte y PAdb que usa Nexo (2172, 267, 7448…).
create schema vcdb_base;  create schema vcdb_parts; create schema vcdb_config;
create schema pcdb_base;  create schema pcdb_parts;
create schema padb_base;  create schema padb_config; create schema padb_meta;

create table vcdb_parts.db_version (database_name text, version text, publication_date date);
create table pcdb_parts.db_version (database_name text, version text, publication_date date);
create table padb_meta.db_version  (database_name text, version text, publication_date date);
insert into vcdb_parts.db_version values ('VCdb', '1.0', '2026-01-30');
insert into pcdb_parts.db_version values ('PCdb', '1.0', '2026-01-30');
insert into padb_meta.db_version  values ('PAdb', '1.0', '2026-01-30');

create table vcdb_base.make (make_id integer primary key, make_name text);
create table vcdb_base.model (model_id integer primary key, model_name text);
create table vcdb_base.sub_model (sub_model_id integer primary key, sub_model_name text);
create table vcdb_parts.region (region_id integer primary key, region_abbr text, region_name text);
create table vcdb_base.base_vehicle (base_vehicle_id integer primary key, year_id integer, make_id integer, model_id integer);
create table vcdb_base.vehicle_type (vehicle_type_id integer primary key, vehicle_type_name text);
create table vcdb_parts.mfr (mfr_id integer primary key, mfr_name text);
create table vcdb_base.equipment_model (equipment_model_id integer primary key, equipment_model_name text);
create table vcdb_base.equipment_base (equipment_base_id integer primary key, mfr_id integer, equipment_model_id integer);
create table vcdb_config.engine_config (engine_config_id integer primary key);
create table vcdb_config.transmission (transmission_id integer primary key);
create table pcdb_base.part (part_terminology_id integer primary key, part_terminology_name text);
create table pcdb_base.position (position_id integer primary key, position text);
create table padb_base.part_attribute (paid integer primary key, pa_name text);
create table padb_config.part_attribute_assignment (paptid integer primary key, part_terminology_id integer, paid integer);
create table padb_config.meta_uom_code_assignment (paptid integer);
create table padb_base.valid_value (valid_value_id integer primary key, valid_value text);
create table padb_config.valid_value_assignment (paptid integer, valid_value_id integer);
create table padb_base.meta_uom_code (uom_code text primary key, uom_label text);

insert into vcdb_base.make values (901, 'Suzuki'), (903, 'Changan');
insert into vcdb_base.model values (9101, 'Grand Vitara'), (9102, 'CS35');
insert into vcdb_base.sub_model values (20, 'Base'), (21, 'GLX');
insert into vcdb_parts.region values (1, 'USA', 'United States'), (13, 'GTM', 'Guatemala'), (21, 'SLV', 'El Salvador');
insert into vcdb_base.base_vehicle select 800000 + y, y, 901, 9101 from generate_series(2005, 2015) y;
insert into vcdb_base.base_vehicle select 810000 + y, y, 903, 9102 from generate_series(2017, 2020) y;
insert into vcdb_base.vehicle_type values (5, 'Car');
insert into vcdb_parts.mfr values (601, 'Perkins Engines Company Ltd');
insert into vcdb_base.equipment_model values (6501, '1104C-44T');
insert into vcdb_base.equipment_base values (700001, 601, 6501);
insert into vcdb_config.engine_config values (4704), (4705);
insert into vcdb_config.transmission values (1);
-- 2172 Radiator y 6708 A/C Condenser son de Nexo; 9999 es un tipo de parte que Nexo no usa (no debe copiarse)
insert into pcdb_base.part values (2172, 'Radiator'), (6708, 'A/C Condenser'), (9999, 'Wiper Blade');
insert into pcdb_base.position values (1, 'Front');
insert into padb_base.part_attribute values (267, 'Core Height'), (268, 'Core Thickness'), (269, 'Core Width'), (7448, 'Flow Type'),
                                            (302, 'Core Material'), (5555, 'Blade Length');
insert into padb_config.part_attribute_assignment values (1, 2172, 267), (2, 2172, 268), (3, 2172, 269), (4, 2172, 7448), (5, 2172, 302),
                                                         (6, 9999, 5555);
insert into padb_config.meta_uom_code_assignment values (1), (2), (3), (6);
insert into padb_base.valid_value values (391, 'Cross Flow'), (444, 'Down Flow'), (203, 'Aluminum'), (381, 'Copper'), (777, 'Rubber');
insert into padb_config.valid_value_assignment values (4, 391), (4, 444), (5, 203), (5, 381), (6, 777);
insert into padb_base.meta_uom_code values ('MM', 'Millimeter');
