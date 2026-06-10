"""
Script simple para añadir el campo 'war_type' a los ataques en un archivo JSON.
El campo 'war_type' es importante para el modelo de predicción, ya que las estrategias y resultados pueden variar entre guerras normales y CWL.
Este script tiene dos modos:
1. Añadir 'war_type' con un valor por defecto (normal) a todas las filas que no lo tengan.
2. Intentar detectar si el ataque es de CWL basándose en patrones (como el tamaño del equipo o el nombre del clan) y asignar 'war_type' en consecuencia.
El script también crea un backup del archivo original antes de modificarlo, para evitar pérdida de datos en caso de errores.
"""

import json
import os
from datetime import datetime

def add_war_type_to_jsonl(input_file, output_file=None):
    """
    Añade el campo 'war_type' a las filas que no lo tengan
    Por defecto asume que son guerras normales
    """
    
    if not os.path.exists(input_file):
        print(f"El archivo {input_file} no existe")
        return
    
    # Si no se especifica archivo de salida, usar el mismo archivo
    if output_file is None:
        output_file = input_file
        # Crear backup del archivo original
        backup_file = f"{input_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(input_file, backup_file)
        print(f"Backup creado: {backup_file}")
    
    filas_procesadas = 0
    filas_modificadas = 0
    
    print(f"Procesando archivo: {input_file}")
    
    with open(backup_file if output_file == input_file else input_file, 'r', encoding='utf-8') as f_in:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            for linea_num, linea in enumerate(f_in, 1):
                linea = linea.strip()
                if not linea:
                    continue
                
                try:
                    # Cargar el JSON
                    ataque = json.loads(linea)
                    filas_procesadas += 1
                    
                    # Verificar si ya tiene war_type
                    if 'war_type' not in ataque:
                        # Añadir war_type por defecto como "normal"
                        # En el futuro podrías añadir lógica más sofisticada aquí
                        # para detectar si es CWL basándote en otros campos
                        ataque['war_type'] = "normal"
                        filas_modificadas += 1
                        
                        if filas_modificadas <= 5:  # Mostrar solo los primeros 5
                            print(f"Línea {linea_num}: Añadido war_type='normal'")
                    
                    # Escribir la línea (modificada o no)
                    f_out.write(json.dumps(ataque) + '\n')
                    
                    # Mostrar progreso cada 100 filas
                    if filas_procesadas % 100 == 0:
                        print(f"Procesadas: {filas_procesadas} filas, modificadas: {filas_modificadas}")
                        
                except json.JSONDecodeError as e:
                    print(f"Error en línea {linea_num}: {e}")
                    # Escribir la línea tal como está si hay error
                    f_out.write(linea + '\n')
                except Exception as e:
                    print(f"Error inesperado en línea {linea_num}: {e}")
                    f_out.write(linea + '\n')
    
    print(f"\nPROCESO COMPLETADO")
    print(f"Estadísticas:")
    print(f"   - Filas procesadas: {filas_procesadas}")
    print(f"   - Filas modificadas: {filas_modificadas}")
    print(f"   - Filas sin cambios: {filas_procesadas - filas_modificadas}")
    print(f"Archivo actualizado: {output_file}")
    
    if output_file == input_file:
        print(f"Backup disponible en: {backup_file}")

def add_war_type_smart(input_file, output_file=None):
    """
    Versión inteligente que intenta detectar CWL basándose en patrones
    """
    if not os.path.exists(input_file):
        print(f"El archivo {input_file} no existe")
        return
    
    if output_file is None:
        output_file = input_file
        backup_file = f"{input_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(input_file, backup_file)
        print(f"Backup creado: {backup_file}")
    
    filas_procesadas = 0
    filas_modificadas = 0
    cwl_detectadas = 0
    
    print(f"Procesamiento inteligente de: {input_file}")
    
    with open(backup_file if output_file == input_file else input_file, 'r', encoding='utf-8') as f_in:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            for linea_num, linea in enumerate(f_in, 1):
                linea = linea.strip()
                if not linea:
                    continue
                
                try:
                    ataque = json.loads(linea)
                    filas_procesadas += 1
                    
                    if 'war_type' not in ataque:
                        # Lógica inteligente para detectar CWL
                        war_type = "normal"
                        
                        # Indicadores de CWL (puedes ajustar estos criterios):
                        # 1. Team size típico de CWL (15v15 es común en CWL)
                        # 2. Nombres de clanes que sugieren CWL
                        # 3. Patrones en fechas (CWL ocurre en semanas específicas)
                        
                        team_size = ataque.get('team_size', 0)
                        clan_name = ataque.get('attacker_name', '').lower()
                        
                        # Criterios de detección CWL (puedes mejorar esto):
                        if (team_size == 15 or  # 15v15 es muy común en CWL
                            'cwl' in clan_name or 
                            'league' in clan_name):
                            war_type = "cwl"
                            cwl_detectadas += 1
                        
                        ataque['war_type'] = war_type
                        filas_modificadas += 1
                        
                        if filas_modificadas <= 10:
                            print(f"Línea {linea_num}: war_type='{war_type}' {'(CWL detectada!)' if war_type == 'cwl' else ''}")
                    
                    f_out.write(json.dumps(ataque) + '\n')
                    
                    if filas_procesadas % 100 == 0:
                        print(f"Procesadas: {filas_procesadas}, modificadas: {filas_modificadas}, CWL: {cwl_detectadas}")
                        
                except json.JSONDecodeError as e:
                    print(f"Error en línea {linea_num}: {e}")
                    f_out.write(linea + '\n')
                except Exception as e:
                    print(f"Error inesperado en línea {linea_num}: {e}")
                    f_out.write(linea + '\n')
    
    print(f"\nPROCESO COMPLETADO")
    print(f"Estadísticas:")
    print(f"   - Filas procesadas: {filas_procesadas}")
    print(f"   - Filas modificadas: {filas_modificadas}")
    print(f"   - CWL detectadas: {cwl_detectadas}")
    print(f"   - Guerras normales: {filas_modificadas - cwl_detectadas}")
    print(f"Archivo actualizado: {output_file}")

if __name__ == "__main__":
    # Archivo de entrada
    input_file = "ataques_recientes.jsonl"
    
    print("Script para añadir war_type a ataques")
    print("=" * 50)
    
    # Verificar si el archivo existe
    if not os.path.exists(input_file):
        print(f"No se encontró el archivo {input_file}")
        exit(1)
    
    # Mostrar opciones
    print("Opciones disponibles:")
    print("1. Añadir war_type='normal' a todas las filas sin el campo")
    print("2. Detección inteligente de CWL vs guerras normales")
    print("3. Salir")
    
    try:
        opcion = input("\nElige una opción (1-3): ").strip()
        
        if opcion == "1":
            print("\nEjecutando versión simple...")
            add_war_type_to_jsonl(input_file)
        elif opcion == "2":
            print("\nEjecutando detección inteligente...")
            add_war_type_smart(input_file)
        elif opcion == "3":
            print("Saliendo...")
        else:
            print("Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\nProceso cancelado por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")
