from flask import Flask, render_template, request, redirect, url_for
from database import init_db, load_data, save_data, get_next_id
from datetime import datetime

app = Flask(__name__)
init_db()

@app.route('/')
def index():
    ots = load_data('ordenes')
    equipos = load_data('equipos')
    
    # --- CÁLCULO DE KPIs ---
    total = len(ots)
    completadas = [o for o in ots if o['estado'] == 'Completada']
    
    cumplimiento = (len(completadas) / total * 100) if total > 0 else 0
    
    # MTTR (Mean Time To Repair)
    horas_total = sum([o.get('horas_trabajo', 0) for o in completadas])
    mttr = horas_total / len(completadas) if completadas else 0
    
    # Disponibilidad (Simulada: 100% - % de tiempo en reparación sobre 720h mes)
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
    
    # Cruce dinámico para la tabla
    lista_ots = load_data('ordenes')
    equipos = {e['id']: e['tag'] for e in load_data('equipos')}
    for o in lista_ots:
        o['tag_equipo'] = equipos.get(o['equipo_id'], "N/A")
        
    return render_template('ordenes.html', ots=lista_ots, equipos=load_data('equipos'))

@app.route('/orden/<int:id_ot>')
def detalle_ot(id_ot):
    # 1. Cargar todas las fuentes de datos
    todas_ots = load_data('ordenes')
    todos_equipos = load_data('equipos')
    todo_personal = load_data('personal')
    todos_repuestos = load_data('repuestos')
    todas_actividades = load_data('actividades')

    # 2. Buscar la OT específica
    ot = next((o for o in todas_ots if o['id'] == id_ot), None)
    
    if ot:
        # 3. CRUCES DE DATOS (Relaciones)
        # Buscar el equipo asociado
        equipo = next((e for e in todos_equipos if e['id'] == ot.get('equipo_id')), {"nombre": "No asignado", "tag": "N/A"})
        
        # Buscar el técnico responsable
        tecnico = next((p for p in todo_personal if p['id'] == ot.get('personal_id')), {"nombre": "No asignado", "especialidad": "N/A"})
        
        # Filtrar actividades de esta OT
        actividades_ot = [a for a in todas_actividades if a['ot_id'] == id_ot]
        
        # Filtrar repuestos (En una BETA, simulamos que los repuestos tienen un campo 'ot_id' si fueron usados)
        # O podrías tener una lista de IDs de repuestos dentro de la OT.
        repuestos_usados = [r for r in todos_repuestos if r.get('ot_id') == id_ot]

        return render_template('detalle_ot.html', 
                               ot=ot, 
                               equipo=equipo, 
                               tecnico=tecnico, 
                               actividades=actividades_ot,
                               repuestos=repuestos_usados)
    
    return "Orden no encontrada", 404

# --- GESTIÓN DE PERSONAL ---
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

# --- GESTIÓN DE REPUESTOS ---
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
if __name__ == '__main__':
    app.run(debug=True)