import interpreter
import encoder
import expander

USAGE = "\n\nInstrucciones validas:\n\n* VARIABLE OPERACION\n\n* ETIQUETA:\n\n* IF VARIABLE != 0 GOTO ETIQUETA\n\n* CALL NOMBRE_MACRO\n\n* MACRO NOMBRE_MACRO ... END\n\nVARIABLE = Y, X1, Z1, X2, Z2, ...\nVARIABLE MACRO = T1, W1, T2, W2, ...\nOPERACION = ++, --, ==\nETIQUETA = A1, B1, C1, D1, S1, A2, ...\nETIQUETA MACRO = G1, G2, G3, ..."


def error_msg(tipo, línea, error):
    tipo_error = ""
    match tipo:
        case -1:
            tipo_error = "léxico"
        case -2:
            tipo_error = "sintáctico"
        case -3:
            tipo_error = "semántico"
        case -4:
            return f"Error de ejecución: {error}"

    return f"Error {tipo_error} en la línea {línea}: {error}"

def compose_code(code):
    s = ""
    for line in code:
        s = s + line + "\n"
    return s

def analyse_variables(text):
    return interpreter.interpreter(text)

def run(text, lVars, lLabels, init_vars, codification):
    check_str = ""
	
    code_expanded = expander.expander(text, lVars, lLabels)
    if code_expanded[0] < 0:
        return error_msg(code_expanded[0], code_expanded[1], code_expanded[2])
    
    #print(code_expanded[1])

    result = interpreter.interpreter(code_expanded[1])
    if result[0] < 0:
        return "Después de la expansión: \n\n" + error_msg(result[0], result[1], result[2]) + "\nDe la expansión:\n\n" + compose_code(code_expanded[1])
    
    result = interpreter.execute(result[2], result[3], init_vars)
    if result[0] < 0:
        return f"Para los valores de entrada {init_vars}\n" + error_msg(result[0], result[1], result[2])
    
    if codification:
        check_str = "Codificación:\n" + encoder.encoder(code_expanded[1]) + "\n"
    
    return check_str + f"Para los valores de entrada {init_vars}\nResult: " + str(result[0])