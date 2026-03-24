import time
import os
import easyocr
import re
import base64
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# ========== ألوان للطباعة ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

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
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # مسار Chromium
        chrome_options.binary_location = "/usr/bin/chromium"
        
        # إعدادات للطباعة
        chrome_options.add_argument("--kiosk-printing")
        
        # تهيئة EasyOCR
        print(f"{Colors.CYAN}📦 جاري تحميل EasyOCR...{Colors.ENDC}")
        self.reader = easyocr.Reader(['en'], gpu=False)
        print(f"{Colors.GREEN}✅ تم تحميل EasyOCR بنجاح{Colors.ENDC}")
        
        # تشغيل المتصفح
        self.driver = webdriver.Chrome(
            options=chrome_options,
            service=Service("/usr/bin/chromedriver")
        )
        self.wait = WebDriverWait(self.driver, 20)
    
    def _solve_captcha(self):
        """حل الكابتشا باستخدام EasyOCR و PIL فقط (بدون OpenCV)"""
        try:
            captcha_img = self.driver.find_element(By.ID, "imgCaptcha")
            captcha_img.screenshot('captcha_temp.png')
            
            # تحسين الصورة باستخدام PIL فقط
            img = Image.open('captcha_temp.png')
            
            # تحويل إلى تدرج الرمادي
            img = img.convert('L')
            
            # زيادة التباين
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # عتبة بسيطة (أسود وأبيض)
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
            
            # إزالة الضوضاء
            img = img.filter(ImageFilter.MedianFilter(size=3))
            
            # تكبير الصورة
            width, height = img.size
            img = img.resize((int(width * 1.5), int(height * 1.5)), Image.Resampling.LANCZOS)
            
            img.save('captcha_enhanced.png')
            
            # EasyOCR
            result = self.reader.readtext(
                'captcha_enhanced.png', 
                paragraph=False, 
                allowlist='0123456789',
                text_threshold=0.5,
                low_text=0.3,
                mag_ratio=1.5
            )
            
            captcha_text = ''
            for detection in result:
                text = detection[1]
                text = ''.join([c for c in text if c.isdigit()])
                captcha_text += text
            
            captcha_text = captcha_text.strip()
            if len(captcha_text) > 6:
                captcha_text = captcha_text[:6]
            
            # حذف الملفات المؤقتة
            for file in ['captcha_temp.png', 'captcha_enhanced.png']:
                if os.path.exists(file):
                    os.remove(file)
            
            print(f"   {Colors.GREEN}🔐 تم قراءة الكابتشا: {captcha_text}{Colors.ENDC}")
            return captcha_text
            
        except Exception as e:
            print(f"   {Colors.FAIL}❌ خطأ في قراءة الكابتشا: {e}{Colors.ENDC}")
            return ""
    
    def _refresh_captcha(self):
        """تحديث صورة الكابتشا"""
        try:
            refresh_btn = self.driver.find_element(By.ID, "btnRefreshCaptcha")
            refresh_btn.click()
            time.sleep(1)
            print(f"   {Colors.WARNING}🔄 تم تحديث الكابتشا{Colors.ENDC}")
            return True
        except:
            return False
    
    def _select_nationality(self):
        """اختيار الجنسية"""
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
        """استخراج بيانات التأشيرة"""
        visa_data = {'full_name': '', 'passport_number': ''}
        try:
            elements = self.driver.find_elements(By.CLASS_NAME, "col-3")
            for elem in elements:
                text = elem.text
                if 'الاسم' in text and 'Name' in text:
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        visa_data['full_name'] = lines[1].strip()
                if 'رقم الجواز' in text or 'Passport No' in text:
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        visa_data['passport_number'] = lines[1].strip()
            return visa_data
        except Exception as e:
            print(f"   {Colors.WARNING}⚠️ فشل استخراج البيانات: {e}{Colors.ENDC}")
            return visa_data
    
    def _print_to_pdf(self, passport_number, full_name=""):
        """طباعة الصفحة إلى PDF"""
        if full_name:
            clean_name = re.sub(r'[\\/*?:"<>|]', '_', full_name).replace(' ', '_')
            filename = f"Visa_{passport_number}_{clean_name}.pdf"
        else:
            filename = f"Visa_{passport_number}.pdf"
        
        pdf_path = os.path.join("outputs", filename)
        os.makedirs("outputs", exist_ok=True)
        
        try:
            # استخدام CDP للطباعة
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
            
            print(f"{Colors.GREEN}✅ تم إنشاء PDF: {pdf_path}{Colors.ENDC}")
            return pdf_path
            
        except Exception as e:
            print(f"{Colors.FAIL}❌ فشل إنشاء PDF: {e}{Colors.ENDC}")
            return None
    
    def search_visa(self, passport_number, first_name="محمد"):
        """البحث عن تأشيرة"""
        print(f"{Colors.BLUE}🔍 البحث عن التأشيرة: {passport_number}{Colors.ENDC}")
        
        try:
            self.driver.get("https://visa.mofa.gov.sa/Visaservices/SearchVisa")
            time.sleep(5)
            
            # إغلاق الكوكيز
            try:
                cookie_btn = self.driver.find_element(By.CLASS_NAME, "acceptcookies")
                cookie_btn.click()
                time.sleep(1)
            except:
                pass
            
            # اختيار رقم الجواز
            first_select = Select(self.wait.until(
                EC.element_to_be_clickable((By.ID, "ddlFirstValue"))
            ))
            first_select.select_by_value("PassPortNo")
            time.sleep(1)
            
            # كتابة رقم الجواز
            field1 = self.driver.find_element(By.ID, "tbFirstValue")
            field1.clear()
            field1.send_keys(passport_number)
            
            # اختيار الاسم الاول
            second_select = Select(self.driver.find_element(By.ID, "ddlSecondValue"))
            second_select.select_by_value("fName")
            time.sleep(1)
            
            # كتابة الاسم
            field2 = self.driver.find_element(By.ID, "tbSecondValue")
            field2.clear()
            field2.send_keys(first_name)
            
            # اختيار الجنسية
            self._select_nationality()
            
            # حل الكابتشا
            print(f"\n{Colors.BOLD}🔐 جاري حل رمز التحقق...{Colors.ENDC}")
            max_attempts = 3
            
            for attempt in range(max_attempts):
                print(f"{Colors.WARNING}📝 محاولة {attempt + 1}/{max_attempts}{Colors.ENDC}")
                captcha_text = self._solve_captcha()
                
                if captcha_text and len(captcha_text) == 6:
                    captcha_field = self.driver.find_element(By.ID, "Captcha")
                    captcha_field.clear()
                    captcha_field.send_keys(captcha_text)
                    
                    print(f"{Colors.GREEN}📝 تم إدخال الرمز: {captcha_text}{Colors.ENDC}")
                    print(f"{Colors.CYAN}🔍 جاري البحث...{Colors.ENDC}")
                    search_btn = self.driver.find_element(By.ID, "btnSubmit")
                    search_btn.click()
                    time.sleep(5)
                    
                    error_msgs = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
                    if error_msgs:
                        error_text = error_msgs[0].text
                        if "رمز الصورة" in error_text or "captcha" in error_text.lower():
                            print(f"{Colors.WARNING}⚠️ رمز غير صحيح، إعادة المحاولة...{Colors.ENDC}")
                            self._refresh_captcha()
                            continue
                        else:
                            return {'success': False, 'message': error_text}
                    else:
                        print(f"{Colors.GREEN}✅ تم الاستعلام بنجاح!{Colors.ENDC}")
                        break
                else:
                    print(f"{Colors.WARNING}⚠️ فشل القراءة، تحديث...{Colors.ENDC}")
                    self._refresh_captcha()
            
            time.sleep(3)
            visa_info = self._extract_visa_info()
            pdf_path = self._print_to_pdf(passport_number, visa_info['full_name'])
            
            if pdf_path and os.path.exists(pdf_path):
                return {'success': True, 'pdf_path': pdf_path, 'visa_data': visa_info}
            else:
                return {'success': False, 'message': 'فشل إنشاء PDF'}
                
        except Exception as e:
            print(f"{Colors.FAIL}❌ خطأ: {e}{Colors.ENDC}")
            return {'success': False, 'message': str(e)}
    
    def close(self):
        """إغلاق المتصفح"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print(f"{Colors.CYAN}🔧 تم إغلاق المتصفح{Colors.ENDC}")
