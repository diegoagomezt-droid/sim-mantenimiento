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
@app.route('/orden/<int:id_ot>')
def detalle_ot(id_ot):
    todas_ots = load_data('ordenes')
    todos_equipos = load_data('equipos')
    todo_personal = load_data('personal') # Necesario para el selector
    todos_repuestos = load_data('repuestos')
    todas_actividades = load_data('actividades')

    ot = next((o for o in todas_ots if o['id'] == id_ot), None)
    
    if ot:
        equipo = next((e for e in todos_equipos if e['id'] == ot.get('equipo_id')), {"nombre": "N/A", "tag": "N/A"})
        
        # Filtramos actividades y repuestos vinculados a esta OT
        actividades_ot = [a for a in todas_actividades if a['ot_id'] == id_ot]
        repuestos_usados = [r for r in todos_repuestos if r.get('ot_id') == id_ot]

        return render_template('detalle_ot.html', 
                               ot=ot, 
                               equipo=equipo, 
                               actividades=actividades_ot,
                               repuestos=repuestos_usados,
                               todos_los_repuestos_disponibles=todos_repuestos,
                               personal_disponible=todo_personal) # Enviamos el personal aquí

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
def eliminar_ot(id_ot):
    ordenes = load_data('ordenes')
    # Filtramos para quitar la OT seleccionada
    ordenes_filtradas = [o for o in ordenes if o['id'] != id_ot]
    save_data('ordenes', ordenes_filtradas)
    
    # También limpiamos las actividades asociadas a esa OT
    actividades = load_data('actividades')
    actividades_filtradas = [a for a in actividades if a['ot_id'] != id_ot]
    save_data('actividades', actividades_filtradas)
    
    # Redirección directa a la lista de órdenes para evitar BuildError
    return redirect('/ordenes')

# Eliminar una intervención específica con devolución de stock
@app.route('/actividad/<int:id_actividad>/eliminar', methods=['POST'])
def eliminar_actividad(id_actividad):
    actividades = load_data('actividades')
    repuestos = load_data('repuestos')
    
    actividad = next((a for a in actividades if a['id'] == id_actividad), None)
    
    if actividad:
        id_ot = actividad['ot_id']
        
        # Opcional: Devolver stock si la actividad tenía repuestos asociados
        # (Esto funciona si guardaste el repuesto_id en el registro de la actividad)
        
        actividades_filtradas = [a for a in actividades if a['id'] != id_actividad]
        save_data('actividades', actividades_filtradas)
        
        return redirect(f'/orden/{id_ot}')
    
    return redirect('/ordenes')

# ESTO SIEMPRE AL FINAL DEL ARCHIVO
if __name__ == '__main__':
    app.run(debug=True)