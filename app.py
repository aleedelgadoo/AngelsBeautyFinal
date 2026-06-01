import os
import uuid
import mimetypes
from flask import Flask, config, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import httpx
from flask_wtf.csrf import CSRFProtect
 
load_dotenv()
 
SUPABASE_URL    = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY    = os.environ.get('SUPABASE_SERVICE_KEY', '')
SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'fotos')
 
def _supabase_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    }
 
def subir_imagen_supabase(file_storage) -> str | None:
    if not (SUPABASE_URL and SUPABASE_KEY):
        print("[Supabase] ERROR: Faltan variables SUPABASE_URL o SUPABASE_SERVICE_KEY")
        return None
 
    original = secure_filename(file_storage.filename)
    ext      = original.rsplit('.', 1)[-1].lower() if '.' in original else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    data     = file_storage.read()
    mime     = mimetypes.guess_type(original)[0] or 'application/octet-stream'
 
    url     = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    headers = {**_supabase_headers(), 'Content-Type': mime}
 
    resp = httpx.put(url, content=data, headers=headers)
    if resp.status_code not in (200, 201):
        print(f"[Supabase] ERROR al subir {filename}: {resp.status_code} {resp.text}")
        return None
 
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
    return public_url
 
def eliminar_imagen_supabase(url: str):
    if not url or not (SUPABASE_URL and SUPABASE_KEY):
        return
    prefix = f"/storage/v1/object/public/{SUPABASE_BUCKET}/"
    if prefix not in url:
        return
    filename = url.split(prefix)[-1]
    del_url  = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    httpx.delete(del_url, headers=_supabase_headers())
 
def procesar_imagen(file_storage) -> str | None:
    if not file_storage or not allowed_file(file_storage.filename):
        return None
    return subir_imagen_supabase(file_storage)
 
# ── Flask app ─────────────────────────────────────────────────────────────────
 
app = Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_ENV') == 'development'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '')
csrf = CSRFProtect(app) # Esto protege automáticamente todos los POST
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp', 'jfif'}
app.config['MAX_CONTENT_LENGTH'] = 35 * 1024 * 1024
 
uri = os.environ.get('DATABASE_URL')
if uri:
    print("DEBUG: ¡ÉXITO! Encontré la URL en el .env")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
else:
    print("DEBUG: ¡ERROR! No encontré ninguna URL. Usando SQLite.")
    uri = 'sqlite:///maquillaje.db'
 
app.config['SQLALCHEMY_DATABASE_URI']        = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
 
db            = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
 
# ==========================================
# MODELOS
# ==========================================
 
class Admin(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
 
class ConfiguracionGlobal(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    titulo_sitio     = db.Column(db.String(100), nullable=False, default="TIARA BEAUTY")
    logo             = db.Column(db.String(500), nullable=True, default="")
    imagen_sobre_mi  = db.Column(db.String(500), nullable=False, default="")
    link_turno       = db.Column(db.String(500), nullable=True, default="#")
 
    imagen_hero        = db.Column(db.String(500), nullable=True, default="")
    posicion_foco_hero = db.Column(db.String(20), nullable=False, default="50%")
    opacidad_overlay   = db.Column(db.Float, nullable=False, default=0.3)
    altura_banner      = db.Column(db.Integer, nullable=False, default=60)
 
    sec_home        = db.Column(db.String(50), default="HOME")
    sec_about       = db.Column(db.String(50), default="ABOUT")
    sec_servicios   = db.Column(db.String(50), default="SERVICES")
    sec_cursos      = db.Column(db.String(50), default="COURSES")
    sec_testimonios = db.Column(db.String(50), default="TESTIMONIALS")
    sec_faq         = db.Column(db.String(50), default="FAQ")
 
    link_whatsapp  = db.Column(db.String(500), nullable=True, default="")
    link_instagram = db.Column(db.String(500), nullable=True, default="")
    link_tiktok    = db.Column(db.String(500), nullable=True, default="")
    hero_titulo    = db.Column(db.String(200), nullable=True, default="UNLEASH YOUR BEAUTY WITH CONFIDENCE")
    hero_subtitulo = db.Column(db.String(200), nullable=True, default="Professional Makeup Services Tailored Just For You")
    hero_boton     = db.Column(db.String(100), nullable=True, default="Book Your Appointment")
 
class Faq(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    pregunta  = db.Column(db.String(255), nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
 
class Experiencia(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False)
    foto_perfil = db.Column(db.String(500), nullable=False)
    testimonio  = db.Column(db.Text, nullable=False)
 
class Servicio(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    tipo             = db.Column(db.String(100), nullable=False)
    duracion         = db.Column(db.String(50), nullable=False)
    incluye          = db.Column(db.Text, nullable=False)
    imagen_principal = db.Column(db.String(500), nullable=False)
    posicion_foco    = db.Column(db.String(20), nullable=False, default="50%")
    fotos    = db.relationship('FotoServicio', backref='servicio', cascade="all, delete-orphan", lazy=True)
    paquetes = db.relationship('Paquete',      backref='servicio', cascade="all, delete-orphan", lazy=True)
 
class FotoServicio(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    ruta        = db.Column(db.String(500), nullable=False)
    posicion_foco = db.Column(db.String(20), nullable=False, default="50%")
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicio.id'), nullable=False)
 
class Paquete(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicio.id'), nullable=False)
 
class Curso(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    nombre           = db.Column(db.String(100), nullable=False)
    duracion         = db.Column(db.String(50), nullable=False)
    descripcion      = db.Column(db.Text, nullable=False)
    imagen_principal = db.Column(db.String(500), nullable=False)
    posicion_foco    = db.Column(db.String(20), nullable=False, default="50%")
    fotos = db.relationship('FotoCurso', backref='curso', cascade="all, delete-orphan", lazy=True)
 
class FotoCurso(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    ruta     = db.Column(db.String(500), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)
 
class FotoGeneral(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    posicion_foco = db.Column(db.String(20), nullable=False, default="50% 50%")
    ruta = db.Column(db.String(500), nullable=False)
 
# ==========================================
# LOGIN / CONTEXT PROCESSOR
# ==========================================
 
@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))
 
@app.context_processor
def inject_global_config():
    config = ConfiguracionGlobal.query.first()
    if not config:
        config = ConfiguracionGlobal(
            titulo_sitio="TIARA BEAUTY", link_turno="#", imagen_sobre_mi="",
            logo="", imagen_hero="", posicion_foco_hero="50%",
            opacidad_overlay=0.3, altura_banner=60,
            sec_home="HOME", sec_about="ABOUT", sec_servicios="SERVICES",
            sec_cursos="COURSES", sec_testimonios="TESTIMONIALS", sec_faq="FAQ",
            link_whatsapp="", link_instagram="", link_tiktok=""
        )
        db.session.add(config)
        db.session.commit()
    return dict(global_config=config)
 
# ==========================================
# RUTAS PÚBLICAS
# ==========================================
 
@app.route('/')
def inicio():
    servicios       = Servicio.query.all()
    cursos          = Curso.query.all()
    faqs            = Faq.query.all()
    experiencias    = Experiencia.query.all()
    galeria_general = FotoGeneral.query.all()
    return render_template('inicio.html', servicios=servicios, cursos=cursos,
                           faqs=faqs, experiencias=experiencias,
                           galeria_general=galeria_general)
 
@app.route('/servicios/<int:id>')
def servicio_detalle(id):
    return render_template('servicio_detalle.html', servicio=Servicio.query.get_or_404(id))
 
@app.route('/cursos/<int:id>')
def curso_detalle(id):
    return render_template('curso_detalle.html', curso=Curso.query.get_or_404(id))
 
# ==========================================
# AUTENTICACIÓN
# ==========================================
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('Credenciales incorrectas.', 'danger')
    return render_template('login.html')
 
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('inicio'))
 
# ==========================================
# PANEL DE ADMINISTRACIÓN
# ==========================================
 
@app.route('/admin')
@login_required
def admin_dashboard():
    servicios       = Servicio.query.all()
    cursos          = Curso.query.all()
    faqs            = Faq.query.all()
    experiencias    = Experiencia.query.all()
    galeria_general = FotoGeneral.query.all()
    return render_template('admin.html', servicios=servicios, cursos=cursos,
                           faqs=faqs, experiencias=experiencias,
                           galeria_general=galeria_general)
 
# ── Configuración global ───────────────────────────────────────────────────────
 
@app.route('/admin/configuracion-global', methods=['POST'])
@login_required
def actualizar_configuracion_global():
    config = ConfiguracionGlobal.query.first()
    if not config:
        config = ConfiguracionGlobal()
        db.session.add(config)
 
    config.titulo_sitio    = request.form.get('titulo_sitio', 'TIARA BEAUTY').upper()
    config.link_turno      = request.form.get('link_turno', '#')
    config.sec_home        = request.form.get('sec_home',        'HOME').upper()
    config.sec_about       = request.form.get('sec_about',       'ABOUT').upper()
    config.sec_servicios   = request.form.get('sec_servicios',   'SERVICES').upper()
    config.sec_cursos      = request.form.get('sec_cursos',      'COURSES').upper()
    config.sec_testimonios = request.form.get('sec_testimonios', 'TESTIMONIALS').upper()
    config.sec_faq         = request.form.get('sec_faq',         'FAQ').upper()
    config.link_whatsapp   = request.form.get('link_whatsapp',  '')
    config.link_instagram  = request.form.get('link_instagram', '')
    config.link_tiktok     = request.form.get('link_tiktok',    '')
    config.hero_titulo   = request.form.get('hero_titulo', 'UNLEASH YOUR BEAUTY WITH CONFIDENCE')
    config.hero_subtitulo = request.form.get('hero_subtitulo', 'Professional Makeup Services Tailored Just For You')
    config.hero_boton    = request.form.get('hero_boton', 'Book Your Appointment')
 
    if request.form.get('posicion_foco_hero'):
        config.posicion_foco_hero = request.form.get('posicion_foco_hero') + '%'
    if request.form.get('opacidad_overlay'):
        config.opacidad_overlay = float(request.form.get('opacidad_overlay')) / 100.0
    if request.form.get('altura_banner'):
        config.altura_banner = int(request.form.get('altura_banner'))
 
    url = procesar_imagen(request.files.get('foto_sobre_mi'))
    if url:
        eliminar_imagen_supabase(config.imagen_sobre_mi)
        config.imagen_sobre_mi = url
 
    url = procesar_imagen(request.files.get('logo_sitio'))
    if url:
        eliminar_imagen_supabase(config.logo)
        config.logo = url
 
    url = procesar_imagen(request.files.get('imagen_hero'))
    if url:
        eliminar_imagen_supabase(config.imagen_hero)
        config.imagen_hero = url
 
    db.session.commit()
    flash('Configuración global actualizada con éxito.', 'success')
    return redirect(url_for('admin_dashboard'))
 
# ── Servicios ─────────────────────────────────────────────────────────────────
 
@app.route('/admin/servicio/nuevo', methods=['POST'])
@login_required
def nuevo_servicio():
    tipo     = request.form.get('tipo')
    duracion = request.form.get('duracion')
    incluye  = request.form.get('incluye')
    posicion = request.form.get('posicion_foco', '50') + '%'
    url      = procesar_imagen(request.files.get('imagen_principal'))
    if url:
        db.session.add(Servicio(tipo=tipo, duracion=duracion, incluye=incluye,
                                imagen_principal=url, posicion_foco=posicion))
        db.session.commit()
        flash('Servicio creado con éxito.', 'success')
    else:
        flash('Debés subir una imagen principal.', 'danger')
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/servicio/editar/<int:id>', methods=['POST'])
@login_required
def editar_servicio(id):
    servicio          = Servicio.query.get_or_404(id)
    servicio.tipo     = request.form.get('tipo')
    servicio.duracion = request.form.get('duracion')
    servicio.incluye  = request.form.get('incluye')
    if request.form.get('posicion_foco'):
        servicio.posicion_foco = request.form.get('posicion_foco') + '%'
    url = procesar_imagen(request.files.get('imagen_principal'))
    if url:
        eliminar_imagen_supabase(servicio.imagen_principal)
        servicio.imagen_principal = url
    db.session.commit()
    flash('Servicio editado con éxito.', 'success')
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/servicio/eliminar/<int:id>')
@login_required
def eliminar_servicio(id):
    serv = Servicio.query.get_or_404(id)
    eliminar_imagen_supabase(serv.imagen_principal)
    for foto in serv.fotos:
        eliminar_imagen_supabase(foto.ruta)
    db.session.delete(serv)
    db.session.commit()
    flash('Servicio eliminado.', 'warning')
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/servicio/galeria/subir/<int:id>', methods=['POST'])
@login_required
def subir_foto_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    for file in request.files.getlist('fotos_galeria'):
        url = procesar_imagen(file)
        if url:
            db.session.add(FotoServicio(ruta=url, servicio_id=servicio.id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/servicio/galeria/eliminar/<int:foto_id>')
@login_required
def eliminar_foto_servicio(foto_id):
    foto = FotoServicio.query.get_or_404(foto_id)
    eliminar_imagen_supabase(foto.ruta)
    db.session.delete(foto)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/servicio/galeria/foco/<int:foto_id>', methods=['POST'])
@login_required
def ajustar_foco_foto_servicio(foto_id):
    foto = FotoServicio.query.get_or_404(foto_id)
    valor = request.form.get('posicion_foco', '50')
    foto.posicion_foco = valor + '%'
    db.session.commit()
    return ('', 204)

@app.route('/admin/migrar-foco-fotos')
@login_required
def migrar_foco_fotos():
    with db.engine.connect() as conn:
        conn.execute(db.text("ALTER TABLE foto_servicio ADD COLUMN IF NOT EXISTS posicion_foco VARCHAR(20) DEFAULT '50%'"))
        conn.commit()
    return 'Migración OK'
 
# ── Paquetes ──────────────────────────────────────────────────────────────────
 
@app.route('/admin/paquete/nuevo', methods=['POST'])
@login_required
def nuevo_paquete():
    servicio_id = request.form.get('servicio_id')
    nombre      = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    if nombre and descripcion and servicio_id:
        db.session.add(Paquete(nombre=nombre, descripcion=descripcion, servicio_id=servicio_id))
        db.session.commit()
        flash('Paquete añadido.', 'success')
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/paquete/eliminar/<int:id>')
@login_required
def eliminar_paquete(id):
    paq = Paquete.query.get_or_404(id)
    db.session.delete(paq)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
# ── Experiencias ──────────────────────────────────────────────────────────────
 
@app.route('/admin/experiencia/nueva', methods=['POST'])
@login_required
def nueva_experiencia():
    nombre     = request.form.get('nombre')
    testimonio = request.form.get('testimonio')
    url        = procesar_imagen(request.files.get('foto_perfil'))
    if url:
        db.session.add(Experiencia(nombre=nombre, testimonio=testimonio, foto_perfil=url))
        db.session.commit()
        flash('Testimonio guardado.', 'success')
    else:
        flash('Debés subir una foto de perfil.', 'danger')
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/experiencia/eliminar/<int:id>')
@login_required
def eliminar_experiencia(id):
    exp = Experiencia.query.get_or_404(id)
    eliminar_imagen_supabase(exp.foto_perfil)
    db.session.delete(exp)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
# ── FAQs ──────────────────────────────────────────────────────────────────────
 
@app.route('/admin/faq/nueva', methods=['POST'])
@login_required
def nueva_faq():
    pregunta  = request.form.get('pregunta')
    respuesta = request.form.get('respuesta')
    if pregunta and respuesta:
        db.session.add(Faq(pregunta=pregunta, respuesta=respuesta))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/faq/eliminar/<int:id>')
@login_required
def eliminar_faq(id):
    faq = Faq.query.get_or_404(id)
    db.session.delete(faq)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
# ── Cursos ────────────────────────────────────────────────────────────────────
 
@app.route('/admin/curso/nuevo', methods=['POST'])
@login_required
def nuevo_curso():
    nombre      = request.form.get('nombre')
    duracion    = request.form.get('duracion')
    descripcion = request.form.get('descripcion')
    posicion    = request.form.get('posicion_foco', '50') + '%'
    url         = procesar_imagen(request.files.get('imagen_principal'))
    if url:
        db.session.add(Curso(nombre=nombre, duracion=duracion, descripcion=descripcion,
                             imagen_principal=url, posicion_foco=posicion))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/curso/editar/<int:id>', methods=['POST'])
@login_required
def editar_curso(id):
    curso             = Curso.query.get_or_404(id)
    curso.nombre      = request.form.get('nombre')
    curso.duracion    = request.form.get('duracion')
    curso.descripcion = request.form.get('descripcion')
    if request.form.get('posicion_foco'):
        curso.posicion_foco = request.form.get('posicion_foco') + '%'
    url = procesar_imagen(request.files.get('imagen_principal'))
    if url:
        eliminar_imagen_supabase(curso.imagen_principal)
        curso.imagen_principal = url
    db.session.commit()
    flash('Curso editado con éxito.', 'success')
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/curso/eliminar/<int:id>')
@login_required
def eliminar_curso(id):
    cur = Curso.query.get_or_404(id)
    eliminar_imagen_supabase(cur.imagen_principal)
    for foto in cur.fotos:
        eliminar_imagen_supabase(foto.ruta)
    db.session.delete(cur)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/curso/galeria/subir/<int:id>', methods=['POST'])
@login_required
def subir_foto_curso(id):
    curso = Curso.query.get_or_404(id)
    for file in request.files.getlist('fotos_galeria'):
        url = procesar_imagen(file)
        if url:
            db.session.add(FotoCurso(ruta=url, curso_id=curso.id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/curso/galeria/eliminar/<int:foto_id>')
@login_required
def eliminar_foto_curso(foto_id):
    foto = FotoCurso.query.get_or_404(foto_id)
    eliminar_imagen_supabase(foto.ruta)
    db.session.delete(foto)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
# ── Galería general ───────────────────────────────────────────────────────────
 
@app.route('/admin/galeria-general/subir', methods=['POST'])
@login_required
def subir_galeria_general():
    for file in request.files.getlist('fotos_generales'):
        url = procesar_imagen(file)
        if url:
            db.session.add(FotoGeneral(ruta=url))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))
 
@app.route('/admin/galeria-general/eliminar/<int:id>')
@login_required
def eliminar_foto_general(id):
    foto = FotoGeneral.query.get_or_404(id)
    eliminar_imagen_supabase(foto.ruta)
    db.session.delete(foto)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/galeria-general/foco/<int:foto_id>', methods=['POST'])
@login_required
def ajustar_foco_foto_general(foto_id):
    foto = FotoGeneral.query.get_or_404(foto_id)
    valor = request.form.get('posicion_foco', '50 50')
    foto.posicion_foco = valor
    db.session.commit()
    return ('', 204)

# ==========================================
# INICIO
# ==========================================
 


##Acivar ESTO AL HACER EL DEPLOY 

with app.app_context():
    db.create_all()

if __name__ == '__main__':
       with app.app_context():
            db.create_all()
            
            # Leemos del archivo .env. 
            # Si no pusiste nada en el .env, estas variables serán None
            user = os.environ.get('ADMIN_USER')
            pwd = os.environ.get('ADMIN_PASSWORD')
      #     
            if user and pwd:
                if not Admin.query.filter_by(username=user).first():
                    hashed_pw = generate_password_hash(pwd, method='pbkdf2:sha256')
                    db.session.add(Admin(username=user, password=hashed_pw))
                    db.session.commit()
                    print(f"✅ Usuario '{user}' creado correctamente.")
            else:
                print("⚠️ ERROR: No configuraste ADMIN_USER o ADMIN_PASSWORD en el archivo .env")
app.run(debug=True)
