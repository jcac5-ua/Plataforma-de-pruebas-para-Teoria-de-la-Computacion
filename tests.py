import unittest
from unittest import mock

import core
import encoder
import expander
import interpreter

# Códigos de error del núcleo (primer elemento de las listas de resultado)
LEXICO = -1
SINTACTICO = -2
SEMANTICO = -3
EJECUCION = -4

# Macros predefinidas: copia literal de las de main.py (que no se puede importar
# sin Qt). Lo ideal es que vivan en core.py y que los tests las importen de allí.
COPIA = ["MACRO COPIA","IF T2 != 0 GOTO G4","W1 ++","IF W1 != 0 GOTO G5","G4: T2 --","IF T2 != 0 GOTO G4","G5: IF T1 != 0 GOTO G2","W2 ++","IF W1 != 0 GOTO F","G2: T1 --","T2 ++","W3 ++","IF T1 != 0 GOTO G2","G3: W3 --","T1 ++","IF W3 != 0 GOTO G3","END"]
SALTO = ["MACRO SALTO", "W1 ++", "IF W1 != 0 GOTO T1", "END"]
SUMA = ["MACRO SUMA","IF T3 != 0 GOTO G1","CALL SALTO G2","G1: T3 --","IF T3 != 0 GOTO G1","G2: CALL COPIA T2 W2","CALL COPIA T1 T3","IF T2 != 0 GOTO G3","CALL SALTO G4","G3: T3 ++","T2 --","IF T2 != 0 GOTO G3","G4: CALL COPIA W2 T2", "END"]
RESTA = ["MACRO RESTA","CALL COPIA T1 T3","CALL COPIA T2 W1","IF T2 != 0 GOTO G1","CALL SALTO F","G1: W1 --","T3 --","IF W1 != 0 GOTO G1","END"]


class CasoBase(unittest.TestCase):
	"""Ayudantes comunes. Si mañana core.run devuelve un resultado estructurado,
	solo hay que cambiar estos métodos y no cada test."""

	def setUp(self):
		# Límite de pasos bajo: un bucle infinito falla en milisegundos y no en segundos.
		patcher = mock.patch.object(interpreter, "MAX_INSTR", 100000)
		patcher.start()
		self.addCleanup(patcher.stop)

	def analizar(self, text):
		return core.analyse_variables(list(text))

	def ejecutar(self, text, entradas=None, codificacion=False):
		text = list(text)
		variables = core.analyse_variables(text)
		self.assertGreaterEqual(variables[0], 0, f"el análisis falló: {variables}")
		return core.run(text, variables[4], variables[5], entradas or {}, codificacion)

	def valor_y(self, text, entradas=None):
		salida = self.ejecutar(text, entradas)
		self.assertIn("Result: ", salida, salida)
		return int(salida.split("Result: ")[-1])

	def assertErrorAnalisis(self, text, codigo, linea=None, fragmento=None):
		resultado = self.analizar(text)
		self.assertEqual(resultado[0], codigo, f"se esperaba el error {codigo} y se obtuvo {resultado}")
		if linea is not None:
			self.assertEqual(resultado[1], linea)
		if fragmento is not None:
			self.assertIn(fragmento, resultado[2])

	def assertSinError(self, text):
		resultado = self.analizar(text)
		self.assertEqual(resultado[0], 1, f"se esperaba éxito y se obtuvo {resultado}")


def en_macro(*lineas):
	return ["MACRO M", *lineas, "END"]


# ======================================================================================
# Programas sin macros: lo más básico del lenguaje
# ======================================================================================
class TestProgramasSinMacros(CasoBase):
	def test_incremento_simple(self):
		text = ['Y ++']
		variables = core.analyse_variables(text)
		resultado = core.run(text, variables[4], variables[5], {}, False)
		self.assertEqual(resultado, "Para los valores de entrada {}\nResult: 1")

	def test_decremento_en_cero_se_queda_en_cero(self):
		self.assertEqual(self.valor_y(["Y --"]), 0)

	def test_decremento_normal(self):
		self.assertEqual(self.valor_y(["Y ++", "Y ++", "Y --"]), 1)

	def test_operacion_igual_no_hace_nada(self):
		self.assertEqual(self.valor_y(["Y =="]), 0)

	def test_variable_de_entrada_se_lee(self):
		self.assertEqual(self.valor_y(["Y ++", "X1 --"], {"X1": 0}), 1)

	def test_if_no_salta_si_la_variable_es_cero(self):
		self.assertEqual(self.valor_y(["IF X1 != 0 GOTO A1", "Y ++", "A1: Y ++"], {"X1": 0}), 2)

	def test_if_salta_si_la_variable_no_es_cero(self):
		self.assertEqual(self.valor_y(["IF X1 != 0 GOTO A1", "Y ++", "A1: Y ++"], {"X1": 1}), 1)

	def test_copia_manual_de_davis(self):
		# Y <- X1, el programa clásico de Davis. Sale por una etiqueta (C1) que no existe.
		programa = [
			"A1: IF X1 != 0 GOTO B1",
			"Z1 ++",
			"IF Z1 != 0 GOTO C1",
			"B1: X1 --",
			"Y ++",
			"Z1 ++",
			"IF Z1 != 0 GOTO A1",
		]
		for x in (0, 1, 3, 7):
			with self.subTest(x=x):
				self.assertEqual(self.valor_y(programa, {"X1": x}), x)

	def test_salto_a_etiqueta_inexistente_termina_el_programa(self):
		# Semántica de Davis-Weyuker: GOTO a una etiqueta inexistente equivale a terminar.
		programa = ["IF X1 != 0 GOTO A9", "Y ++"]
		self.assertEqual(self.valor_y(programa, {"X1": 1}), 0)
		self.assertEqual(self.valor_y(programa, {"X1": 0}), 1)

	def test_programa_vacio(self):
		for programa in ([], [""], ["# solo un comentario"]):
			with self.subTest(programa=programa):
				self.assertEqual(self.valor_y(programa), 0)

	def test_programa_con_solo_macros(self):
		self.assertEqual(self.valor_y(COPIA + SALTO), 0)


# ======================================================================================
# A. Errores léxicos (-1)
# ======================================================================================
class TestErroresLexicos(CasoBase):
	def test_etiqueta_mal_formada_fuera_de_macro(self):
		# E1 se rechaza a propósito: el codificador no sabe tratar la etiqueta E.
		for linea in ("E1: Y ++", "A: Y ++", "A1B: Y ++", "a1: Y ++", "G1: Y ++"):
			with self.subTest(linea=linea):
				self.assertErrorAnalisis([linea], LEXICO, linea=1)

	def test_etiqueta_normal_dentro_de_macro(self):
		self.assertErrorAnalisis(en_macro("A1: T1 ++"), LEXICO)

	def test_etiqueta_de_macro_dentro_de_macro_es_valida(self):
		self.assertSinError(en_macro("G1: T1 ++"))

	# BUG CONOCIDO: los textos de los dos mensajes de etiqueta están intercambiados.
	# Cuando se corrija, quitar los decoradores.
	@unittest.expectedFailure
	def test_mensaje_etiqueta_mal_definida_fuera_de_macro_no_habla_de_macro(self):
		resultado = self.analizar(["A: Y ++"])
		self.assertNotIn("en una macro", resultado[2])

	@unittest.expectedFailure
	def test_mensaje_etiqueta_mal_definida_dentro_de_macro_habla_de_macro(self):
		resultado = self.analizar(en_macro("A1: T1 ++"))
		self.assertIn("en una macro", resultado[2])

	def test_variable_invalida(self):
		for linea in ("Q1 ++", "X ++", "x1 ++", "Y1 ++", "X1a ++", "T1 ++"):
			with self.subTest(linea=linea):
				self.assertErrorAnalisis([linea], LEXICO, fragmento="mal definida")

	def test_variable_invalida_dentro_de_macro(self):
		for linea in ("X1 ++", "Y ++", "Z1 ++"):
			with self.subTest(linea=linea):
				self.assertErrorAnalisis(en_macro(linea), LEXICO)

	def test_variables_validas_fuera_de_macro(self):
		for linea in ("Y ++", "X1 ++", "X12 ++", "Z1 --", "Z10 =="):
			with self.subTest(linea=linea):
				self.assertSinError([linea])

	def test_variables_validas_dentro_de_macro(self):
		for linea in ("T1 ++", "W1 --", "T12 =="):
			with self.subTest(linea=linea):
				self.assertSinError(en_macro(linea))

	def test_operacion_desconocida(self):
		for linea in ("Y +-", "Y **", "Y ="):
			with self.subTest(linea=linea):
				self.assertErrorAnalisis([linea], LEXICO, fragmento="desconocida")

	def test_instruccion_con_numero_de_partes_incorrecto(self):
		# Caracterización: el espaciado es rígido (un espacio exacto entre partes,
		# sin espacios al final). Documenta una limitación del tokenizador actual.
		for linea in ("Y", "Y ++ ++", "Y  ++", "Y ++ "):
			with self.subTest(linea=linea):
				self.assertErrorAnalisis([linea], LEXICO, fragmento="desconocida")

	def test_if_con_variable_invalida(self):
		self.assertErrorAnalisis(["IF W1 != 0 GOTO A1"], LEXICO, fragmento="W1")

	def test_if_con_etiqueta_invalida(self):
		for etiqueta in ("G1", "A", "T1", "E1"):
			with self.subTest(etiqueta=etiqueta):
				self.assertErrorAnalisis([f"IF Y != 0 GOTO {etiqueta}"], LEXICO, fragmento=etiqueta)

	def test_if_con_operador_invalido(self):
		self.assertErrorAnalisis(["IF Y == 0 GOTO A1"], LEXICO, fragmento="desconocida")

	def test_if_con_palabra_clave_invalida(self):
		self.assertErrorAnalisis(["IF Y != 0 JUMP A1"], LEXICO, fragmento="desconocida")

	def test_if_dentro_de_macro_invalido(self):
		for linea in ("IF Y != 0 GOTO G1", "IF T1 != 0 GOTO A1", "IF T1 != 0 GOTO W1"):
			with self.subTest(linea=linea):
				self.assertErrorAnalisis(en_macro(linea), LEXICO)

	def test_if_dentro_de_macro_valido(self):
		for linea in ("IF T1 != 0 GOTO T2", "IF W1 != 0 GOTO F", "IF T1 != 0 GOTO G1"):
			with self.subTest(linea=linea):
				self.assertSinError(en_macro(linea))


# ======================================================================================
# B. Errores sintácticos (-2)
# ======================================================================================
class TestErroresSintacticos(CasoBase):
	def test_if_con_partes_de_mas(self):
		self.assertErrorAnalisis(["IF Y != 0 GOTO A1 A2"], SINTACTICO, fragmento="Sobran parámetros")

	def test_if_con_partes_de_menos(self):
		self.assertErrorAnalisis(["IF Y != 0"], SINTACTICO, fragmento="Faltan parámetros")

	def test_if_sola(self):
		self.assertErrorAnalisis(["IF"], SINTACTICO, fragmento="Faltan parámetros")

	def test_macro_anidada(self):
		self.assertErrorAnalisis(["MACRO A", "MACRO B", "END", "END"], SINTACTICO, fragmento="dentro de otra")

	def test_macro_con_parametros_de_mas(self):
		self.assertErrorAnalisis(["MACRO A B", "END"], SINTACTICO, fragmento="Sobran parámetros")

	def test_end_sin_macro(self):
		self.assertErrorAnalisis(["END"], SINTACTICO, fragmento="sin haber definido")

	def test_macro_sin_end(self):
		self.assertErrorAnalisis(["MACRO M", "T1 ++"], SINTACTICO, fragmento="END")

	def test_call_sin_argumentos(self):
		self.assertErrorAnalisis(["CALL COPIA"], SINTACTICO, fragmento="COPIA")


# ======================================================================================
# Numeración de líneas: caracterización
# ======================================================================================
class TestNumeroDeLinea(CasoBase):
	def test_el_analizador_no_cuenta_comentarios_ni_lineas_vacias(self):
		# Caracterización: hoy el contador solo cuenta instrucciones.
		resultado = self.analizar(["# comentario", "", "", "Y ++", "Q ++"])
		self.assertEqual(resultado[:2], [LEXICO, 2])

	def test_el_analizador_no_cuenta_la_linea_macro(self):
		# Caracterización: la línea MACRO no suma, y END sí. Línea del editor: 6.
		resultado = self.analizar(["# c", "", "MACRO M", "T1 ++", "END", "IF Y != 0 GOTO A1 A2"])
		self.assertEqual(resultado[:2], [SINTACTICO, 3])

	# BUG CONOCIDO: el usuario ve en su editor otra línea distinta de la que se informa.
	@unittest.expectedFailure
	def test_la_linea_reportada_es_la_del_editor(self):
		resultado = self.analizar(["# comentario", "", "", "Y ++", "Q ++"])
		self.assertEqual(resultado[:2], [LEXICO, 5])

	def test_el_expansor_numera_por_posicion_en_el_texto(self):
		# El expansor usa otra numeración: aquí sí coincide con la línea del editor.
		salida = self.ejecutar(["# comentario", "MACRO M", "T3 ++", "END", "CALL M X1"], {"X1": 1})
		self.assertIn("Error semántico en la línea 3", salida)


# ======================================================================================
# D. Errores semánticos (-3), pasan por run
# ======================================================================================
class TestErroresSemanticos(CasoBase):
	def test_macro_no_definida(self):
		salida = self.ejecutar(["CALL NOEXISTE X1"], {"X1": 1})
		self.assertIn("Error semántico en la línea 1", salida)
		self.assertIn("NOEXISTE", salida)

	def test_argumento_no_declarado(self):
		salida = self.ejecutar(en_macro("T3 ++") + ["CALL M X1"], {"X1": 1})
		self.assertIn("Error semántico", salida)
		self.assertIn("En la macro 'M'", salida)
		self.assertIn("T3", salida)

	def test_argumento_no_declarado_con_llamada_de_dos_argumentos(self):
		salida = self.ejecutar(en_macro("T1 ++", "T3 ++") + ["CALL M X1 X2"], {"X1": 1, "X2": 1})
		self.assertIn("Error semántico en la línea 3", salida)
		self.assertIn("T3", salida)

	def test_argumento_no_declarado_en_if(self):
		salida = self.ejecutar(en_macro("IF T3 != 0 GOTO T1") + ["CALL M X1"], {"X1": 1})
		self.assertIn("Error semántico", salida)
		self.assertIn("T3", salida)

	def test_error_tras_la_expansion_se_distingue_del_error_del_usuario(self):
		# Pasan la primera validación y fallan en la segunda: el fallo es del
		# resultado de la expansión, no del texto escrito por el usuario.
		casos = [
			(en_macro("IF T1 != 0 GOTO T2") + ["CALL M X1 Q9"], {"X1": 1}),
			(en_macro("T1 ++") + ["CALL M Q9"], {}),
			(en_macro("T1 ++") + ["CALL M 5"], {}),
		]
		for programa, entradas in casos:
			with self.subTest(programa=programa):
				salida = self.ejecutar(programa, entradas)
				self.assertTrue(salida.startswith("Después de la expansión"), salida)
				self.assertIn("Error léxico", salida)
				self.assertIn("De la expansión:", salida)


# ======================================================================================
# E. Error de ejecución (-4)
# ======================================================================================
class TestErrorDeEjecucion(CasoBase):
	def test_bucle_infinito_alcanza_el_limite_de_pasos(self):
		with mock.patch.object(interpreter, "MAX_INSTR", 50):
			salida = self.ejecutar(["A1: Y ++", "IF Y != 0 GOTO A1"])
		self.assertIn("Error de ejecución", salida)
		self.assertIn("(50)", salida)

	def test_execute_devuelve_el_codigo_de_error(self):
		with mock.patch.object(interpreter, "MAX_INSTR", 20):
			resultado = interpreter.execute(["INC Y", "JMP Y A1", "HALT"], {"A1": 0}, {})
		self.assertEqual(resultado[0], EJECUCION)
		self.assertIn("(20)", resultado[2])

	def test_un_programa_corto_no_alcanza_el_limite(self):
		with mock.patch.object(interpreter, "MAX_INSTR", 50):
			self.assertEqual(self.valor_y(["Y ++"]), 1)

	def test_execute_devuelve_y(self):
		self.assertEqual(interpreter.execute(["INC Y", "INC Y", "HALT"], {}, {}), [2])
		self.assertEqual(interpreter.execute(["HALT"], {}, {}), [0])


# ======================================================================================
# C. Robustez: ninguna entrada debería lanzar una excepción
# ======================================================================================
class TestRobustez(CasoBase):
	# BUG CONOCIDO: lanzan IndexError. Cuando se corrija, quitar los decoradores.
	@unittest.expectedFailure
	def test_call_sola_no_lanza_excepcion(self):
		self.assertLess(self.analizar(["CALL"])[0], 0)

	@unittest.expectedFailure
	def test_macro_sola_no_lanza_excepcion(self):
		self.assertLess(self.analizar(["MACRO"])[0], 0)

	@unittest.expectedFailure
	def test_linea_con_un_solo_espacio_no_lanza_excepcion(self):
		self.assertLess(self.analizar([" "])[0], 0)

	def test_dos_puntos_solos_son_error_lexico(self):
		self.assertErrorAnalisis([":"], LEXICO)

	def test_etiqueta_sola_es_valida(self):
		self.assertSinError(["A1:"])


# ======================================================================================
# F. Comportamientos silenciosos: tests de caracterización
# ======================================================================================
class TestComportamientosSilenciosos(CasoBase):
	def test_etiqueta_repetida_gana_la_primera(self):
		programa = ["IF X1 != 0 GOTO A1", "A1: Y ++", "Y ++", "Y ++", "A1: Y ++"]
		self.assertEqual(self.valor_y(programa, {"X1": 1}), 4)

	def test_macro_repetida_gana_la_primera(self):
		programa = en_macro("T1 ++") + ["MACRO M", "T1 ++", "T1 ++", "END", "CALL M Y"]
		self.assertEqual(self.valor_y(programa), 1)

	def test_argumentos_sobrantes_se_ignoran(self):
		programa = en_macro("T1 ++") + ["CALL M Y X5", "Y ++"]
		self.assertEqual(self.valor_y(programa, {"X5": 0}), 2)

	def test_macro_definida_despues_de_su_uso_no_se_expande(self):
		# Caracterización: el expansor solo mira después del último END, así que la
		# llamada queda sin expandir y se ignora sin avisar. Decisión de diseño pendiente:
		# ¿error semántico, o expandir también hacia atrás?
		programa = ["CALL M Y"] + en_macro("T1 ++")
		self.assertEqual(self.valor_y(programa), 0)

	# BUG CONOCIDO: el expansor solo reconoce líneas que empiezan por CALL; si la
	# llamada lleva etiqueta, no se expande. Afecta a SUMA ("G2: CALL COPIA T2 W2").
	@unittest.expectedFailure
	def test_llamada_con_etiqueta_se_expande(self):
		programa = ["MACRO A", "T1 ++", "END", "MACRO B", "G1: CALL A T1", "END", "CALL B Y"]
		self.assertEqual(self.valor_y(programa), 1)

	# BUG CONOCIDO: una macro vacía deja un END de más tras expandirse.
	@unittest.expectedFailure
	def test_macro_vacia(self):
		programa = ["MACRO M", "END", "CALL M X1", "Y ++"]
		self.assertEqual(self.valor_y(programa, {"X1": 1}), 1)

	def test_macro_que_llama_a_otra_macro(self):
		programa = ["MACRO A", "T1 ++", "END", "MACRO B", "CALL A T1", "CALL A T1", "END", "CALL B Y"]
		self.assertEqual(self.valor_y(programa), 2)

	def test_definir_una_macro_con_salto_no_altera_el_resultado(self):
		programa = SALTO + ["Y ++"]
		self.assertEqual(self.valor_y(programa), 1)

	def test_etiquetas_tras_definir_una_macro_apuntan_a_su_instruccion(self):
		programa = en_macro("T1 ++") + [
			"A1: IF X1 != 0 GOTO B1",
			"IF Z1 != 0 GOTO C1",
			"B1: X1 --",
			"CALL M Y",
			"IF X1 != 0 GOTO B1",
			"C1: Z1 ++",
		]
		self.assertEqual(self.valor_y(programa, {"X1": 4}), 4)


# ======================================================================================
# G. Oráculos: las macros deben calcular lo mismo que Python
# ======================================================================================
# Los oráculos también deben comprobar los efectos laterales: las macros de Davis
# conservan sus operandos (solo cambia la variable de salida).
class TestMacrosOraculos(CasoBase):
	def test_copia(self):
		for x in (0, 1, 5):
			with self.subTest(x=x):
				self.assertEqual(self.valor_y(COPIA + ["CALL COPIA X1 Y"], {"X1": x}), x)

	def test_suma(self):
		for x, y in ((0, 0), (0, 3), (3, 0), (2, 3), (5, 1)):
			with self.subTest(x=x, y=y):
				programa = COPIA + SALTO + SUMA + ["CALL SUMA X1 X2 Y"]
				self.assertEqual(self.valor_y(programa, {"X1": x, "X2": y}), x + y)

	# BUG CONOCIDO: SUMA contiene "G2: CALL COPIA T2 W2" (llamada con etiqueta), que no se
	# expande, así que X2 se consume. test_suma no lo detecta porque solo mira Y.
	@unittest.expectedFailure
	def test_suma_conserva_sus_operandos(self):
		for x, y in ((2, 3), (0, 4), (3, 0)):
			with self.subTest(x=x, y=y):
				programa = COPIA + SALTO + SUMA + ["CALL SUMA X1 X2 Z1", "CALL COPIA X2 Y"]
				self.assertEqual(self.valor_y(programa, {"X1": x, "X2": y}), y)

	def test_resta_es_truncada_a_cero(self):
		# Resta natural: x - y si x >= y, y 0 en otro caso (la de Davis).
		for x, y in ((0, 0), (0, 3), (3, 0), (5, 2), (2, 5), (4, 4)):
			with self.subTest(x=x, y=y):
				programa = COPIA + SALTO + RESTA + ["CALL RESTA X1 X2 Y"]
				self.assertEqual(self.valor_y(programa, {"X1": x, "X2": y}), max(x - y, 0))

	def test_salto_incondicional(self):
		programa = SALTO + ["CALL SALTO A1", "Y ++", "A1: Y ++"]
		self.assertEqual(self.valor_y(programa), 1)


# ======================================================================================
# Expansor (nivel de fase, sin pasar por run)
# ======================================================================================
class TestExpansor(CasoBase):
	def expandir(self, text):
		variables = self.analizar(text)
		self.assertGreaterEqual(variables[0], 0, variables)
		resultado = expander.expander(list(text), variables[4], variables[5])
		self.assertEqual(resultado[0], 1, resultado)
		return resultado[1]

	def principal(self, codigo):
		"""Líneas posteriores al último END: lo que no son definiciones de macros."""
		ultimo_end = max(i for i, linea in enumerate(codigo) if linea == "END")
		return codigo[ultimo_end + 1:]

	def etiquetas_definidas(self, codigo):
		definidas = []
		for linea in self.principal(codigo):
			primera = linea.split(" ")[0]
			if primera.endswith(":"):
				definidas.append(primera)
		return definidas

	def test_sin_llamadas_el_codigo_no_cambia(self):
		self.assertEqual(self.expandir(["Y ++"]), ["Y ++"])

	def test_la_llamada_se_sustituye_por_el_cuerpo(self):
		codigo = self.expandir(en_macro("T1 ++", "T1 ++") + ["CALL M Y"])
		self.assertEqual(self.principal(codigo), ["Y ++", "Y ++", "A1:", "#Fin de la macro expandida M"])

	def test_dos_llamadas_generan_etiquetas_distintas(self):
		codigo = self.expandir(en_macro("G1: T1 ++") + ["CALL M Y", "CALL M Y"])
		etiquetas = self.etiquetas_definidas(codigo)
		self.assertEqual(len(etiquetas), len(set(etiquetas)), etiquetas)

	def test_las_etiquetas_nuevas_no_chocan_con_las_del_usuario(self):
		codigo = self.expandir(en_macro("G1: T1 ++") + ["A1: Y ++", "CALL M Y"])
		etiquetas = self.etiquetas_definidas(codigo)
		self.assertEqual(len(etiquetas), len(set(etiquetas)), etiquetas)
		self.assertEqual(etiquetas.count("A1:"), 1)

	def test_dos_llamadas_usan_auxiliares_distintos(self):
		codigo = self.expandir(en_macro("W1 ++") + ["CALL M Y", "CALL M Y"])
		self.assertIn("Z1 ++", codigo)
		self.assertIn("Z2 ++", codigo)

	def test_el_auxiliar_nuevo_no_reutiliza_el_del_usuario(self):
		codigo = self.expandir(en_macro("W1 ++") + ["Z1 ++", "CALL M Y"])
		self.assertEqual(codigo.count("Z1 ++"), 1)
		self.assertIn("Z2 ++", codigo)

	def test_los_argumentos_se_sustituyen_por_posicion(self):
		codigo = self.expandir(en_macro("T2 ++", "T1 --") + ["CALL M X1 X2"])
		self.assertEqual(self.principal(codigo)[:2], ["X2 ++", "X1 --"])


# ======================================================================================
# H. Detección de variables y contrato posicional de analyse_variables
# ======================================================================================
class TestDeteccionDeVariables(CasoBase):
	def test_estructura_del_resultado_exitoso(self):
		# Contrato posicional actual: [ok, entradas, programa, etiquetas, auxiliares, etiquetas usadas]
		self.assertEqual(self.analizar(["Y ++"]), [1, [], ["INC Y", "HALT"], {}, [], []])

	def test_sin_duplicados_y_en_orden_de_aparicion(self):
		self.assertEqual(self.analizar(["X1 ++", "X2 ++", "X1 --"])[1], ["X1", "X2"])

	def test_entrada_detectada_a_traves_de_un_call(self):
		self.assertEqual(self.analizar(en_macro("T1 ++") + ["CALL M X1 Z1"])[1], ["X1"])

	def test_entrada_detectada_en_un_if(self):
		self.assertEqual(self.analizar(["IF X3 != 0 GOTO A1"])[1], ["X3"])

	def test_y_no_es_una_entrada(self):
		self.assertEqual(self.analizar(["Y ++"])[1], [])

	def test_las_etiquetas_se_registran_con_su_posicion(self):
		variables = self.analizar(["A1: Y ++", "B2: Y ++"])
		self.assertEqual(variables[3], {"A1": 0, "B2": 1})
		self.assertEqual(variables[5], ["A1", "B2"])

	def test_etiqueta_repetida_conserva_la_primera_posicion(self):
		self.assertEqual(self.analizar(["A1: Y ++", "Y ++", "A1: Y ++"])[3]["A1"], 0)

	def test_auxiliar_de_una_cifra(self):
		self.assertEqual(self.analizar(["Z3 ++"])[4], ["3"])

	def test_auxiliar_de_dos_cifras_via_call_guarda_el_numero_completo(self):
		self.assertEqual(self.analizar(en_macro("T1 ++") + ["CALL M Z10"])[4], ["10"])

	# BUG CONOCIDO: la lista de auxiliares se calcula de tres formas distintas
	# (var[1], var[1:] y una comparación que nunca coincide). El expansor usa esa
	# lista para no reutilizar nombres, así que puede acabar generando un Z que choque.
	@unittest.expectedFailure
	def test_auxiliar_de_dos_cifras_guarda_el_numero_completo(self):
		self.assertEqual(self.analizar(["Z10 ++"])[4], ["10"])

	@unittest.expectedFailure
	def test_auxiliar_de_dos_cifras_en_if_guarda_el_numero_completo(self):
		self.assertEqual(self.analizar(["IF Z12 != 0 GOTO A1"])[4], ["12"])

	@unittest.expectedFailure
	def test_auxiliar_repetido_no_se_duplica(self):
		self.assertEqual(self.analizar(["Z1 ++", "Z1 ++"])[4], ["1"])


# ======================================================================================
# Codificación de Gödel
# ======================================================================================
class TestCodificacion(CasoBase):
	def test_num_pair_es_biyectiva_con_l_y_r(self):
		for a in range(6):
			for b in range(6):
				with self.subTest(a=a, b=b):
					n = encoder.num_pair(a, b)
					self.assertEqual(encoder.l(n), a)
					self.assertEqual(encoder.r(n), b)

	def test_codigos_de_instruccion_de_davis(self):
		self.assertEqual(encoder.codificar_I(0, 1, 0), 2)    # Y <- Y + 1
		self.assertEqual(encoder.codificar_I(1, 2, 1), 45)   # [A1] X1 <- X1 - 1
		self.assertEqual(encoder.codificar_I(0, 3, 1), 46)   # IF X1 != 0 GOTO A1

	def test_codificar_programa(self):
		self.assertEqual(encoder.codificar_P([]), 0)
		self.assertEqual(encoder.codificar_P([2]), 3)         # 2**2 - 1

	def test_primos(self):
		self.assertEqual([encoder.enesimo_primo(n) for n in range(1, 6)], [2, 3, 5, 7, 11])
		self.assertFalse(encoder.es_primo(1))
		self.assertTrue(encoder.es_primo(13))

	def test_codigo_de_variables_y_etiquetas(self):
		self.assertEqual([encoder.var(v) for v in ("Y", "X1", "Z1", "X2", "Z2")], [0, 1, 2, 3, 4])
		self.assertEqual([encoder.etiq(e) for e in ("A1", "B1", "C1", "D1", "S1", "A2")], [1, 2, 3, 4, 5, 6])

	# BUG CONOCIDO: var y etiq solo leen una cifra del índice (line[1]), así que
	# Z10, X12 o A10 se codifican como Z1, X1 y A1.
	@unittest.expectedFailure
	def test_codigo_de_variables_con_indice_de_dos_cifras(self):
		self.assertEqual(encoder.var("Z10"), 20)
		self.assertEqual(encoder.var("X12"), 23)

	@unittest.expectedFailure
	def test_codigo_de_etiquetas_con_indice_de_dos_cifras(self):
		self.assertEqual(encoder.etiq("A10"), 46)

	def test_el_codificador_ignora_las_definiciones_de_macros(self):
		codigo = en_macro("T1 ++") + ["Y ++"]
		self.assertEqual(encoder.encoder(codigo), "1 : Y ++ => [0, [1, 0]] #I = 2\n")

	def test_codificacion_dentro_de_run(self):
		salida = self.ejecutar(["Y ++"], codificacion=True)
		self.assertEqual(salida, "Codificación:\n1 : Y ++ => [0, [1, 0]] #I = 2\n\nPara los valores de entrada {}\nResult: 1")

	def test_codificacion_con_etiqueta_e_if(self):
		salida = self.ejecutar(["A1: X1 --", "IF X1 != 0 GOTO A1"], {"X1": 1}, codificacion=True)
		self.assertIn("1 : A1: X1 -- => [1, [2, 1]] #I = 45", salida)
		self.assertIn("2 : IF X1 != 0 GOTO A1 => [0, [3, 1]] #I = 46", salida)

	def test_sin_codificacion_no_aparece(self):
		self.assertNotIn("Codificación", self.ejecutar(["Y ++"], codificacion=False))


# ======================================================================================
# Efectos secundarios: requisitos de testabilidad del núcleo
# ======================================================================================
class TestEfectosSecundarios(CasoBase):
	# BUG CONOCIDO: el expansor modifica en sitio la lista que recibe, así que
	# llamar dos veces a run con el mismo texto no es seguro.
	@unittest.expectedFailure
	def test_run_no_modifica_el_texto_de_entrada(self):
		texto = en_macro("T1 ++") + ["CALL M Y"]
		copia = list(texto)
		variables = core.analyse_variables(texto)
		core.run(texto, variables[4], variables[5], {}, False)
		self.assertEqual(texto, copia)

	def test_analyse_variables_no_modifica_el_texto_de_entrada(self):
		texto = en_macro("T1 ++") + ["CALL M Y"]
		copia = list(texto)
		core.analyse_variables(texto)
		self.assertEqual(texto, copia)

	def test_dos_ejecuciones_independientes_dan_lo_mismo(self):
		programa = en_macro("T1 ++") + ["CALL M Y", "Y ++"]
		self.assertEqual(self.ejecutar(programa), self.ejecutar(programa))


if __name__ == '__main__':
	unittest.main()