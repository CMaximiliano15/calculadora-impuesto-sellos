*Este DO toma la base original de sellos y le aplica modificaciones para estandarizarla y corregir errores. La salida de esta base es base_sellos_portal_v03.dta

cap use "G:\Mi unidad\Facultad (Eco)\CEFIP\Calculadora Sellos\Backup\base_sellos_portal_v01.dta"

* Corrección de nombres 

replace actividad="Actos, contratos y operaciones que abonen Cuotas Fijas" if actividad=="Actos, Contratos y Operaciones que Abonen Cuotas Fijas" | actividad=="Actos contratos y operacones que abonen cuotas fijas"
replace actividad="Actos, contratos y operaciones sobre inmuebles" if actividad=="Actos,contratos y operaciones sobre inmuebles"
replace actividad="Operaciones de tipo comercial y bancario" if actividad=="Operaciones de Tipo Comercial y Bancario"


* Estandarización de monto_fijo
replace monto_fijo =. if monto_fijo==0


* Correccion de alicuotas

*Comentario: al realizar sum alicuota se encuentran valores máximos de 100

*La forma de modificar las alicuotas es la siguiente:
** 1. Se filtran aquellas alicuotas que son mayores a 1
** 2. Las alícuotas que son mayores a 10 (por ejemplo 30, 40 100) se dividen por 1000. Las alícuotas que son mayores a 1 y menores a 10 se dividen por 100
** Por ejemplo, si alicuota= 30 -> alicuota* = 0.03 (3%)
** 				si alicuota= 1.3 -> alicuota* = 0.013 (1.3%)


replace alicuota = alicuota/1000 if alicuota>=10
replace alicuota = alicuota/100 if alicuota>=1 & alicuota<10

cap save "G:\Mi unidad\Facultad (Eco)\CEFIP\Calculadora Sellos\base_sellos_portal_v03.dta"