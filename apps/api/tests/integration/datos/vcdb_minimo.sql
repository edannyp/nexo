-- Esquema VCdb mínimo (solo las columnas que lee el adaptador AutoCare) con datos sintéticos. NO son datos de AutoCare.
create schema vcdb_base;
create schema vcdb_parts;
create schema vcdb_config;
create table vcdb_base.make (make_id integer primary key, make_name text not null);
create table vcdb_base.model (model_id integer primary key, model_name text not null);
create table vcdb_base.sub_model (sub_model_id integer primary key, sub_model_name text not null);
create table vcdb_base.base_vehicle (base_vehicle_id integer primary key, year_id integer, make_id integer, model_id integer);
create table vcdb_parts.region (region_id integer primary key, region_abbr text not null);
create table vcdb_base.vehicle (vehicle_id integer primary key, base_vehicle_id integer, sub_model_id integer, region_id integer);
create table vcdb_parts.engine_base (engine_base_id integer primary key, liter numeric, block_type text, cylinders text);
create table vcdb_parts.engine_designation (engine_designation_id integer primary key, engine_designation_name text);
create table vcdb_parts.fuel_type (fuel_type_id integer primary key, fuel_type_name text);
create table vcdb_parts.aspiration (aspiration_id integer primary key, aspiration_name text);
create table vcdb_config.engine_config (engine_config_id integer primary key, engine_base_id integer, engine_designation_id integer,
                                        fuel_type_id integer, aspiration_id integer);
create table vcdb_config.vehicle_to_engine_config (vehicle_id integer, engine_config_id integer);

insert into vcdb_base.make values (1, 'Toyota'), (2, 'Isuzu');
insert into vcdb_base.model values (10, 'Pickup'), (11, 'Hilux'), (20, 'D-Max');
insert into vcdb_base.sub_model values (100, 'DLX'), (101, 'SR5');
insert into vcdb_base.base_vehicle values (5001, 1986, 1, 10), (5002, 1987, 1, 10), (5003, 1987, 1, 11), (6001, 2012, 2, 20);
insert into vcdb_parts.region values (1, 'USA'), (2, 'CAN');
insert into vcdb_parts.engine_base values (1, 2.4, 'L', '4');
insert into vcdb_parts.engine_designation values (1, '22R'), (2, '-');
insert into vcdb_parts.fuel_type values (1, 'GAS');
insert into vcdb_parts.aspiration values (1, 'Naturally Aspirated'), (2, 'Turbocharged');
insert into vcdb_config.engine_config values (4704, 1, 1, 1, 1), (4705, 1, 2, 1, 2);
-- DLX 22R en 1986 (USA y CAN) y 1987 (USA); SR5 turbo solo en 1987
insert into vcdb_base.vehicle values (1, 5001, 100, 1), (2, 5001, 100, 2), (3, 5002, 100, 1), (4, 5002, 101, 1);
insert into vcdb_config.vehicle_to_engine_config values (1, 4704), (2, 4704), (3, 4704), (4, 4705);
