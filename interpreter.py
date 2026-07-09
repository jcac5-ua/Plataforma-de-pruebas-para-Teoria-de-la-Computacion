#!/usr/bin/env	python3 

MAX_INSTR = 10000000
#MAX_INSTR = 70
class Memory(object):
	def __init__(self, nombre = ""):
		self.variables = {}
		self.nombre = nombre

	def get(self, var):
		value = self.variables.get(var, 0)
		return value

	def inc(self, var):
		value = self.variables.get(var, 0)
		self.variables.update({var : value + 1})

	def dec(self, var):
		value = self.variables.get(var, 0)
		if value != 0:
			self.variables[var] = value - 1

	def set(self, var, value):
		self.variables[var] = value

	def get_vars(self):
		return self.variables

	def print_var(self, var):
		print(f"{var} : {self.variables.get(var, 0)}")

	def is_declared(self, var):
		return self.variables.get(var, -1) != -1

	def get_name(self):
		return self.nombre

def check_label(label):

	if label[0] != 'A' and label[0] != 'B' and label[0] != 'C' and label[0] != 'D' and label[0] != 'E' and label[0] != 'S':
		return False
	if label.endswith(':'):
		label = label[1:-1]
	else:
		label = label[1:]
	return label.isnumeric()

def check_macro_label(label):
	if label[0] != 'G':
		return False
	if label.endswith(':'):
		label = label[1:-1]
	else:
		label = label[1:]
	return label.isnumeric()

def check_var(variable):
	if variable == "Y":
		return True
	if variable[0] != 'X' and variable[0] != 'Z':
		return False
	variable = variable[1:]
	return variable.isnumeric()

def check_arg_var(variable):
	return variable[0] == 'X'

def check_aux_var(variable):
	return variable[0] == 'Z'

def check_macro_var(variable):
	if variable[0] != 'T' and variable[0] != 'W':
		return False
	variable = variable[1:]
	return variable.isnumeric()

def check_macroArg_var(variable):
	if variable[0] != 'T':
		return False
	variable = variable[1:]
	return variable.isnumeric()


def printDict(dictionary):
	for d in dictionary:
		print(f"{d}: {dictionary[d]}")

def interpreter(program_lines):
	program = []
	label_tracker = {}
	number_line = 0
	in_macro = False
	nombre_macro = ""
	arg_vars = []
	labels_used = []
	aux_used = []

	for line in program_lines:
		print(str(number_line) + ": '" + line + "'")
		parts = line.split(" ")
		var = parts[0]
		if line.startswith("#") or line == "":
			continue

		##########################################################################################################
		##############################		ETIQUETA								##############################
		##########################################################################################################
		if var.endswith(":"):
			if in_macro and not check_macro_label(var):
					return [-1, number_line + 1, f"\nEtiqueta '{var}' mal definida."]
			elif not in_macro and not check_label(var):
				return [-1, number_line + 1, f"\nEtiqueta '{var}' mal definida en una macro."]
			if not in_macro:
				if label_tracker.get(var[:-1], -1) == -1:
					label_tracker[var[:-1]] = number_line

			if not in_macro:
				labels_used.append(var[:-1])
			if len(parts) == 1:
				continue
			parts = parts[1:]
			var = parts[0]

		##########################################################################################################
		##############################		CONDICIONAL								##############################
		##########################################################################################################
		if var == "IF":
			if len(parts) > 6:
				return [-2, number_line + 1, f"\nSobran parámetros para la instrucción IF: '{line}'."]
			if len(parts) < 6:
				return [-2, number_line + 1, f"\nFaltan parámetros para la instrucción IF: '{line}'."]
			
			if not in_macro:
				if not check_var(parts[1]):
					return [-1, number_line + 1, f"\nVariable '{parts[1]}' mal definida."]
				if not check_label(parts[5]):
					return [-1, number_line + 1, f"\nEtiqueta '{parts[5]} mal definida'"]
				if check_arg_var(parts[1]) and any(x == parts[1] for x in arg_vars) == False:
					arg_vars.append(parts[1])
				elif check_aux_var(parts[1]) and any(x == parts[1] for x in aux_used) == False:
					aux_used.append(parts[1][1])
			else:
				if not check_macro_var(parts[1]):
					return [-1, number_line + 1, f"\nVariable '{parts[1]}' mal definida en una macro."]
				if  not ( check_macro_label(parts[5]) or (check_macro_var(parts[5]) and check_macroArg_var(parts[5])) or parts[5] == "F"):
					return [-1, number_line + 1, f"\nEtiqueta '{parts[5]}' mal definida"]
			
			if parts[2] != "!=" or parts[4] != "GOTO":
				return [-1, number_line + 1, f"\nOperación '{line}' desconocida."]
			


			program.append("JMP " + parts[1] + " " + parts[5])
		elif var == "MACRO":
			if in_macro == True:
				return [-2, number_line + 1, f"\nSe ha intentado definir una macro dentro de otra"]
			if len(parts) > 2:
				return [-2, number_line + 1, f"\nSobran parámetros en la definición de la macro '{parts[1]}'"]
			if len(parts) < 2:
				return [-2, number_line + 1, f"\nFaltan parámetros en la definición de la macro '{parts[1]}'"]
			label_tracker[parts[1]] = number_line
			nombre_macro = parts[1]
			number_line = number_line - 1
			in_macro = True
		elif line == "END":
			if in_macro == False:
				return [-2, number_line + 1, f"\nSe ha cerrado una macro sin haber definido una previamente"]
			nombre_macro = ""
			main_start = number_line
			in_macro = False
		##########################################################################################################
		##############################		CALL MACRO								##############################
		##########################################################################################################
		elif var == "CALL":
			if len(parts) < 3:
				return [-2, number_line + 1, f"\nLa llamada a la macro '{parts[1]}' requiere de al menos un parámetro."]
			s = parts[1] + " "
			for i in parts[2:]:
				if not str(i).isnumeric():
					if check_arg_var(i) and any(x == i for x in arg_vars) == False:
						arg_vars.append(i)
					elif check_aux_var(i) and any(x == i for x in aux_used) == False:
						aux_used.append(i[1:])

				s = s + str(i) + " "
			program.append(s)
		elif line != "":
			if len(parts) != 2:
				return [-1, number_line + 1, f"\nOperación '{line}' desconocida."]
			if in_macro and not check_macro_var(var):
				return [-1, number_line + 1, f"\nVariable '{var}' mal definida en una macro."]
			elif not in_macro and not check_var(var):
				return [-1, number_line + 1, f"\nVariable '{var}' mal definida."]
			
			if check_arg_var(var) and any(x == var for x in arg_vars) == False:
				arg_vars.append(var)
			elif check_aux_var(var) and any(x == var for x in aux_used) == False:
				aux_used.append(var[1])
			
			opcode = parts[1]
			if opcode == "++":
				program.append("INC " + var)
			elif opcode == "--":
				program.append("DEC " + var)
			elif opcode != "==":
				return [-1, number_line + 1, f"\nOperación '{line}' desconocida."]
		number_line += 1
	if in_macro:
		return [-2, number_line + 1, f"\nNo se encuentra operador END que cierra la MACRO"]
	program.append("HALT")
	return [1, arg_vars, program, label_tracker, aux_used, labels_used]

def execute(program, label_tracker, init_vars):
	if program == ['HALT']:
		return [0]
	mem_stack = []
	ret_pc = []
	refs = []
	mem = Memory()
	for var in init_vars:
		mem.set(var, init_vars.get(var))
	i = len(program) - 1
	while i > 0 and program[i] != "RET":
		i = i -1
	pc = i + 1 if i != 0 else 0
	num_pasos = 0

	mem_stack.append(mem)
	while program[pc] != "HALT":
		print(f"{pc}: {program[pc]}: {mem.get_vars()}")
		mem = mem_stack[-1]
		parts = program[pc].split(" ")
		opcode = parts[0]
		if program[pc].startswith("#"):
			continue
		if opcode == "INC":
			var = parts[1]

			mem.inc(var)
		elif opcode == "DEC":
			var = parts[1]
			mem.dec(var)
		elif opcode == "JMP":
			var = parts[1]

			value = mem.get(var)
			if check_macroArg_var(parts[2]):
				tag = mem.get(parts[2])
				print(tag)
			else:
				tag = mem.get_name() + parts[2]
			if value != 0:
				pc = label_tracker.get(tag, len(program) - 1) - 1
				if pc >= len(program) - 1:
					pc = len(program) - 2
		pc += 1
		num_pasos += 1
		if num_pasos > MAX_INSTR:
			return [-4, pc +1, f"\nNúmero máximo de instrucciones ({MAX_INSTR}) alcanzado"]
	mem = mem_stack[-1]
	y = mem.get("Y")
	return [y]