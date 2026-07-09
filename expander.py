#!/usr/bin/env	python3

import interpreter

def expander(code, lVars, lLabels):
	print(f"listas iniciales Vars = {lVars} Etiquetas = {lLabels}")
	i = len(code) - 1
	while i > 0 and code[i] != "END":
		i = i -1

	call_founded = True
	while call_founded:
		call_founded = False 
		pc = i + 1 if i != 0 else 0
		while pc < len(code):
			registro = {}

			if code[pc].startswith("CALL"):
				f_label = next_free_label(lLabels)
				registro["F"] = f_label
				call_founded = True
				code_parts = code[pc].split(" ")
				name_macro = code_parts[1]
				pc_macro = line_macro(code, name_macro)
				if pc_macro == -1:
					return [-3, pc + 1, f"\nMacro {name_macro} no está definida"]
				args = code_parts[2:]
				line = translate_macro_line(code[pc_macro], args, lVars, lLabels, registro)
				if line[0] < 0:
					return [line[0], pc_macro + 1,f"\nEn la macro '{name_macro}' " + line[1]]
				code[pc] = line[1]
				pc = pc + 1
				pc_macro = pc_macro + 1
				while code[pc_macro] != "END":
					line = translate_macro_line(code[pc_macro], args, lVars, lLabels, registro)
					if line[0] < 0:
						return [line[0], pc_macro + 1,f"\nEn la macro '{name_macro}' " + line[1]]
					code.insert(pc, line[1])
					pc = pc + 1
					pc_macro = pc_macro + 1
				code.insert(pc, "#Fin de la macro expandida " + name_macro)
				code.insert(pc, f_label + ":")
	
			pc = pc + 1
	return [1, code]

def line_macro(code, macro):
	i = 0
	found = False
	
	while i < len(code) and found == False:
		line = code[i]
		line_parts = line.split(" ")
		if line_parts[0] == "MACRO":
			if macro == line_parts[1]:
				found = True
		i = i + 1
	if found == False:
		return -1
	return i


def translate_macro_line(line, args, lVars, lLabels, registro):
	if line == "":
		return [1, ""]
	if line[0].startswith("#"):
		return [1, line]
		
	print(registro)
	delimiter = " "
	line = line.split(" ")


	if line[0][0] == "G" and len(line) > 1:
		label_token = line[0][:-1]
		new_label = registro.get(label_token, -1)
		if new_label == -1:
			new_label = next_free_label(lLabels)
			registro[label_token] = new_label
		resto = delimiter.join(line[1:])
		resultado_resto = translate_macro_line(resto, args, lVars, lLabels, registro)
		if resultado_resto[0] < 0:
			return resultado_resto
		return [1, new_label + ":" + delimiter + resultado_resto[1]]

	if line[0][0] == "G":
		new_label = registro.get(line[0][:-1], -1)
		if new_label == -1:
			new_label = next_free_label(lLabels)
			registro[line[0][:-1]] = new_label
		line[0] = new_label + ":"
		if len(line) == 1:
			line = delimiter.join(line)
			return [1, line]

	if line[0][0] == "T":
		index = int(line[0][1:]) - 1
		if index >= len(args):
			return [-3, f"\nArgumento {line[0]} no declarado"]
		line[0] = args[index]
	elif line[0][0] == "W":
		new_aux = registro.get(line[0], -1)
		if new_aux  == -1: 
			new_aux = next_free_aux(lVars)
			registro[line[0]] = new_aux
		line[0] = new_aux

	elif line[0] == "IF":
		if line[1][0] == "T":
			index = int(line[1][1:]) - 1
			if index >= len(args):
				return [-3, f"\nArgumento {line[1]} no declarado"]
			line[1] = args[index]
		else:
			new_aux = registro.get(line[1], -1)
			if new_aux  == -1: 
				new_aux = next_free_aux(lVars)
				registro[line[1]] = new_aux
			line[1] = new_aux

		if line[5][0] == "T":
			index = int(line[5][1:]) - 1
			if index >= len(args):
				return [-3, f"\nArgumento {line[5]} no declarado"]
			line[5] = args[index]
		else:
			new_label = registro.get(line[5], -1)
			if new_label == -1:
				new_label = next_free_label(lLabels)
				registro[line[5]] = new_label
			line[5] = new_label

	elif line[0] == "CALL":
		params = line[2:]
		for i in range(len(params)):
			if params[i][0] == "T":
				index = int(params[i][1:]) - 1
				if index >= len(args):
					return [-3, f"\nArgumento {params[i]} no declarado"]
				line[i + 2] = args[index]
			elif params[i][0] == "W":
				new_aux = registro.get(params[i], -1)
				if new_aux  == -1: 
					new_aux = next_free_aux(lVars)
					registro[params[i]] = new_aux	
				line[i + 2] = new_aux
			elif params[i][0] == "G" or params[i] == "F":
				new_label = registro.get(params[i], -1)
				if new_label == -1:
					new_label = next_free_label(lLabels)
					registro[params[i]] = new_label
				line[i + 2] = new_label


	line = delimiter.join(line)
	return [1, line]

def next_free_aux(var_list):
	i = 1
	while str(i) in var_list:
		i += 1
	var_list.append(str(i))
	return "Z" + str(i)

def next_free_label(label_list):
	i = 0
	found = False
	label = ""
	while not found:
		i += 1
		if "A" + str(i) not in label_list:
			found = True
			label = "A"
		elif "B" + str(i) not in label_list:
			found = True
			label = "B"
		elif "C" + str(i) not in label_list:
			found = True
			label = "C"
		elif "D" + str(i) not in label_list:
			found = True
			label = "D"
	label_list.append(label + str(i))
	return label + str(i)
