import unittest
from unittest import mock

import core
import encoder
import expander
import interpreter

# Convenciones:
#  - Los tests marcados con @unittest.expectedFailure documentan un fallo conocido
#    o sospechado. Cuando se arregle el codigo, saldran como "unexpected success"
#    y habra que quitar el decorador.
#  - Los tests de "caracterizacion" fijan lo que el codigo hace HOY, aunque quiza
#    no sea lo ideal. Si cambias el comportamiento a proposito, actualizalos.

# ---------------------------------------------------------------------------
# Biblioteca de macros (copiada de main.py; deberia vivir en core)
# ---------------------------------------------------------------------------
COPIA = ["MACRO COPIA", "IF T2 != 0 GOTO G4", "W1 ++", "IF W1 != 0 GOTO G5", "G4: T2 --", "IF T2 != 0 GOTO G4", "G5: IF T1 != 0 GOTO G2", "W2 ++", "IF W1 != 0 GOTO F", "G2: T1 --", "T2 ++", "W3 ++", "IF T1 != 0 GOTO G2", "G3: W3 --", "T1 ++", "IF W3 != 0 GOTO G3", "END"]
SUMA = ["MACRO SUMA", "IF T3 != 0 GOTO G1", "CALL SALTO G2", "G1: T3 --", "IF T3 != 0 GOTO G1", "G2: CALL COPIA T2 W2", "CALL COPIA T1 T3", "IF T2 != 0 GOTO G3", "CALL SALTO G4", "G3: T3 ++", "T2 --", "IF T2 != 0 GOTO G3", "G4: CALL COPIA W2 T2", "END"]
SALTO = ["MACRO SALTO", "W1 ++", "IF W1 != 0 GOTO T1", "END"]
RESTA = ["MACRO RESTA", "CALL COPIA T1 T3", "CALL COPIA T2 W1", "IF T2 != 0 GOTO G1", "CALL SALTO F", "G1: W1 --", "T3 --", "IF W1 != 0 GOTO G1", "END"]

MACROS_COPIA = COPIA
MACROS_SALTO = SALTO
MACROS_SUMA = COPIA + SALTO + SUMA
MACROS_RESTA = COPIA + SALTO + RESTA

VALORES = [0, 1, 2, 5]


# ---------------------------------------------------------------------------
# Ayudantes. Cuando run() devuelva un resultado estructurado, solo habra que
# cambiar estas funciones, no los tests.
# ---------------------------------------------------------------------------
def programa(macros, *lineas):
	return "\n".join(list(macros) + list(lineas))


def analizar(texto):
	return core.analyse_variables(texto.split("\n"))


def ejecutar(texto, entradas=None, codificar=False):
	lineas = texto.split("\n")
	variables = core.analyse_variables(lineas)
	if variables[0] < 0:
		raise AssertionError(f"El analisis fallo antes de ejecutar: {variables}")
	return core.run(lineas, variables[4], variables[5], entradas or {}, codificar)


def valor(texto, entradas=None):
	salida = ejecutar(texto, entradas)
	if "Result: " not in salida:
		raise AssertionError(f"No hay resultado, salida: {salida!r}")
	return int(salida.rsplit("Result: ", 1)[1])


# ---------------------------------------------------------------------------
# A. Errores lexicos (-1)
# ---------------------------------------------------------------------------
class TestLexico(unittest.TestCase):
	def test_etiqueta_mal_formada_fuera_de_macro(self):
		for prog in ["E1: Y ++", "A: Y ++", "A1B: Y ++", "a1: Y ++", "G1: Y ++"]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_etiqueta_de_programa_dentro_de_macro(self):
		self.assertEqual(analizar("MACRO M\nA1: T1 ++\nEND")[0], -1)

	def test_variable_invalida_fuera_de_macro(self):
		for prog in ["Q1 ++", "X ++", "x1 ++", "Y1 ++", "X1a ++", "T1 ++", "W1 ++"]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_variable_invalida_dentro_de_macro(self):
		for prog in ["MACRO M\nX1 ++\nEND", "MACRO M\nY ++\nEND", "MACRO M\nZ1 ++\nEND"]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_operacion_desconocida(self):
		for prog in ["Y +-", "Y **", "Y ="]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_numero_de_partes_en_instruccion_simple(self):
		# Caracterizacion: el espaciado es rigido (un solo espacio, sin espacios finales)
		for prog in ["Y", "Y ++ ++", "Y  ++", "Y ++ "]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_if_con_variable_o_etiqueta_invalida(self):
		for prog in ["IF W1 != 0 GOTO A1", "IF Y != 0 GOTO G1", "IF Y != 0 GOTO A", "IF Q != 0 GOTO A1"]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_if_con_operador_o_palabra_clave_invalida(self):
		for prog in ["IF Y == 0 GOTO A1", "IF Y != 0 JUMP A1"]:
			with self.subTest(prog=prog):
				self.assertEqual(analizar(prog)[0], -1)

	def test_if_invalido_dentro_de_macro(self):
		for cuerpo in ["IF Y != 0 GOTO G1", "IF T1 != 0 GOTO A1", "IF X1 != 0 GOTO G1"]:
			with self.subTest(cuerpo=cuerpo):
				self.assertEqual(analizar(f"MACRO M\n{cuerpo}\nEND")[0], -1)

	def test_if_valido_dentro_de_macro(self):
		for cuerpo in ["IF T1 != 0 GOTO T2", "IF W1 != 0 GOTO F", "IF T1 != 0 GOTO G1", "IF W1 != 0 GOTO G2"]:
			with self.subTest(cuerpo=cuerpo):
				self.assertEqual(analizar(f"MACRO M\n{cuerpo}\nEND")[0], 1)

	@unittest.expectedFailure
	def test_mensaje_etiqueta_fuera_de_macro_no_dice_en_una_macro(self):
		# Los mensajes de los dos casos de etiqueta parecen intercambiados
		mensaje = analizar("E1: Y ++")[2]
		self.assertNotIn("en una macro", mensaje)

	@unittest.expectedFailure
	def test_linea_reportada_es_la_linea_real_del_texto(self):
		# Ideal: la linea 4. Hoy el contador salta comentarios y lineas vacias
		resultado = analizar("#comentario\n\nY ++\nQ1 ++")
		self.assertEqual(resultado[0], -1)
		self.assertEqual(resultado[1], 4)


# ---------------------------------------------------------------------------
# B. Errores sintacticos (-2)
# ---------------------------------------------------------------------------
class TestSintactico(unittest.TestCase):
	def test_errores_sintacticos(self):
		casos = {
			"IF con partes de mas": "IF Y != 0 GOTO A1 A2",
			"IF con partes de menos": "IF Y != 0",
			"IF sola": "IF",
			"macro anidada": "MACRO A\nMACRO B\nEND\nEND",
			"MACRO con parametros de mas": "MACRO A B\nEND",
			"END sin MACRO": "END",
			"MACRO sin END": "MACRO M\nT1 ++",
			"CALL sin argumentos": "CALL COPIA",
		}
		for nombre, prog in casos.items():
			with self.subTest(nombre):
				self.assertEqual(analizar(prog)[0], -2)


# ---------------------------------------------------------------------------
# C. Robustez: ninguna entrada deberia lanzar excepcion
# ---------------------------------------------------------------------------
class TestRobustez(unittest.TestCase):
	@unittest.expectedFailure
	def test_call_sola_da_error_limpio(self):
		self.assertLess(analizar("CALL")[0], 0)

	@unittest.expectedFailure
	def test_macro_sola_da_error_limpio(self):
		self.assertLess(analizar("MACRO")[0], 0)

	@unittest.expectedFailure
	def test_linea_de_un_solo_espacio_da_error_limpio(self):
		self.assertLess(analizar(" ")[0], 0)

	def test_etiqueta_sin_nombre(self):
		self.assertEqual(analizar(":")[0], -1)

	def test_etiqueta_sola_es_valida(self):
		self.assertEqual(analizar("A1:")[0], 1)


# ---------------------------------------------------------------------------
# D. Errores semanticos (-3) y errores tras la expansion
# ---------------------------------------------------------------------------
class TestSemantico(unittest.TestCase):
	def test_macro_no_definida(self):
		salida = ejecutar("CALL NOEXISTE X1", {"X1": 0})
		self.assertIn("semántico", salida)
		self.assertIn("NOEXISTE", salida)

	def test_argumento_de_macro_no_declarado(self):
		prog = "MACRO M\nT1 ++\nT3 ++\nEND\nCALL M X1 X2"
		salida = ejecutar(prog, {"X1": 0, "X2": 0})
		self.assertIn("semántico", salida)
		self.assertIn("T3", salida)
		self.assertIn("'M'", salida)

	def test_etiqueta_invalida_como_argumento_falla_tras_la_expansion(self):
		salida = ejecutar(programa(MACROS_SALTO, "CALL SALTO Q9"))
		self.assertTrue(salida.startswith("Después de la expansión"), salida)
		self.assertIn("léxico", salida)

	def test_numero_como_variable_falla_tras_la_expansion(self):
		salida = ejecutar(programa(MACROS_COPIA, "CALL COPIA X1 5"), {"X1": 3})
		self.assertTrue(salida.startswith("Después de la expansión"), salida)


# ---------------------------------------------------------------------------
# E. Error de ejecucion (-4)
# ---------------------------------------------------------------------------
class TestEjecucion(unittest.TestCase):
	def test_limite_de_instrucciones(self):
		with mock.patch.object(interpreter, "MAX_INSTR", 50):
			salida = ejecutar("A1: Y ++\nIF Y != 0 GOTO A1")
		self.assertIn("Error de ejecución", salida)
		self.assertIn("(50)", salida)

	def test_programa_sencillo(self):
		self.assertEqual(valor("Y ++\nY ++\nY --"), 1)

	def test_decremento_no_baja_de_cero(self):
		self.assertEqual(valor("Y --\nY --"), 0)

	def test_bucle_con_if(self):
		# Y = X1 mediante bucle
		prog = "A1: IF X1 != 0 GOTO B1\nIF Z1 != 0 GOTO C1\nB1: X1 --\nY ++\nIF X1 != 0 GOTO B1\nC1: Y ++\nY --"
		self.assertEqual(valor(prog, {"X1": 4}), 4)


# ---------------------------------------------------------------------------
# F. Comportamientos silenciosos (caracterizacion: fijan lo que ocurre hoy)
# ---------------------------------------------------------------------------
class TestSilenciosos(unittest.TestCase):
	def test_salto_a_etiqueta_inexistente_termina_sin_error(self):
		self.assertEqual(valor("Y ++\nIF Y != 0 GOTO A9"), 1)

	def test_etiqueta_repetida_prevalece_la_primera(self):
		prog = "X1 ++\nIF X1 != 0 GOTO A1\nY ++\nA1: Y ++\nA1: Y ++"
		self.assertEqual(valor(prog, {"X1": 0}), 2)

	def test_dos_macros_con_el_mismo_nombre_usa_la_primera(self):
		prog = "MACRO M\nT1 ++\nEND\nMACRO M\nT1 ++\nT1 ++\nEND\nCALL M Y"
		self.assertEqual(valor(prog), 1)

	def test_call_con_argumentos_de_sobra_los_ignora(self):
		prog = "MACRO M\nT1 ++\nEND\nCALL M Y Z1 Z2"
		self.assertEqual(valor(prog), 1)

	def test_programa_vacio(self):
		self.assertEqual(valor(""), 0)

	def test_solo_comentarios(self):
		self.assertEqual(valor("#hola\n#adios"), 0)

	def test_solo_macros_sin_llamadas(self):
		self.assertEqual(valor(programa(MACROS_COPIA)), 0)

	def test_macro_definida_despues_de_su_uso_no_se_expande(self):
		# El expansor solo mira tras el ultimo END, asi que la llamada queda sin expandir
		prog = "CALL M Y\nMACRO M\nT1 ++\nEND"
		self.assertEqual(valor(prog), 0)

	def test_ejecutar_dos_veces_con_las_mismas_listas_da_lo_mismo(self):
		texto = programa(MACROS_COPIA, "CALL COPIA X1 Y")
		variables = core.analyse_variables(texto.split("\n"))
		salidas = []
		for _ in range(2):
			salidas.append(core.run(texto.split("\n"), variables[4], variables[5], {"X1": 3}, False))
		self.assertEqual(salidas[0], salidas[1])


# ---------------------------------------------------------------------------
# G. Oraculos: las macros deben coincidir con la operacion en Python
# ---------------------------------------------------------------------------
class TestOraculos(unittest.TestCase):
	def test_copia(self):
		for x in VALORES:
			with self.subTest(x=x):
				prog = programa(MACROS_COPIA, "CALL COPIA X1 Y")
				self.assertEqual(valor(prog, {"X1": x}), x)

	def test_salto_incondicional(self):
		prog = programa(MACROS_SALTO, "CALL SALTO A1", "Y ++", "A1: Y ++")
		self.assertEqual(valor(prog), 1)

	def test_suma(self):
		for x in VALORES:
			for y in VALORES:
				with self.subTest(x=x, y=y):
					prog = programa(MACROS_SUMA, "CALL SUMA X1 X2 Y")
					self.assertEqual(valor(prog, {"X1": x, "X2": y}), x + y)

	def test_resta_truncada_a_cero(self):
		for x in VALORES:
			for y in VALORES:
				with self.subTest(x=x, y=y):
					prog = programa(MACROS_RESTA, "CALL RESTA X1 X2 Y")
					self.assertEqual(valor(prog, {"X1": x, "X2": y}), max(0, x - y))

	def test_llamada_con_etiqueta_dentro_de_macro_se_expande(self):
		prog = programa(MACROS_COPIA, "MACRO ENVUELVE", "G1: CALL COPIA T1 T2", "END", "CALL ENVUELVE X1 Y")
		self.assertEqual(valor(prog, {"X1": 3}), 3)


# ---------------------------------------------------------------------------
# H. Deteccion de variables
# ---------------------------------------------------------------------------
class TestDeteccionVariables(unittest.TestCase):
	def test_sin_duplicados_y_en_orden_de_aparicion(self):
		self.assertEqual(analizar("X1 ++\nX2 ++\nX1 --")[1], ["X1", "X2"])

	def test_variable_de_entrada_detectada_a_traves_de_un_call(self):
		self.assertEqual(analizar("CALL COPIA X1 Z1")[1], ["X1"])

	def test_sin_variables_de_entrada(self):
		self.assertEqual(analizar("Y ++")[1], [])

	@unittest.expectedFailure
	def test_auxiliar_de_dos_digitos_se_registra_completa(self):
		# Hoy se guarda solo var[1] ('1'), no '10'
		self.assertEqual(analizar("Z10 ++")[4], ["10"])


# ---------------------------------------------------------------------------
# Codificador
# ---------------------------------------------------------------------------
class TestCodificador(unittest.TestCase):
	def test_etiquetas(self):
		esperado = {"A1": 1, "B1": 2, "C1": 3, "D1": 4, "S1": 5, "A2": 6, "A1:": 1}
		for etiqueta, codigo in esperado.items():
			with self.subTest(etiqueta=etiqueta):
				self.assertEqual(encoder.etiq(etiqueta), codigo)

	def test_variables(self):
		esperado = {"Y": 0, "X1": 1, "Z1": 2, "X2": 3, "Z2": 4}
		for variable, codigo in esperado.items():
			with self.subTest(variable=variable):
				self.assertEqual(encoder.var(variable), codigo)

	def test_instrucciones(self):
		self.assertEqual(encoder.instr("=="), 0)
		self.assertEqual(encoder.instr("++"), 1)
		self.assertEqual(encoder.instr("--"), 2)

	@unittest.expectedFailure
	def test_etiquetas_de_dos_digitos(self):
		# int(line[1]) solo lee un digito
		self.assertEqual(encoder.etiq("A10:"), 46)

	@unittest.expectedFailure
	def test_variables_de_dos_digitos(self):
		self.assertEqual(encoder.var("X12"), 23)

	def test_l_y_r_son_inversas_de_num_pair(self):
		for a in range(8):
			for b in range(8):
				with self.subTest(a=a, b=b):
					n = encoder.num_pair(a, b)
					self.assertEqual(encoder.l(n), a)
					self.assertEqual(encoder.r(n), b)

	def test_codificar_instruccion(self):
		self.assertEqual(encoder.codificar_I(0, 1, 0), 2)
		self.assertEqual(encoder.codificar_I(1, 3, 0), 29)

	def test_primos(self):
		self.assertEqual([encoder.enesimo_primo(n) for n in range(1, 6)], [2, 3, 5, 7, 11])

	def test_codificar_programa(self):
		self.assertEqual(encoder.codificar_P([]), 0)
		self.assertEqual(encoder.codificar_P([1, 2]), 17)  # 2^1 * 3^2 - 1

	def test_run_con_codificacion_incluye_la_codificacion(self):
		salida = ejecutar("Y ++", codificar=True)
		self.assertTrue(salida.startswith("Codificación:"))
		self.assertIn("#I = 2", salida)
		self.assertIn("Result: 1", salida)

	def test_run_con_codificacion_de_un_if_con_etiqueta(self):
		salida = ejecutar("A1: IF Y != 0 GOTO A1", codificar=True)
		self.assertIn("#I = 29", salida)


# ---------------------------------------------------------------------------
# Generadores de nombres frescos del expansor
# ---------------------------------------------------------------------------
class TestNombresFrescos(unittest.TestCase):
	def test_primera_etiqueta_libre(self):
		etiquetas = []
		self.assertEqual(expander.next_free_label(etiquetas), "A1")
		self.assertEqual(etiquetas, ["A1"])

	def test_siguiente_etiqueta_libre(self):
		self.assertEqual(expander.next_free_label(["A1"]), "B1")
		self.assertEqual(expander.next_free_label(["A1", "B1", "C1", "D1"]), "A2")

	def test_siguiente_auxiliar_libre(self):
		auxiliares = ["1"]
		self.assertEqual(expander.next_free_aux(auxiliares), "Z2")
		self.assertEqual(auxiliares, ["1", "2"])


if __name__ == '__main__':
	unittest.main()