-- SOLO PARA PRUEBAS LOCALES (sin acceso a AutoCare). Con acceso real usar db/ref/cargar_ref.py.
-- Reales: part_terminology 2172/6708, PAdb 267/268/269/5061/302, regiones 1/13/21, uom MM.
-- Sintéticos (NO son de AutoCare): make/model/base_vehicle (8xx/9xxx), valid_value 990001-2.

insert into ref.version (base, version, publicacion) values ('VCdb','2.0','2026-07-30'), ('PCdb','2.0','2026-07-30'), ('PAdb','5.0','2026-07-30');
insert into ref.part_terminology values (2172, 'Radiator'), (6708, 'A/C Condenser');
insert into ref.atributo_permitido (part_terminology_id, paid, nombre, requiere_uom) values
  (2172, 267, 'Core Height', true), (2172, 268, 'Core Thickness', true), (2172, 269, 'Core Width', true),
  (2172, 5061, 'Core Row Quantity', false), (2172, 302, 'Core Material', false);
insert into ref.valor_permitido values (2172, 302, 990001, 'Aluminum'), (2172, 302, 990002, 'Copper/Brass');
insert into ref.uom values ('MM', 'Millimeter');
insert into ref.region values (1, 'USA', 'United States'), (13, 'GTM', 'Guatemala'), (21, 'SLV', 'El Salvador');
insert into ref.make values (901, 'Suzuki'), (902, 'Hyundai'), (903, 'Changan');
insert into ref.model values (9101, 'Grand Vitara'), (9102, 'CS35');
insert into ref.base_vehicle select 800000 + y, y, 901, 9101 from generate_series(2005, 2015) y;
insert into ref.base_vehicle select 810000 + y, y, 903, 9102 from generate_series(2017, 2020) y;
insert into ref.equipment_base values (700001);
