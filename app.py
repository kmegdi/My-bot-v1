import os
import time
import subprocess
import sys
import psutil
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PASSWORD = "XZANJA"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'py'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_script_running(filename):
    """تحقق إذا كان السكربت قيد التشغيل"""
    pid_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_pid.txt")
    if not os.path.exists(pid_file):
        return False
    
    with open(pid_file, 'r') as f:
        try:
            pid = int(f.read())
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                return process.is_running()
            return False
        except (ValueError, psutil.NoSuchProcess):
            return False

@app.route('/Api-hosting-python-by-xzanja-py/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORD:
            return redirect('/how-to-use')
    return render_template('login.html')

@app.route('/how-to-use', methods=['GET', 'POST'])
def how_to_use():
    if request.method == 'POST':
        return redirect('/dashboard')
    return render_template('how_to_use.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    script_statuses = {file: is_script_running(file) for file in files if file.endswith('.py')}
    message = ""
    
    if request.method == "POST":
        package_name = request.form.get('package_name')
        message = install_package(package_name)
    
    return render_template('dashboard.html', files=files, message=message, script_statuses=script_statuses)

@app.route('/lgos')
def logs_list():
    log_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('_log.txt')]
    return render_template('logs.html', logs=log_files)

def install_package(package_name):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return f"تم تثبيت المكتبة {package_name} بنجاح!"
    except subprocess.CalledProcessError:
        return f"فشل في تثبيت المكتبة {package_name}."

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return redirect('/dashboard')
    return redirect('/dashboard')

@app.route('/run/<filename>')
def run_script(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return f"<h3>الملف <b>{filename}</b> غير موجود.</h3><br><a href='/dashboard'>رجوع</a>"
    
    if is_script_running(filename):
        return f"<h3>السكربت <b>{filename}</b> يعمل بالفعل.</h3><br><a href='/dashboard'>رجوع</a>"
    
    try:
        log_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_log.txt")
        with open(log_path, 'w') as f:
            process = subprocess.Popen(['python3', filepath], stdout=f, stderr=f)
        
        pid_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_pid.txt")
        with open(pid_file, 'w') as pid_f:
            pid_f.write(str(process.pid))
        
        return f"<h3>تم تشغيل السكربت <b>{filename}</b> في الخلفية.</h3><br><a href='/dashboard'>رجوع</a><br><a href='/log/{filename}'>عرض السجل</a>"
    except Exception as e:
        return f"<h3>خطأ أثناء التشغيل:</h3><pre>{str(e)}</pre>"

@app.route('/stop/<filename>')
def stop_script(filename):
    try:
        pid_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_pid.txt")
        if not os.path.exists(pid_file):
            return f"<h3>لم يتم العثور على PID للسكربت <b>{filename}</b>.</h3><br><a href='/dashboard'>رجوع</a>"

        with open(pid_file, 'r') as pid_f:
            process_pid = int(pid_f.read())
        
        try:
            process = psutil.Process(process_pid)
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()
            
            time.sleep(1)
            
            if os.path.exists(pid_file):
                os.remove(pid_file)
                
            return f"<h3>تم إيقاف السكربت <b>{filename}</b>.</h3><br><a href='/dashboard'>رجوع</a>"
        except psutil.NoSuchProcess:
            return f"<h3>السكربت <b>{filename}</b> غير قيد التشغيل.</h3><br><a href='/dashboard'>رجوع</a>"
    except Exception as e:
        return f"<h3>خطأ في إيقاف السكربت:</h3><pre>{str(e)}</pre>"

@app.route('/restart/<filename>')
def restart_script(filename):
    try:
        pid_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_pid.txt")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return f"<h3>الملف <b>{filename}</b> غير موجود.</h3><br><a href='/dashboard'>رجوع</a>"

        if os.path.exists(pid_file):
            with open(pid_file, 'r') as pid_f:
                process_pid = int(pid_f.read())
            try:
                process = psutil.Process(process_pid)
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()
                
                time.sleep(1)

                if os.path.exists(pid_file):
                    os.remove(pid_file)
            except psutil.NoSuchProcess:
                pass

        log_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_log.txt")
        with open(log_path, 'w') as f:
            process = subprocess.Popen(['python3', filepath], stdout=f, stderr=f)

        with open(pid_file, 'w') as pid_f:
            pid_f.write(str(process.pid))

        return f"<h3>تم إعادة تشغيل السكربت <b>{filename}</b>.</h3><br><a href='/dashboard'>رجوع</a><br><a href='/log/{filename}'>عرض السجل</a>"
    
    except Exception as e:
        return f"<h3>خطأ أثناء إعادة التشغيل:</h3><pre>{str(e)}</pre>"

@app.route('/log/<filename>')
def view_log(filename):
    log_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_log.txt")
    if not os.path.exists(log_path):
        return "<h3>لا يوجد سجل لهذا السكربت.</h3>"
    with open(log_path, 'r') as f:
        content = f.read()
    return f"<h3>Log for {filename}</h3><pre>{content}</pre><br><a href='/dashboard'>رجوع</a>"

@app.route('/before-upload')
def before_upload():
    return render_template('before_upload.html', allowed=ALLOWED_EXTENSIONS)

@app.route('/choose-time', methods=['GET', 'POST'])
def choose_time():
    if request.method == 'POST':
        selected_time = request.form.get('selected_time')
        return redirect('/before-upload')
    times = ['12 يوم', '30 شهر', '10 يوم', '7 أسبوع', 'أيام أخرى']
    return render_template('choose_time.html', times=times)

@app.route('/speed')
def speed():
    start = time.time()
    for _ in range(1000000):
        pass
    end = time.time()
    return f"<h2>Speed Test Done in {end - start:.4f} seconds</h2>"

if __name__ == '__main__':
    app.run(debug=True)