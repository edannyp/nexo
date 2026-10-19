-- SOLO PARA PRUEBAS LOCALES (sin acceso a AutoCare). Con acceso real usar db/ref/cargar_ref.py.
-- Reales: regiones 1/13/21. Sintéticos (NO son de AutoCare): make/model/base_vehicle/mfr/equipment.

insert into ref.version (base, version, publicacion) values ('VCdb','2.0','2026-07-30');
insert into ref.region values (1, 'USA', 'United States'), (13, 'GTM', 'Guatemala'), (21, 'SLV', 'El Salvador');
insert into ref.vehicle_type values (5, 'Car');
insert into ref.make (make_id, make_name) values (901, 'Suzuki'), (903, 'Changan');
insert into ref.model (model_id, model_name) values (9101, 'Grand Vitara'), (9102, 'CS35');
insert into ref.base_vehicle select 800000 + y, y, 901, 9101 from generate_series(2005, 2015) y;
insert into ref.base_vehicle select 810000 + y, y, 903, 9102 from generate_series(2017, 2020) y;
insert into ref.mfr (mfr_id, mfr_name) values (601, 'Perkins Engines Company Ltd'), (602, 'Cummins');
insert into ref.equipment_model (equipment_model_id, equipment_model_name) values (6501, '1104C-44T');
insert into ref.equipment_base values (700001, 601, 6501);
