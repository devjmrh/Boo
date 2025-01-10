import telebot
import os
import subprocess
import speedtest

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحبًا! أرسل لي ملف ZIP يحتوي على مشروعك مع ملف Procfile.")

@bot.message_handler(commands=['stop'])
def stop_process(message):
    global running_process
    if running_process and running_process.poll() is None:
        running_process.terminate()
        bot.reply_to(message, "تم إيقاف العملية بنجاح.")
    else:
        bot.reply_to(message, "لا توجد عملية قيد التشغيل حاليًا.")

@bot.message_handler(commands=['logs'])
def get_logs(message):
    global log_file_path
    if log_file_path and os.path.exists(log_file_path):
        with open(log_file_path, "r") as log_file:
            logs = log_file.readlines()[-10:]
        bot.reply_to(message, "آخر 10 أسطر من السجل:\n" + "".join(logs))
    else:
        bot.reply_to(message, "لم يتم العثور على سجل أو أن السجل فارغ.")

@bot.message_handler(commands=['net'])
def check_network_speed(message):
    try:
        bot.reply_to(message, "جاري قياس سرعة الإنترنت، يرجى الانتظار...")
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000  # تحويل إلى ميغابت
        upload_speed = st.upload() / 1_000_000      # تحويل إلى ميغابت
        ping = st.results.ping

        bot.reply_to(
            message,
            f"سرعة الإنترنت:\n"
            f"📥 تنزيل: {download_speed:.2f} Mbps\n"
            f"📤 رفع: {upload_speed:.2f} Mbps\n"
            f"📡 Ping: {ping:.2f} ms"
        )
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء قياس سرعة الإنترنت: {str(e)}")

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
            read_procfile_and_run(project_dir, message)
        else:
            bot.reply_to(message, "الرجاء إرسال ملف ZIP فقط.")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء معالجة الملف: {str(e)}")

def read_procfile_and_run(project_dir, message):
    try:
        global running_process, log_file_path

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

                # تشغيل الأمر وحفظ السجل
                log_file_path = os.path.join(project_dir, "logs.txt")
                with open(log_file_path, "w") as log_file:
                    running_process = subprocess.Popen(
                        command, shell=True, cwd=project_dir, stdout=log_file, stderr=subprocess.STDOUT
                    )
                bot.reply_to(message, f"تم تشغيل المشروع بنجاح! PID: {running_process.pid}")
                return
        
        bot.reply_to(message, "لم يتم العثور على تعريف worker في ملف Procfile!")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء قراءة أو تشغيل Procfile: {str(e)}")

# تعريف المتغيرات العالمية
running_process = None
log_file_path = None

# بدء تشغيل البوت
bot.polling()
