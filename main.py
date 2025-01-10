import telebot
import os
import zipfile
import subprocess
import threading
import signal

# قراءة التوكن من Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("الرجاء ضبط متغير البيئة BOT_TOKEN لتشغيل البوت.")

bot = telebot.TeleBot(BOT_TOKEN)

# المجلد الذي سيُحفظ فيه المشروع
BASE_DIR = "uploaded_projects"

# التأكد من وجود المجلد
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# متغير للتحكم في العمليات
processes = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحبًا! أرسل لي ملف ZIP يحتوي على مشروعك مع ملف Procfile.")

@bot.message_handler(commands=['s'])
def stop(message):
    # إيقاف العملية التي تم تشغيلها من خلال Procfile
    global processes
    if processes:
        for pid, process in processes.items():
            process.terminate()
            bot.reply_to(message, f"تم إيقاف العملية: {pid}")
        processes.clear()
    else:
        bot.reply_to(message, "لا توجد عملية قيد التشغيل للإيقاف.")

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
            run_procfile(project_dir, message)
        else:
            bot.reply_to(message, "الرجاء إرسال ملف ZIP فقط.")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء معالجة الملف: {str(e)}")

def run_procfile(project_dir, message):
    try:
        # مسار ملف Procfile
        procfile_path = os.path.join(project_dir, "Procfile")
        if not os.path.exists(procfile_path):
            bot.reply_to(message, "ملف Procfile غير موجود داخل المشروع!")
            return

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
                process = subprocess.Popen(command, shell=True, cwd=project_dir)
                processes[process.pid] = process  # حفظ العملية في القاموس
                bot.reply_to(message, f"تم تشغيل المشروع بنجاح! PID: {process.pid}")
                return
        
        bot.reply_to(message, "لم يتم العثور على تعريف worker في ملف Procfile!")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء قراءة أو تشغيل Procfile: {str(e)}")

# بدء تشغيل البوت
bot.polling()
