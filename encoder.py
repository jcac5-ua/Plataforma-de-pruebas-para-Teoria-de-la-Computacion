import sys
import math

def etiq(line):
	if line[0] == 'A':
		return 1 + 5 * (int(line[1]) - 1)
	elif line[0] == 'B':
		return 2 + 5 * (int(line[1]) - 1)
	elif line[0] == 'C':
		return 3 + 5 * (int(line[1]) - 1)
	elif line[0] == 'D':
		return 4 + 5 * (int(line[1]) - 1)
	elif line[0] == 'S':
		return 5 + 5 * (int(line[1]) - 1)
	else:
		return 0

def instr(line):
	if line == "==":
		return 0
	elif line == "++":
		return 1
	elif line == "--":
		return 2
	else:
		return 0

def var(line):
	if line[0] == 'Y':
		return 0
	elif line[0] == 'X':
		return 1 + 2 * (int(line[1]) - 1)
	elif line[0] == 'Z':
		return 2 + 2 * (int(line[1]) - 1)
	else:
		return 0

def l(x):
	x = x + 1
	a = 0
	while x % 2 == 0:
		x = x // 2
		a += 1
	return a

def r(x):
	return ((x + 1) // (2 ** l(x)) - 1) // 2

def num_pair(a, b):
	return ((2 ** a) * (2*b + 1)) - 1

def codificar_P(codigos_instrucciones):
    resultado = 1
    for i, ci in enumerate(codigos_instrucciones):
        resultado *= enesimo_primo(i + 1) ** ci
    return resultado - 1

def codificar_I(a, b, c):
	return num_pair(a, num_pair(b, c))

def es_primo(n):
    """Verifica si un número es primo."""
    if n < 2:
        return False
    # Comprobamos divisores hasta la raíz cuadrada de n
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def enesimo_primo(n):
    """Encuentra el enésimo número primo."""
    contador = 0
    numero_actual = 1
    
    while contador < n:
        numero_actual += 1
        if es_primo(numero_actual):
            contador += 1
            
    return numero_actual

def encoder(code):
	program = []
	label = 0
	number_line = 1

	I = []

	i = len(code) - 1
	while i > 0 and code[i] != "END":
		i = i -1
	pc = i + 1 if i != 0 else 0

	for line in code[pc:]:
		print(line)
		if line == "" or line.startswith("#"):
			continue
		parts = line.split(" ")
		variable = parts[0]

		#Es una labelueta
		if variable.endswith(":"):
			label = etiq(variable)
			if len(parts) == 1:
				continue
			parts = parts[1:]
			variable = parts[0]

		if variable == "IF":
			instruction = 2 + etiq(parts[5])
			variable = var(parts[1])
		else:
			instruction = instr(parts[1])
			variable = var(variable)

		cod_i = codificar_I(label, instruction, variable)

		I.append(cod_i)
		program.append(f"{number_line} : {line} => [{label}, [{instruction}, {variable}]] #I = {cod_i}")
		label = 0
		number_line += 1

	cod_p = codificar_P(I)
	codification = ""
	for p in program:
		codification = codification + p + "\n"
	#codification = codification + f"Codificación de #P = {str(cod_p)}" + "\n"
	return codification
	
