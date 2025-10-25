# [file name]: ai.py
# -*- coding: utf-8 -*-
"""
بلجن الذكاء الاصطناعي Gemini API - مدمج مع النظام الجديد
"""

import requests
import json
import time

# 🔑 مفتاح Gemini API المجاني
GEMINI_API_KEY = "AIzaSyALer2PqEAdVCtI-sr9rfJckb8yhDNbQEA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

# تعريف المتغيرات العالمية التي سيتم تعيينها
send_msg = None
is_owner = None

def init_plugin(global_vars):
    """تهيئة البلجن بالمتغيرات العالمية"""
    global send_msg, is_owner
    
    # استيراد الدوال من النظام الرئيسي
    send_msg = global_vars.get('send_msg')
    is_owner = global_vars.get('is_owner')
    
    print("✅ تم تهيئة بلجن الذكاء الاصطناعي مع النظام")

def call_gemini(prompt):
    """
    استدعاء Gemini API المجاني بنص المستخدم
    """
    headers = {
        "Content-Type": "application/json",
    }
    
    # تحسين الpayload ليكون أكثر فعالية
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.8,  # زيادة قليلة للإبداع في إنشاء الأكواد
            "topK": 50,
            "topP": 0.9,
            "maxOutputTokens": 2048,  # زيادة للسماح بأكواد أطول
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH", 
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    }
    
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    answer = candidate["content"]["parts"][0].get("text", "")
                    return answer.strip()
                else:
                    return "❌ لم يتم العثور على محتوى في الرد."
            else:
                error_msg = "❌ لم يتم إرجاع رد من النموذج."
                if "promptFeedback" in data:
                    feedback = data["promptFeedback"]
                    if "blockReason" in feedback:
                        error_msg += f" السبب: {feedback['blockReason']}"
                return error_msg
                
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "طلب غير صحيح")
            return f"❌ خطأ في الطلب: {error_msg}"
            
        elif response.status_code == 403:
            return "❌ خطأ في المصادقة: مفتاح API غير صالح أو منتهي الصلاحية"
            
        elif response.status_code == 429:
            return "❌ تجاوز الحد المسموح: تم تجاوز عدد الطلبات المسموح بها"
            
        elif response.status_code == 500:
            return "❌ خطأ داخلي في الخادم: حاول مرة أخرى لاحقاً"
            
        else:
            return f"❌ خطأ غير متوقع: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "❌ انتهت مهلة الطلب: حاول مرة أخرى"
    except requests.exceptions.ConnectionError:
        return "❌ خطأ في الاتصال: تحقق من اتصال الإنترنت"
    except Exception as e:
        return f"❌ خطأ غير متوقع: {str(e)}"
        
def ذكاء(msg_type, jid, nick, text):
    """
    أمر: !ذكاء [سؤال أو نص عربي أو إنجليزي]
    """
    if not text.strip():
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال السؤال أو النص بعد الأمر !ذكاء")
        return
    
    send_msg(msg_type, jid, nick, "🤖 جاري معالجة الطلب بواسطة Gemini AI ...")
    
    # إضافة سياق عربي لتحسين الردود
    enhanced_prompt = f"""
    أنت مساعد ذكي يتحدث العربية بطلاقة. أجب على السؤال التالي بلغة المستخدم مع الحفاظ على الدقة والوضوح.
    
    السؤال: {text}
    
    الرجاء الإجابة بلغة واضحة ومفيدة ومناسبة للسياق.
    """
    
    answer = call_gemini(enhanced_prompt)
    
    if answer.startswith("❌"):
        send_msg(msg_type, jid, nick, answer)
    else:
        # تقسيم الإجابة إذا كانت طويلة
        if len(answer) > 1500:
            parts = [answer[i:i+1500] for i in range(0, len(answer), 1500)]
            for i, part in enumerate(parts):
                if i == 0:
                    send_msg(msg_type, jid, nick, f"🧠 إجابة Gemini (الجزء {i+1} من {len(parts)}):\n{part}")
                else:
                    send_msg(msg_type, jid, nick, f"🧠 (تابع {i+1}):\n{part}")
                time.sleep(0.5)  # تأخير بسيط بين الأجزاء
        else:
            send_msg(msg_type, jid, nick, f"🧠 إجابة Gemini:\n{answer}")

def معلومات_ذكاء(msg_type, jid, nick, text):
    """
    أمر: !معلومات_ذكاء
    """
    msg = (
        "🤖 نظام الذكاء الاصطناعي Gemini Pro\n"
        "المزود: Google AI\n"
        "النموذج: gemini-pro (مجاني)\n"
        "اللغة: يدعم العربية والإنجليزية\n"
        "الميزات: إجابة الأسئلة، التلخيص، الترجمة، إنشاء الأكواد\n\n"
        "📋 الأوامر المتاحة:\n"
        "• !ذكاء [سؤال] - سؤال مباشر للذكاء الاصطناعي\n" 
        "• !تلخيص [نص] - تلخيص النصوص الطويلة\n"
        "• !ترجمة [نص] إلى [لغة] - ترجمة بين اللغات\n"
        "• !كود [وصف الكود] - إنشاء كود برمجي\n"
        "• !معلومات_ذكاء - عرض هذه المعلومات"
    )
    send_msg(msg_type, jid, nick, msg)

def تلخيص(msg_type, jid, nick, text):
    """
    أمر: !تلخيص [نص طويل]
    """
    if not text.strip():
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال النص المراد تلخيصه بعد الأمر !تلخيص")
        return
        
    send_msg(msg_type, jid, nick, "📝 جار تلخيص النص باستخدام Gemini ...")
    
    prompt = f"""
    قم بتلخيص النص التالي باللغة العربية في نقاط واضحة ومختصرة مع الحفاظ على الأفكار الرئيسية:
    
    النص:
    {text}
    
    الرجاء تقديم ملخص واضح ومنظم.
    """
    
    answer = call_gemini(prompt)
    
    if answer.startswith("❌"):
        send_msg(msg_type, jid, nick, answer)
    else:
        send_msg(msg_type, jid, nick, f"📄 الملخص:\n{answer}")

def ترجمة(msg_type, jid, nick, text):
    """
    أمر: !ترجمة [النص] إلى [اللغة]
    مثال: !ترجمة هذا نص تجريبي إلى الإنجليزية
    """
    text = text.strip()
    if not text or "إلى" not in text:
        send_msg(msg_type, jid, nick, "❌ صيغة الأمر: !ترجمة [النص] إلى [اللغة]")
        send_msg(msg_type, jid, nick, "💡 أمثلة:\n!ترجمة مرحبا إلى الإنجليزية\n!ترجمة Hello إلى العربية")
        return
        
    try:
        src, lang = text.split("إلى", 1)
        src = src.strip()
        lang = lang.strip()
        
        if not src or not lang:
            raise Exception("نص أو لغة فارغة")
            
    except Exception:
        send_msg(msg_type, jid, nick, "❌ صيغة غير صحيحة. استخدم: !ترجمة [النص] إلى [اللغة]")
        return
        
    send_msg(msg_type, jid, nick, f"🔄 جار ترجمة النص إلى {lang} ...")
    
    prompt = f"""
    قم بترجمة النص التالي إلى اللغة {lang} بدقة مع الحفاظ على المعنى والسياق:
    
    النص: {src}
    
    الرجاء تقديم الترجمة فقط بدون أي إضافات.
    """
    
    answer = call_gemini(prompt)
    
    if answer.startswith("❌"):
        send_msg(msg_type, jid, nick, answer)
    else:
        send_msg(msg_type, jid, nick, f"🌐 الترجمة إلى {lang}:\n{answer}")

def كود(msg_type, jid, nick, text):
    """
    أمر: !كود [وصف الكود المطلوب]
    أمثلة: 
    !كود دالة بايثون لحساب العوامل
    !كود كائن جافا سكريبت لإدارة المستخدمين
    !كود صفحة HTML مع CSS لجعلها متجاوبة
    """
    if not text.strip():
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال وصف الكود المطلوب بعد الأمر !كود")
        send_msg(msg_type, jid, nick, "💡 أمثلة:\n!كود دالة بايثون لحساب مجموع الأعداد\n!كود صفحة HTML مع CSS")
        return
    
    send_msg(msg_type, jid, nick, "💻 جاري إنشاء الكود المطلوب ...")
    
    # تحسين الprompt ليكون أكثر تحديداً
    prompt = f"""
    أنت مساعد مبرمج خبير. قم بإنشاء الكود المطلوب بناء على الوصف التالي:
    
    "{text}"
    
    المتطلبات الأساسية:
    1. أنتج الكود العملي فقط بدون أي شرح خارجي
    2. استخدم التعليقات داخل الكود باللغة الإنجليزية لتوضيح الوظائف
    3. تأكد من أن الكود نظيف وسهل القراءة والتطبيق
    4. أضف تعليق في الأعلى يوضح وظيفة الكود
    5. استخدم أفضل الممارسات وأحدث المعايير في لغة البرمجة
    6. تأكد من أن الكود قابل للتشغيل والتنفيذ
    
    المطلوب: أنشئ الكود الكامل بناء على الطلب أعلاه.
    """
    
    answer = call_gemini(prompt)
    
    # معالجة الردود الفارغة أو غير الصحيحة
    if not answer or answer.startswith("❌") or "لم يتم العثور على محتوى" in answer:
        # محاولة ثانية مع prompt مختلف
        alternative_prompt = f"""
        قم بكتابة كود برمجي للطلب التالي:
        {text}
        
        المتطلبات:
        - اكتب الكود الكامل فقط
        - استخدم التعليقات داخل الكود
        - تأكد من أن الكود عملي وقابل للتشغيل
        - لا تضيف أي شرح خارج عن الكود
        
        اللغة: استخدم اللغة المناسبة للطلب أو Python كلغة افتراضية
        """
        
        answer = call_gemini(alternative_prompt)
        
        if not answer or answer.startswith("❌") or "لم يتم العثور على محتوى" in answer:
            send_msg(msg_type, jid, nick, "❌ تعذر إنشاء الكود حالياً. يرجى المحاولة مرة أخرى أو استخدام وصف أكثر تحديداً.")
            return
    
    # تنظيف الإجابة وإزالة أي تفسيرات غير مرغوبة
    lines = answer.split('\n')
    code_lines = []
    in_code = False
    
    for line in lines:
        # تخطي الأسطر التفسيرية في البداية
        if any(keyword in line.lower() for keyword in ['الكود', 'code', '```', 'هذا الكود', 'التالي']):
            in_code = True
            continue
        if line.strip() and (in_code or any(char in line for char in ['{', '}', 'def ', 'class ', 'import ', 'function ', '<!DOCTYPE'])):
            code_lines.append(line)
            in_code = True
    
    # إذا لم نتمكن من استخراج الكود، استخدم الإجابة الأصلية
    if not code_lines:
        code_lines = lines
    
    clean_code = '\n'.join(code_lines)
    
    # إزالة علامات الكود إذا كانت موجودة
    clean_code = clean_code.replace('```python', '').replace('```javascript', '').replace('```java', '').replace('```html', '').replace('```css', '').replace('```', '')
    
    if not clean_code.strip():
        send_msg(msg_type, jid, nick, "❌ لم يتم إنشاء كود صالح. يرجى المحاولة بوصف أكثر تحديداً.")
        return
    
    # إضافة تنسيق للكود
    formatted_answer = f"💻 الكود المطلوب:\n```\n{clean_code.strip()}\n```"
    
    # تقسيم الإجابة إذا كانت طويلة
    if len(formatted_answer) > 1500:
        parts = [formatted_answer[i:i+1500] for i in range(0, len(formatted_answer), 1500)]
        for i, part in enumerate(parts):
            if i == 0:
                send_msg(msg_type, jid, nick, f"💻 الكود المطلوب (الجزء {i+1} من {len(parts)}):\n{part}")
            else:
                send_msg(msg_type, jid, nick, f"💻 (تابع {i+1}):\n{part}")
            time.sleep(0.5)
    else:
        send_msg(msg_type, jid, nick, formatted_answer)
def اختبار_المفتاح(msg_type, jid, nick, text):
    """
    أمر: !اختبار_المفتاح - اختبار صلاحية مفتاح API
    """
    if not is_owner(jid):
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
        
    send_msg(msg_type, jid, nick, "🔐 جاري اختبار مفتاح Gemini API ...")
    
    test_prompt = "أجب بكلمة 'نجاح' فقط."
    result = call_gemini(test_prompt)
    
    if "نجاح" in result:
        send_msg(msg_type, jid, nick, "✅ المفتاح يعمل بشكل صحيح!")
    else:
        send_msg(msg_type, jid, nick, f"❌ مشكلة في المفتاح: {result}")

def execute():
    """الدالة الرئيسية التي تستدعيها system.py لتحميل الأوامر"""
    
    # قائمة الأوامر التي سيتم تصديرها
    commands = [
        (1, 'ذكاء', ذكاء, 1, 'اسأل الذكاء الاصطناعي: !ذكاء [سؤال أو نص]'),
        (1, 'معلومات_ذكاء', معلومات_ذكاء, 1, 'معلومات عن نظام الذكاء الاصطناعي'),
        (1, 'تلخيص', تلخيص, 1, 'تلخيص نص: !تلخيص [النص]'),
        (1, 'ترجمة', ترجمة, 1, 'ترجمة نص: !ترجمة [النص] إلى [اللغة]'),
        (1, 'كود', كود, 1, 'إنشاء كود برمجي: !كود [وصف الكود]'),
        (10, 'اختبار_المفتاح', اختبار_المفتاح, 1, 'اختبار صلاحية مفتاح API (للمالكين)'),
    ]
    
    print("✅ تم تحميل بلجن الذكاء الاصطناعي Gemini Pro - الإصدار المجاني الكامل")
    return commands

# قوائم التحكم (يمكن أن تبقى فارغة)
presence_control = []
message_act_control = []
iq_control = []
timer_functions = []