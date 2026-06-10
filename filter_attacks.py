"""
Filtrado de ataques
"""

import json
import os
from datetime import datetime

def filter_attacks_with_power(input_file, output_file=None, required_fields=None):
    """
    Filtra las líneas del archivo JSONL que no tengan los campos requeridos
    """
    if required_fields is None:
        required_fields = ['attacker_offensive_power']
    
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"ataques_filtrados_{timestamp}.jsonl"
    
    if not os.path.exists(input_file):
        print(f"❌ El archivo {input_file} no existe")
        return
    
    print(f"Filtrando archivo: {input_file}")
    print(f"Campos requeridos: {', '.join(required_fields)}")
    print(f"Archivo salida: {output_file}")
    print("=" * 60)
    
    total_lines = 0
    valid_lines = 0
    invalid_lines = 0
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            
            for line_num, line in enumerate(f_in, 1):
                line = line.strip()
                if not line:
                    continue
                
                total_lines += 1
                
                try:
                    attack = json.loads(line)
                    
                    # Verificar si tiene todos los campos requeridos
                    has_all_fields = all(field in attack for field in required_fields)
                    
                    if has_all_fields:
                        # La línea tiene todos los campos, mantenerla
                        f_out.write(line + '\n')
                        valid_lines += 1
                    else:
                        # La línea no tiene todos los campos, descartarla
                        invalid_lines += 1
                        missing_fields = [field for field in required_fields if field not in attack]
                        if invalid_lines <= 5:  # Mostrar solo las primeras 5 para no saturar
                            print(f"Línea {line_num}: Faltan campos {missing_fields}")
                
                except json.JSONDecodeError as e:
                    invalid_lines += 1
                    print(f"Error JSON en línea {line_num}: {e}")
                    continue
                except Exception as e:
                    invalid_lines += 1
                    print(f"Error procesando línea {line_num}: {e}")
                    continue
                
                # Mostrar progreso cada 100 líneas
                if total_lines % 100 == 0:
                    print(f"Procesadas {total_lines} líneas... (Válidas: {valid_lines}, Inválidas: {invalid_lines})")
    
    # Resumen final
    print(f"\nFILTRADO COMPLETADO")
    print("=" * 60)
    print(f"Estadísticas:")
    print(f"   - Total líneas procesadas: {total_lines}")
    print(f"   - Líneas válidas (conservadas): {valid_lines} ({valid_lines/total_lines*100:.1f}%)")
    print(f"   - Líneas inválidas (eliminadas): {invalid_lines} ({invalid_lines/total_lines*100:.1f}%)")
    print(f"Archivo filtrado guardado en: {output_file}")
    
    return valid_lines, invalid_lines

def main():
    print("SCRIPT DE FILTRADO DE ATAQUES")
    print("=" * 50)
    
    # Configuración
    input_file = "ataques_enriquecidos_20250808_190323.jsonl"
    
    # Opciones del usuario
    print("Opciones de filtrado:")
    print("1. Solo ataques con poder ofensivo (attacker_offensive_power)")
    print("2. Solo ataques con poder defensivo (defender_defensive_power)")
    print("3. Solo ataques con ambos poderes")
    print("4. Filtrado personalizado")
    print("5. Salir")
    
    opcion = input("\nElige una opción (1-5): ").strip()
    
    try:
        if opcion == "1":
            print("\nFiltrando ataques con poder ofensivo...")
            filter_attacks_with_power(input_file, required_fields=['attacker_offensive_power'])
            
        elif opcion == "2":
            print("\nFiltrando ataques con poder defensivo...")
            filter_attacks_with_power(input_file, required_fields=['defender_defensive_power'])
            
        elif opcion == "3":
            print("\nFiltrando ataques con ambos poderes...")
            filter_attacks_with_power(input_file, required_fields=['attacker_offensive_power', 'defender_defensive_power'])
            
        elif opcion == "4":
            print("\nFiltrado personalizado")
            campos = input("Introduce los campos requeridos separados por comas: ").strip()
            if campos:
                required_fields = [campo.strip() for campo in campos.split(',')]
                filter_attacks_with_power(input_file, required_fields=required_fields)
            else:
                print("No se especificaron campos")
                
        elif opcion == "5":
            print("Saliendo...")
            
        else:
            print("Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\nProceso cancelado por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")

if __name__ == "__main__":
    main()
