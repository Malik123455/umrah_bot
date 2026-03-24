import time
import os
import easyocr
import cv2
import numpy as np
import re
import base64
import glob
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# ========== إعدادات المسارات ==========
CHROME_DRIVER_PATH = r'C:\Users\malik\Desktop\umrah_bot\chromedriver-win64\chromedriver.exe'

# ========== ألوان للطباعة في التيرمينال ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class MOFAVisaBot:
    def __init__(self, headless=False):
        """تهيئة بوت الاستعلام عن التأشيرات"""
        print(f"{Colors.CYAN}🔧 MOFAVisaBot: جاري تهيئة المتصفح...{Colors.ENDC}")
        
        # إعداد خيارات المتصفح
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # إعدادات للطباعة
        chrome_options.add_argument("--kiosk-printing")
        chrome_options.add_experimental_option("prefs", {
            "printing.print_preview_sticky_settings.appState": '{"recentDestinations":[{"id":"Save as PDF","origin":"local"}],"selectedDestinationId":"Save as PDF","version":2}',
            "savefile.default_directory": os.path.abspath("outputs")
        })
        
        # تهيئة EasyOCR مع إعدادات محسنة
        print(f"{Colors.CYAN}📦 جاري تحميل EasyOCR...{Colors.ENDC}")
        self.reader = easyocr.Reader(['en'], gpu=False)
        print(f"{Colors.GREEN}✅ تم تحميل EasyOCR بنجاح{Colors.ENDC}")
        
        # تشغيل المتصفح
        self.driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
    def _preprocess_image(self, image_path):
        """تحسين جودة الصورة قبل القراءة مع تكبير"""
        img = cv2.imread(image_path)
        
        # تحويل إلى تدرج الرمادي
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # زيادة التباين
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # إزالة الضوضاء
        denoised = cv2.medianBlur(thresh, 3)
        
        # تكبير الصورة لتحسين القراءة
        scale_percent = 150
        width = int(denoised.shape[1] * scale_percent / 100)
        height = int(denoised.shape[0] * scale_percent / 100)
        enlarged = cv2.resize(denoised, (width, height), interpolation=cv2.INTER_CUBIC)
        
        # حفظ الصورة المحسنة
        enhanced_path = 'captcha_enhanced.png'
        cv2.imwrite(enhanced_path, enlarged)
        
        return enhanced_path
    
    def _solve_captcha(self):
        """حل الكابتشا باستخدام EasyOCR مع تحسينات متعددة"""
        try:
            # العثور على صورة الكابتشا
            captcha_img = self.driver.find_element(By.ID, "imgCaptcha")
            
            # التقاط الصورة
            captcha_img.screenshot('captcha_temp.png')
            
            # تحسين جودة الصورة
            enhanced_image = self._preprocess_image('captcha_temp.png')
            
            # استخدام EasyOCR مع إعدادات محسنة
            result = self.reader.readtext(
                enhanced_image, 
                paragraph=False, 
                allowlist='0123456789',
                text_threshold=0.5,
                low_text=0.3,
                link_threshold=0.3,
                canvas_size=2000,
                mag_ratio=1.5,
                width_ths=0.5,
                height_ths=0.5
            )
            
            # استخراج الأرقام فقط
            captcha_text = ''
            for detection in result:
                text = detection[1]
                text = ''.join([c for c in text if c.isdigit()])
                captcha_text += text
            
            # تنظيف النص
            captcha_text = captcha_text.strip()
            
            # التأكد من أن النص مكون من 6 أرقام
            if len(captcha_text) > 6:
                captcha_text = captcha_text[:6]
            
            # حذف الملفات المؤقتة
            for file in ['captcha_temp.png', 'captcha_enhanced.png']:
                if os.path.exists(file):
                    os.remove(file)
            
            print(f"   {Colors.GREEN}🔐 تم قراءة الكابتشا: {captcha_text} ({len(captcha_text)} أرقام){Colors.ENDC}")
            return captcha_text
            
        except Exception as e:
            print(f"   {Colors.FAIL}❌ خطأ في قراءة الكابتشا: {e}{Colors.ENDC}")
            return ""
    
    def _solve_captcha_with_retry(self, max_retries=2):
        """حل الكابتشا مع إعادة المحاولة إذا كان النص غير مكتمل"""
        for attempt in range(max_retries):
            captcha_text = self._solve_captcha()
            
            if len(captcha_text) == 6:
                return captcha_text
            else:
                if attempt < max_retries - 1:
                    print(f"   {Colors.WARNING}⚠️ تم قراءة {len(captcha_text)} أرقام فقط، تحديث الصورة والمحاولة مرة أخرى...{Colors.ENDC}")
                    self._refresh_captcha()
                    time.sleep(1)
        
        return captcha_text
    
    def _refresh_captcha(self):
        """تحديث صورة الكابتشا"""
        try:
            refresh_btn = self.driver.find_element(By.ID, "btnRefreshCaptcha")
            refresh_btn.click()
            time.sleep(1)
            print(f"   {Colors.WARNING}🔄 تم تحديث صورة الكابتشا{Colors.ENDC}")
            return True
        except:
            return False
    
    def _select_nationality(self):
        """اختيار الجنسية من القائمة"""
        try:
            nationality_container = self.wait.until(
                EC.element_to_be_clickable((By.ID, "select2-NationalityId-container"))
            )
            nationality_container.click()
            time.sleep(1)
            search_box = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field"))
            )
            search_box.clear()
            search_box.send_keys("اليمن")
            time.sleep(2)
            result = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'اليمن')]"))
            )
            result.click()
            time.sleep(1)
            print(f"   {Colors.GREEN}✅ تم اختيار الجنسية: اليمن{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"   {Colors.FAIL}❌ فشل اختيار الجنسية: {e}{Colors.ENDC}")
            return False
    
    def _extract_visa_info(self):
        """استخراج اسم صاحب التأشيرة ورقم الجواز من الصفحة"""
        visa_data = {
            'full_name': '',
            'passport_number': ''
        }
        
        try:
            # البحث عن الاسم
            name_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'col-3')]")
            for elem in name_elements:
                text = elem.text
                if 'الاسم' in text and 'Name' in text:
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        visa_data['full_name'] = lines[1].strip()
                        print(f"   {Colors.GREEN}✅ تم استخراج الاسم: {visa_data['full_name']}{Colors.ENDC}")
            
            # البحث عن رقم الجواز
            for elem in name_elements:
                text = elem.text
                if 'رقم الجواز' in text or 'Passport No' in text:
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        visa_data['passport_number'] = lines[1].strip()
                        print(f"   {Colors.GREEN}✅ تم استخراج رقم الجواز: {visa_data['passport_number']}{Colors.ENDC}")
            
            return visa_data
        except Exception as e:
            print(f"   {Colors.WARNING}⚠️ فشل استخراج البيانات: {e}{Colors.ENDC}")
            return visa_data
    
    def _print_to_pdf(self, passport_number, full_name=""):
        """طباعة الصفحة إلى PDF باستخدام أمر الطباعة في المتصفح"""
        # إنشاء اسم ملف مناسب
        if full_name:
            clean_name = re.sub(r'[\\/*?:"<>|]', '_', full_name)
            clean_name = clean_name.replace(' ', '_')
            filename = f"Visa_{passport_number}_{clean_name}.pdf"
        else:
            filename = f"Visa_{passport_number}.pdf"
        
        pdf_path = os.path.join("outputs", filename)
        os.makedirs("outputs", exist_ok=True)
        
        try:
            # استخدام JavaScript لفتح نافذة الطباعة
            js_script = """
            (function() {
                var style = document.createElement('style');
                style.innerHTML = '@media print { body { margin: 0; padding: 0; } .evisa-container { page-break-after: avoid; } }';
                document.head.appendChild(style);
                window.print();
                return true;
            })();
            """
            
            self.driver.execute_script(js_script)
            time.sleep(3)
            
            # البحث عن ملف PDF تم حفظه تلقائياً
            downloads_path = str(Path.home() / "Downloads")
            pdf_files = glob.glob(os.path.join(downloads_path, "*.pdf"))
            
            if pdf_files:
                latest_pdf = max(pdf_files, key=os.path.getctime)
                shutil.copy2(latest_pdf, pdf_path)
                print(f"{Colors.GREEN}✅ تم إنشاء PDF: {pdf_path}{Colors.ENDC}")
                return pdf_path
            
            print(f"{Colors.WARNING}⚠️ لم يتم العثور على ملف PDF، استخدام الطريقة البديلة{Colors.ENDC}")
            return self._print_to_pdf_cdp(passport_number, full_name)
            
        except Exception as e:
            print(f"{Colors.FAIL}❌ فشل الطباعة: {e}{Colors.ENDC}")
            return self._print_to_pdf_cdp(passport_number, full_name)
    
    def _print_to_pdf_cdp(self, passport_number, full_name=""):
        """طباعة الصفحة باستخدام Chrome DevTools Protocol"""
        if full_name:
            clean_name = re.sub(r'[\\/*?:"<>|]', '_', full_name)
            clean_name = clean_name.replace(' ', '_')
            filename = f"Visa_{passport_number}_{clean_name}.pdf"
        else:
            filename = f"Visa_{passport_number}.pdf"
        
        pdf_path = os.path.join("outputs", filename)
        os.makedirs("outputs", exist_ok=True)
        
        try:
            result = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "landscape": False,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": True,
                "paperWidth": 8.27,
                "paperHeight": 11.69,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
                "scale": 1.0
            })
            
            pdf_data = base64.b64decode(result['data'])
            
            with open(pdf_path, "wb") as f:
                f.write(pdf_data)
            
            print(f"{Colors.GREEN}✅ تم إنشاء PDF باستخدام CDP: {pdf_path}{Colors.ENDC}")
            return pdf_path
            
        except Exception as e:
            print(f"{Colors.FAIL}❌ فشل الطباعة باستخدام CDP: {e}{Colors.ENDC}")
            return None
    
    def search_visa(self, passport_number, first_name="محمد"):
        """البحث عن تأشيرة برقم الجواز"""
        print(f"{Colors.BLUE}🔍 جاري البحث عن التأشيرة برقم الجواز: {passport_number}{Colors.ENDC}")
        
        try:
            # فتح الموقع
            print(f"{Colors.CYAN}🌐 جاري فتح موقع وزارة الخارجية...{Colors.ENDC}")
            self.driver.get("https://visa.mofa.gov.sa/Visaservices/SearchVisa")
            time.sleep(5)
            
            # إغلاق نافذة الكوكيز
            try:
                cookie_btn = self.driver.find_element(By.CLASS_NAME, "acceptcookies")
                cookie_btn.click()
                print(f"{Colors.GREEN}✅ تم إغلاق نافذة الكوكيز{Colors.ENDC}")
                time.sleep(1)
            except:
                pass
            
            # 1. اختيار "رقم الجواز"
            print(f"{Colors.CYAN}1️⃣ اختيار رقم الجواز...{Colors.ENDC}")
            first_select = Select(self.wait.until(
                EC.element_to_be_clickable((By.ID, "ddlFirstValue"))
            ))
            first_select.select_by_value("PassPortNo")
            time.sleep(1)
            
            # 2. كتابة رقم الجواز
            print(f"{Colors.CYAN}2️⃣ كتابة رقم الجواز...{Colors.ENDC}")
            field1 = self.driver.find_element(By.ID, "tbFirstValue")
            field1.clear()
            field1.send_keys(passport_number)
            
            # 3. اختيار "الاسم الاول"
            print(f"{Colors.CYAN}3️⃣ اختيار الاسم الاول...{Colors.ENDC}")
            second_select = Select(self.driver.find_element(By.ID, "ddlSecondValue"))
            second_select.select_by_value("fName")
            time.sleep(1)
            
            # 4. كتابة الاسم
            print(f"{Colors.CYAN}4️⃣ كتابة الاسم...{Colors.ENDC}")
            field2 = self.driver.find_element(By.ID, "tbSecondValue")
            field2.clear()
            field2.send_keys(first_name)
            
            # 5. اختيار الجنسية
            print(f"{Colors.CYAN}5️⃣ اختيار الجنسية...{Colors.ENDC}")
            self._select_nationality()
            
            # 6. حل الكابتشا مع تحسينات
            print(f"\n{Colors.BOLD}🔐 جاري حل رمز التحقق...{Colors.ENDC}")
            max_attempts = 3
            search_success = False
            
            for attempt in range(max_attempts):
                print(f"{Colors.WARNING}📝 محاولة {attempt + 1}/{max_attempts}{Colors.ENDC}")
                
                # استخدام الدالة المحسنة مع إعادة المحاولة الداخلية
                captcha_text = self._solve_captcha_with_retry(max_retries=2)
                
                if captcha_text and len(captcha_text) == 6:
                    captcha_field = self.driver.find_element(By.ID, "Captcha")
                    captcha_field.clear()
                    captcha_field.send_keys(captcha_text)
                    
                    print(f"{Colors.GREEN}📝 تم إدخال الرمز: {captcha_text}{Colors.ENDC}")
                    print(f"{Colors.CYAN}🔍 جاري البحث...{Colors.ENDC}")
                    search_btn = self.driver.find_element(By.ID, "btnSubmit")
                    search_btn.click()
                    time.sleep(5)
                    
                    # التحقق من النتيجة
                    error_msgs = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
                    if error_msgs:
                        error_text = error_msgs[0].text
                        if "رمز الصورة" in error_text or "captcha" in error_text.lower():
                            print(f"{Colors.WARNING}⚠️ رمز التحقق غير صحيح، إعادة المحاولة...{Colors.ENDC}")
                            self._refresh_captcha()
                            continue
                        else:
                            return {'success': False, 'message': error_text}
                    else:
                        print(f"{Colors.GREEN}✅ تم الاستعلام بنجاح!{Colors.ENDC}")
                        search_success = True
                        break
                else:
                    print(f"{Colors.WARNING}⚠️ فشل قراءة الكابتشا ({len(captcha_text)} أرقام)، تحديث الصورة...{Colors.ENDC}")
                    self._refresh_captcha()
            
            if not search_success:
                return {'success': False, 'message': 'فشل حل الكابتشا بعد عدة محاولات'}
            
            # انتظار تحميل الصفحة
            time.sleep(3)
            
            # استخراج بيانات صاحب التأشيرة
            visa_info = self._extract_visa_info()
            
            # طباعة الصفحة إلى PDF
            pdf_path = self._print_to_pdf(passport_number, visa_info['full_name'])
            
            if pdf_path and os.path.exists(pdf_path):
                return {'success': True, 'pdf_path': pdf_path, 'visa_data': visa_info}
            else:
                return {'success': False, 'message': 'فشل في إنشاء PDF من صفحة التأشيرة'}
                
        except Exception as e:
            print(f"{Colors.FAIL}❌ خطأ: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    def close(self):
        """إغلاق المتصفح"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print(f"{Colors.CYAN}🔧 MOFAVisaBot: تم إغلاق المتصفح{Colors.ENDC}")