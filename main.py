import telebot
import os
import zipfile
import subprocess

# قراءة التوكن من Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("الرجاء ضبط متغير البيئة BOT_TOKEN لتشغيل البوت.")

bot = telebot.TeleBot(BOT_TOKEN)

# المجلد الذي سيُحفظ فيه المشروع
BASE_DIR = "/tmp/uploaded_projects"

# التأكد من وجود المجلد
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحبًا! أرسل لي ملف ZIP يحتوي على مشروعك مع ملف Procfile و requirements.txt.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        # تنزيل الملف
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # اسم الملف
        file_name = message.document.file_name
        file_path = os.path.join(BASE_DIR, file_name)

        with open(file_path, "wb") as f:
            f.write(downloaded_file)

        bot.reply_to(message, "تم استلام الملف! جاري فك الضغط...")

        # فك ضغط الملف
        if file_name.endswith(".zip"):
            project_dir = os.path.join(BASE_DIR, file_name.replace(".zip", ""))
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(project_dir)

            bot.reply_to(message, "تم فك الضغط بنجاح! جاري البحث عن ملف Procfile...")
            process_project(project_dir, message)
        else:
            bot.reply_to(message, "الرجاء إرسال ملف ZIP فقط.")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء معالجة الملف: {str(e)}")

def process_project(project_dir, message):
    try:
        # البحث عن ملف Procfile
        procfile_path = find_file("Procfile", project_dir)
        if not procfile_path:
            bot.reply_to(message, "ملف Procfile غير موجود داخل المشروع!")
            return

        bot.reply_to(message, f"تم العثور على ملف Procfile في: {procfile_path}")

        # تثبيت المكتبات من requirements.txt إذا وجد
        requirements_path = find_file("requirements.txt", project_dir)
        if requirements_path:
            bot.reply_to(message, "تم العثور على ملف requirements.txt. جاري تثبيت المكتبات...")
            install_requirements(requirements_path, message)
        else:
            bot.reply_to(message, "ملف requirements.txt غير موجود. سيتم تشغيل المشروع بدون تثبيت مكتبات.")

        # تشغيل المشروع
        run_procfile(procfile_path, message)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء معالجة المشروع: {str(e)}")

def find_file(file_name, search_dir):
    """البحث عن ملف معين في جميع المجلدات الفرعية."""
    for root, dirs, files in os.walk(search_dir):
        if file_name in files:
            return os.path.join(root, file_name)
    return None

def install_requirements(requirements_path, message):
    try:
        command = f"pip install -r {requirements_path}"
        process = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot.reply_to(message, "تم تثبيت المكتبات بنجاح!")
    except subprocess.CalledProcessError as e:
        bot.reply_to(message, f"حدث خطأ أثناء تثبيت المكتبات: {e.stderr.decode()}")

def run_procfile(procfile_path, message):
    try:
        # قراءة ملف Procfile
        with open(procfile_path, "r") as f:
            lines = f.readlines()

        # البحث عن السطر الذي يبدأ بـ worker
        for line in lines:
            if line.startswith("worker:"):
                # استخراج الأمر بعد "worker:"
                command = line.split("worker:")[1].strip()
                bot.reply_to(message, f"جاري تشغيل الأمر: {command}")
                
                # تشغيل الأمر
                process = subprocess.Popen(command, shell=True, cwd=os.path.dirname(procfile_path))
                bot.reply_to(message, f"تم تشغيل المشروع بنجاح! PID: {process.pid}")
                return
        
        bot.reply_to(message, "لم يتم العثور على تعريف worker في ملف Procfile!")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء تشغيل Procfile: {str(e)}")

# بدء تشغيل البوت
bot.polling()
