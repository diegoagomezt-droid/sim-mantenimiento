from flask import Flask, render_template, request, redirect, url_for
from database import init_db, load_data, save_data, get_next_id
from datetime import datetime

app = Flask(__name__)
init_db()

@app.route('/')
def index():
    ots = load_data('ordenes')
    equipos = load_data('equipos')
    
    total = len(ots)
    completadas = [o for o in ots if o.get('estado') == 'Completada']
    
    cumplimiento = (len(completadas) / total * 100) if total > 0 else 0
    horas_total = sum([o.get('horas_trabajo', 0) for o in completadas])
    mttr = horas_total / len(completadas) if completadas else 0
    disponibilidad = 100 - ((horas_total / (len(equipos) * 720)) * 100) if equipos else 100

    return render_template('index.html', cumplimiento=round(cumplimiento, 2), 
                           mttr=round(mttr, 2), disp=round(disponibilidad, 2))

@app.route('/equipos', methods=['GET', 'POST'])
def equipos():
    if request.method == 'POST':
        data = load_data('equipos')
        data.append({
            "id": get_next_id('equipos'),
            "tag": request.form['tag'],
            "nombre": request.form['nombre']
        })
        save_data('equipos', data)
    return render_template('equipos.html', equipos=load_data('equipos'))

@app.route('/ordenes', methods=['GET', 'POST'])
def ordenes():
    if request.method == 'POST':
        ots = load_data('ordenes')
        ots.append({
            "id": get_next_id('ordenes'),
            "equipo_id": int(request.form['equipo_id']),
            "descripcion": request.form['descripcion'],
            "estado": "Abierta",
            "horas_trabajo": 0,
            "fecha": datetime.now().strftime("%Y-%m-%d")
        })
        save_data('ordenes', ots)
    
    lista_ots = load_data('ordenes')
    equipos_map = {e['id']: e['tag'] for e in load_data('equipos')}
    for o in lista_ots:
        o['tag_equipo'] = equipos_map.get(o['equipo_id'], "N/A")
        
    return render_template('ordenes.html', ots=lista_ots, equipos=load_data('equipos'))

@app.route('/orden/<int:id_ot>')
def detalle_ot(id_ot):
    todas_ots = load_data('ordenes')
    todos_equipos = load_data('equipos')
    todo_personal = load_data('personal') 
    todos_repuestos = load_data('repuestos')
    todas_actividades = load_data('actividades')

    ot = next((o for o in todas_ots if o['id'] == id_ot), None)
    
    if ot:
        equipo = next((e for e in todos_equipos if e['id'] == ot.get('equipo_id')), {"nombre": "N/A", "tag": "N/A"})
        
        # 1. Filtramos actividades de esta OT
        actividades_ot = [a for a in todas_actividades if a['ot_id'] == id_ot]
        
        # 2. Filtramos repuestos que YA SE USARON en esta OT (para la tabla informativa)
        repuestos_usados = [r for r in todos_repuestos if r.get('ot_id') == id_ot and r.get('cantidad_en_ot', 0) > 0]

        return render_template('detalle_ot.html', 
                               ot=ot, 
                               equipo=equipo, 
                               actividades=actividades_ot,
                               repuestos_usados=repuestos_usados, # Para la tabla de historial
                               repuestos=todos_repuestos,       # Para el selector de añadir (lista completa)
                               personal=todo_personal)           # Para el selector de especialistas
    
    return "Orden no encontrada", 404

@app.route('/personal', methods=['GET', 'POST'])
def gestionar_personal():
    if request.method == 'POST':
        data = load_data('personal')
        data.append({
            "id": get_next_id('personal'),
            "nombre": request.form['nombre'],
            "especialidad": request.form['especialidad']
        })
        save_data('personal', data)
    return render_template('personal.html', personal=load_data('personal'))

@app.route('/repuestos', methods=['GET', 'POST'])
def gestionar_repuestos():
    if request.method == 'POST':
        data = load_data('repuestos')
        data.append({
            "id": get_next_id('repuestos'),
            "nombre": request.form['nombre'],
            "stock": int(request.form['stock']),
            "unidad": request.form['unidad']
        })
        save_data('repuestos', data)
    return render_template('repuestos.html', repuestos=load_data('repuestos'))

@app.route('/orden/<int:id_ot>/registrar_intervencion', methods=['POST'])
@app.route('/orden/<int:id_ot>/registrar_intervencion', methods=['POST'])
def registrar_intervencion(id_ot):
    descripcion = request.form.get('descripcion')
    tecnico_id = int(request.form.get('personal_id')) # <--- NUEVO
    repuesto_id_raw = request.form.get('repuesto_id')
    cantidad = int(request.form.get('cantidad', 0))

    # 1. Guardar la Actividad con el Técnico que la realizó
    actividades = load_data('actividades')
    personal = load_data('personal')
    nombre_tecnico = next((p['nombre'] for p in personal if p['id'] == tecnico_id), "Desconocido")

    actividades.append({
        "id": get_next_id('actividades'),
        "ot_id": id_ot,
        "descripcion": descripcion,
        "tecnico": nombre_tecnico, # <--- Ahora la actividad sabe quién la hizo
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_data('actividades', actividades)

    # 2. Procesar repuesto (si aplica)
    if repuesto_id_raw:
        repuesto_id = int(repuesto_id_raw)
        repuestos = load_data('repuestos')
        for r in repuestos:
            if r['id'] == repuesto_id:
                r['stock'] -= cantidad
                r['ot_id'] = id_ot 
                r['cantidad_en_ot'] = r.get('cantidad_en_ot', 0) + cantidad
        save_data('repuestos', repuestos)

    return redirect(url_for('detalle_ot', id_ot=id_ot))
# Eliminar una OT completa
# Eliminar una OT completa
@app.route('/orden/<int:id_ot>/eliminar', methods=['POST'])
def eliminar_orden(id_ot):
    # 1. Cargar datos
    ordenes = load_data('ordenes')
    actividades = load_data('actividades')
    
    # 2. Filtrar para eliminar la OT
    ordenes_actualizadas = [o for o in ordenes if o['id'] != id_ot]
    
    # 3. (Opcional) Eliminar también las actividades que pertenecían a esa OT
    actividades_actualizadas = [a for a in actividades if a['ot_id'] != id_ot]
    
    # 4. Guardar cambios
    save_data('ordenes', ordenes_actualizadas)
    save_data('actividades', actividades_actualizadas)
    
    return redirect('/ordenes')

# Eliminar una intervención específica con devolución de stock
@app.route('/actividad/<int:id_actividad>/eliminar', methods=['POST'])
def eliminar_actividad(id_actividad):
    actividades = load_data('actividades')
    repuestos = load_data('repuestos')
    
    # 1. Identificar la actividad que se va a borrar
    actividad = next((a for a in actividades if a['id'] == id_actividad), None)
    
    if actividad:
        id_ot = actividad['ot_id']
        descripcion_tarea = actividad['descripcion']

        # 2. Lógica de Reversión de Repuestos
        # Buscamos en el inventario qué repuestos están marcados para esta OT
        for r in repuestos:
            if r.get('ot_id') == id_ot:
                # IMPORTANTE: Devolvemos la cantidad al stock general
                cantidad_a_devolver = r.get('cantidad_en_ot', 0)
                r['stock'] += cantidad_a_devolver
                
                # Limpiamos los campos de la OT para que ya no aparezca en la tabla
                r['cantidad_en_ot'] = 0
                r['ot_id'] = None
        
        # 3. Guardar cambios y filtrar la lista de actividades
        save_data('repuestos', repuestos)
        actividades_filtradas = [a for a in actividades if a['id'] != id_actividad]
        save_data('actividades', actividades_filtradas)
        
        return redirect(f'/orden/{id_ot}')
    
    return redirect('/ordenes')
# Eliminar Personal
@app.route('/personal/eliminar/<int:id_p>', methods=['POST'])
def eliminar_personal(id_p):
    data = load_data('personal')
    # Filtramos la lista: dejamos todos menos el que tiene el ID a eliminar
    data_filtrada = [p for p in data if p['id'] != id_p]
    save_data('personal', data_filtrada)
    return redirect('/personal')
# --- ELIMINAR REPUESTOS ---
@app.route('/repuestos/eliminar/<int:id_r>', methods=['POST'])
def eliminar_repuesto(id_r):
    data = load_data('repuestos')
    data_filtrada = [r for r in data if r['id'] != id_r]
    save_data('repuestos', data_filtrada)
    return redirect('/repuestos')
@app.route('/orden/<int:id_ot>/registrar_actividad', methods=['POST'])
def registrar_actividad(id_ot):
    # Cargar datos
    actividades = load_data('actividades')
    repuestos = load_data('repuestos')
    
    # Datos de la intervención
    tecnico = request.form['tecnico']
    descripcion = request.form['descripcion']
    
    # Listas de repuestos enviados desde el JS
    ids_repuestos = request.form.getlist('repuestos_ids[]')
    cants_repuestos = request.form.getlist('repuestos_cants[]')

    # 1. Guardar la actividad en la bitácora
    nueva_actividad = {
        "id": get_next_id('actividades'),
        "ot_id": id_ot,
        "tecnico": tecnico,
        "descripcion": descripcion,
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    actividades.append(nueva_actividad)
    save_data('actividades', actividades)

    # 2. Actualizar Stock para cada repuesto seleccionado
    for i in range(len(ids_repuestos)):
        r_id = int(ids_repuestos[i])
        r_cant = int(cants_repuestos[i])
        
        for r in repuestos:
            if r['id'] == r_id:
                r['stock'] -= r_cant # Descontar stock
                # Vincular a la OT para que aparezca en la tabla de utilizados
                r['ot_id'] = id_ot
                r['cantidad_en_ot'] = r.get('cantidad_en_ot', 0) + r_cant
                break
    
    save_data('repuestos', repuestos)
    return redirect(f'/orden/{id_ot}')
# --- ELIMINAR EQUIPOS ---
@app.route('/equipos/eliminar/<int:id_e>', methods=['POST'])
def eliminar_equipo(id_e):
    data = load_data('equipos')
    data_filtrada = [e for e in data if e['id'] != id_e]
    save_data('equipos', data_filtrada)
    return redirect('/equipos')
@app.route('/repuestos/sumar/<int:id_r>', methods=['POST'])
def sumar_stock(id_r):
    data = load_data('repuestos')
    # Obtenemos la cantidad desde el nuevo input que agregaremos
    cantidad_a_sumar = int(request.form.get('cantidad_nueva', 0))
    
    for r in data:
        if r['id'] == id_r:
            r['stock'] += cantidad_a_sumar
            break
            
    save_data('repuestos', data)
    return redirect('/repuestos')
@app.route('/ordenes', methods=['GET', 'POST'])
def gestionar_ordenes():
    if request.method == 'POST':
        data = load_data('ordenes')
        # Capturamos la descripción del textarea
        nueva_ot = {
            "id": get_next_id('ordenes'),
            "equipo_id": int(request.form['equipo_id']),
            "descripcion": request.form['descripcion'], # Aquí se guarda el box grande
            "fecha": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "estado": "Abierta",
            "horas_trabajo": 0
        }
        data.append(nueva_ot)
        save_data('ordenes', data)
        return redirect('/ordenes')

# ESTO SIEMPRE AL FINAL DEL ARCHIVO
if __name__ == '__main__':
    app.run(debug=True)