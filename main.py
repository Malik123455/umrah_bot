import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TOKEN
from mofa_selenium import MOFAVisaBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌙 *مرحباً بك في بوت تأشيرات العمرة*\n\n"
        "📌 أرسل *رقم الجواز* لطباعة التأشيرة\n"
        "مثال: `13913933`\n\n"
        "⚠️ ملاحظة: قد يستغرق البحث 30-60 ثانية",
        parse_mode='Markdown'
    )

async def handle_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    passport_number = update.message.text.strip().upper()
    
    msg = await update.message.reply_text(
        f"🔍 جاري الاستعلام عن التأشيرة برقم: `{passport_number}`\n"
        f"⏳ جاري فتح المتصفح وحل رمز التحقق... يرجى الانتظار (30-60 ثانية)",
        parse_mode='Markdown'
    )
    
    bot = None
    try:
        # إنشاء كائن البوت
        bot = MOFAVisaBot(headless=False)
        
        # البحث عن التأشيرة
        result = bot.search_visa(passport_number, first_name="محمد")
        
        if result['success']:
            pdf_path = result['pdf_path']
            visa_data = result.get('visa_data', {})
            
            # إرسال PDF
            with open(pdf_path, 'rb') as pdf:
                await update.message.reply_document(
                    document=pdf,
                    filename=os.path.basename(pdf_path),
                    caption=f"✅ *تم العثور على التأشيرة*\n\n"
                            f"👤 *الاسم:* {visa_data.get('full_name', 'غير متوفر')}\n"
                            f"🆔 *رقم الجواز:* {visa_data.get('passport_number', passport_number)}\n"
                            f"📄 تم إنشاء PDF بنفس تنسيق الصفحة الأصلية",
                    parse_mode='Markdown'
                )
            
            # حذف الملف المؤقت بعد الإرسال
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            await msg.edit_text("✅ تم استخراج التأشيرة بنجاح!")
        else:
            await msg.edit_text(
                f"❌ {result['message']}\n\n"
                f"🔗 يمكنك الاستعلام يدوياً:\n"
                f"https://visa.mofa.gov.sa/Visaservices/SearchVisa\n\n"
                f"📌 البيانات المطلوبة:\n"
                f"• رقم الجواز: {passport_number}\n"
                f"• الاسم الأول: محمد\n"
                f"• الجنسية: اليمن\n"
                f"• رمز التحقق: كما في الصورة"
            )
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if bot:
            bot.close()

def main():
    # التأكد من وجود مجلد outputs
    os.makedirs("outputs", exist_ok=True)
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport))
    
    print("🚀 بوت تلجرام يعمل...")
    print("📌 أرسل رقم الجواز للاستعلام عن التأشيرة")
    app.run_polling()

if __name__ == '__main__':
    main()