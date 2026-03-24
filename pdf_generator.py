import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import requests
from io import BytesIO
from PIL import Image

# تسجيل خط عربي (اختياري - لتحسين عرض العربية)
try:
    # محاولة تحميل خط عربي من النظام
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    ARABIC_FONT = 'Arial'
except:
    ARABIC_FONT = 'Helvetica'

class Colors:
    PURPLE = HexColor('#9379b6')
    DARK_PURPLE = HexColor('#371260')
    RED = HexColor('#ed1c24')
    DARK_GRAY = HexColor('#333333')
    LIGHT_GRAY = HexColor('#f5f5f5')
    WHITE = HexColor('#ffffff')

def create_visa_pdf(visa_data):
    """إنشاء ملف PDF مطابق تماماً لتصميم التأشيرة"""
    
    passport = visa_data.get('passport_number', 'unknown')
    filename = f"outputs/visa_{passport}.pdf"
    os.makedirs("outputs", exist_ok=True)
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # ========== إعدادات الخطوط ==========
    c.setFont("Helvetica", 10)
    
    # ========== إطار خارجي ==========
    c.setStrokeColor(Colors.PURPLE)
    c.setLineWidth(2)
    c.rect(30, 30, width - 60, height - 60)
    
    # ========== الهيدر (الشعارات) ==========
    y_start = height - 50
    
    # شعار وزارة الخارجية (يسار)
    # ملاحظة: يتم رسم مربع بدلاً من الصورة لتجنب مشاكل المسار
    c.setFillColor(Colors.PURPLE)
    c.rect(50, y_start - 30, 80, 40, fill=0)
    c.setFillColor(Colors.WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(55, y_start - 15, "KSA VISA")
    
    # شعار وزارة الحج (يمين)
    c.setFillColor(Colors.PURPLE)
    c.rect(width - 130, y_start - 30, 80, 40, fill=0)
    c.setFillColor(Colors.WHITE)
    c.drawString(width - 125, y_start - 15, "KSA")
    
    # ========== العنوان الرئيسي ==========
    y = height - 100
    c.setFillColor(Colors.DARK_PURPLE)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, y, "Umrah Visa")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, y - 30, "تأشيرة العمرة")
    
    # ========== صورة التأشيرة (مربع رمادي) ==========
    y -= 70
    c.setFillColor(Colors.LIGHT_GRAY)
    c.rect(50, y - 80, width - 100, 80, fill=1, stroke=0)
    c.setFillColor(Colors.DARK_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(width / 2 - 40, y - 40, "Visa Image")
    
    # ========== البيانات الرئيسية (أول صف) ==========
    y -= 100
    y = self._draw_row(c, width, y, "رقم التأشيرة", visa_data.get('visa_number', 'غير متوفر'), "Visa No.")
    y -= 15
    y = self._draw_row(c, width, y, "صالحة اعتباراً من", visa_data.get('issue_date', 'غير متوفر'), "Valid From")
    y -= 15
    y = self._draw_row(c, width, y, "صالحة لغاية", visa_data.get('expiry_date', 'غير متوفر'), "Valid until")
    y -= 15
    
    # مدة الإقامة (صف خاص)
    duration = visa_data.get('duration', '90 Days - ٩٠ يوم')
    c.setFont("Helvetica", 10)
    c.setFillColor(Colors.DARK_PURPLE)
    c.drawString(100, y, "مدة الإقامة:")
    c.setFillColor(Colors.DARK_GRAY)
    c.drawString(250, y, duration)
    c.setFillColor(Colors.DARK_PURPLE)
    c.drawString(width - 180, y, "Duration of Stay")
    
    y -= 25
    y = self._draw_row(c, width, y, "رقم الجواز", visa_data.get('passport_number', 'غير متوفر'), "Passport No.")
    
    # ========== خط فاصل ==========
    y -= 20
    c.setStrokeColor(Colors.PURPLE)
    c.setLineWidth(0.5)
    c.line(80, y, width - 80, y)
    
    # ========== بيانات إضافية ==========
    y -= 25
    y = self._draw_row(c, width, y, "مصدر التأشيرة", "Saudi Digital Embassy - السفارة السعودية الرقمية", "Place of issue")
    y -= 15
    y = self._draw_row(c, width, y, "الاسم", visa_data.get('full_name', 'غير متوفر'), "Name")
    y -= 15
    y = self._draw_row(c, width, y, "الجنسية", f"Yemen - {visa_data.get('nationality', 'اليمن')}", "Nationality")
    y -= 15
    y = self._draw_row(c, width, y, "تاريخ الميلاد", visa_data.get('date_of_birth', 'غير متوفر'), "Birth Date")
    y -= 15
    y = self._draw_row(c, width, y, "نوع التأشيرة", "Umrah - عمرة", "Visa Type")
    
    # ========== خط فاصل ==========
    y -= 20
    c.setStrokeColor(Colors.PURPLE)
    c.line(80, y, width - 80, y)
    
    # ========== معلومات إضافية ==========
    y -= 25
    y = self._draw_row(c, width, y, "مكتب العمرة", "شركة الاتصال الميداني شركة شخص واحد", "Umrah Operator")
    y -= 15
    y = self._draw_row(c, width, y, "الوكيل الخارجي", "ريو تورز للسفريات والسياحة والحج والعمرة", "External Agent")
    y -= 15
    y = self._draw_row(c, width, y, "رقم الحدود", "", "Border No.")
    
    # ========== الباركود (محاكاة) ==========
    y -= 30
    c.setFillColor(Colors.DARK_GRAY)
    c.rect(100, y - 20, width - 200, 20, fill=1, stroke=0)
    c.setFillColor(Colors.WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width / 2, y - 13, visa_data.get('visa_number', '6157894260'))
    
    # ========== ملاحظات مهمة ==========
    y -= 50
    c.setFillColor(Colors.RED)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width / 2, y, "غير مصرح بالحج أو الدخول إلى مكة المكرمة خلال موسم الحج")
    y -= 15
    c.setFont("Helvetica", 7)
    c.drawCentredString(width / 2, y, "Not permitted to perform Hajj, enter or stay in Makkah during Hajj season")
    
    # ========== التذييل ==========
    y -= 40
    c.setFillColor(Colors.PURPLE)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 60, "وزارة الحج والعمرة - المملكة العربية السعودية")
    c.drawCentredString(width / 2, 45, "Ministry of Hajj and Umrah - Kingdom of Saudi Arabia")
    c.drawCentredString(width / 2, 30, f"تاريخ الطباعة: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # ========== رمز MRZ (محاكاة) ==========
    y = 20
    c.setFillColor(Colors.DARK_GRAY)
    c.setFont("Helvetica", 7)
    mrz1 = f"1<YEM{visa_data.get('full_name', 'ABDULAZIZ').upper().replace(' ', '<')[:30]}"
    mrz2 = f"{visa_data.get('passport_number', '13913933')}<0YEM{visa_data.get('date_of_birth', '01011989')}5"
    c.drawCentredString(width / 2, y, mrz1)
    c.drawCentredString(width / 2, y - 12, mrz2)
    
    c.save()
    return filename

def _draw_row(c, width, y, label_ar, value, label_en):
    """رسم صف من البيانات"""
    c.setFont("Helvetica", 10)
    c.setFillColor(Colors.DARK_PURPLE)
    c.drawString(80, y, f"{label_ar}:")
    
    c.setFillColor(Colors.DARK_GRAY)
    c.drawString(220, y, str(value))
    
    c.setFillColor(Colors.DARK_PURPLE)
    c.drawString(width - 200, y, label_en)
    
    return y - 20