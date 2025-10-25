# -*- coding: utf-8 -*-

import time
import xmpp

# تعريف المتغيرات العالمية
send_msg = None
get_user_permission_level = None
db_execute = None
db_fetchone = None
clean_jid = None
BOT_NICKNAME = "xbot"

def init_plugin(global_vars):
    """تهيئة البلجن بالمتغيرات العالمية"""
    global send_msg, get_user_permission_level, db_execute, db_fetchone, clean_jid, BOT_NICKNAME
    
    # استيراد الدوال من النظام الرئيسي
    send_msg = global_vars.get('send_msg')
    get_user_permission_level = global_vars.get('get_user_permission_level')
    db_execute = global_vars.get('db_execute')
    db_fetchone = global_vars.get('db_fetchone')
    clean_jid = global_vars.get('clean_jid')
    
    # إعدادات إضافية من النظام
    if 'BOT_NICKNAME' in global_vars:
        BOT_NICKNAME = global_vars['BOT_NICKNAME']
    
    print("✅ تم تهيئة بلجن تنظيف التاريخ")

def safe_send_msg(msg_type, jid, nick, text):
    """إرسال رسالة بشكل آمن"""
    global send_msg
    if send_msg and callable(send_msg):
        send_msg(msg_type, jid, nick, text)
    else:
        print(f"⚠️ send_msg غير متاح: {text}")

def safe_client_send(obj):
    """إرسال كائن XMPP بشكل آمن"""
    from run import client
    if client and hasattr(client, 'send'):
        client.send(obj)
    else:
        print(f"⚠️ client غير متاح للإرسال: {obj}")

def get_room(jid):
    """استخراج اسم الغرفة من JID"""
    return jid.split('/')[0] if '/' in jid else jid

def get_config(room, config_name, default=None):
    """الحصول على إعدادات البلجن"""
    try:
        row = db_fetchone(
            "SELECT value FROM plugin_data WHERE plugin=? AND key=?",
            ('clear', f"{room}:{config_name}")
        )
        return row["value"] if row else default
    except:
        return default

def clear_history(msg_type, jid, nick, text):
    """تنظيف تاريخ الغرفة بإرسال رسائل فارغة"""
    room = get_room(jid)
    user_level = get_user_permission_level(jid, nick, room)
    
    # التحقق من الصلاحية (مشرف أو أعلى)
    if user_level < 7:
        safe_send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مشرف أو أعلى لتنظيف التاريخ")
        return
    
    try:
        # محاولة تحويل العدد من النص
        if text.strip():
            try:
                count = int(text.strip())
            except ValueError:
                safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال عدد صحيح للرسائل المراد تنظيفها")
                return
        else:
            count = 10  # القيمة الافتراضية
        
        # تحديد الحد الأقصى والحد الأدنى
        if count > 50:  # الحد الأقصى
            count = 50
            safe_send_msg(msg_type, jid, nick, f"⚠️ تم تحديد الحد الأقصى (50 رسالة)")
        elif count < 2:  # الحد الأدنى
            count = 2
            safe_send_msg(msg_type, jid, nick, f"⚠️ تم تحديد الحد الأدنى (2 رسالة)")
        
        # الحصول على إعدادات التأخير
        delay = float(get_config(room, 'delay', '0.5'))
        answer_mode = get_config(room, 'answer_mode', 'message')
        
        # إرسال رسالة البداية
        start_msg = f"🧹 جاري تنظيف {count} رسالة في حوالي {int(count * delay)} ثانية..."
        
        if answer_mode == 'presence':
            # استخدام الحالة كإجابة
            presence = xmpp.Presence(to=room, show='chat', status=start_msg)
            safe_client_send(presence)
        else:
            # استخدام رسالة عادية
            safe_send_msg(msg_type, jid, nick, start_msg)
        
        # الانتظار قليلاً قبل البدء
        time.sleep(1)
        
        # إرسال رسائل فارغة لتنظيف التاريخ
        cleaned_count = 0
        for i in range(count):
            try:
                msg = xmpp.Message(to=room, body="", typ="groupchat")
                msg.setTag('body')  # إضافة جسم فارغ
                safe_client_send(msg)
                cleaned_count += 1
                time.sleep(delay)  # تأخير بين الرسائل
            except Exception as e:
                print(f"⚠️ خطأ في إرسال رسالة التنظيف: {e}")
                continue
        
        # إرسال رسالة النهاية
        end_msg = f"✅ تم تنظيف {cleaned_count} رسالة بنجاح!"
        
        if answer_mode == 'presence':
            # إعادة الحالة إلى الوضع الطبيعي
            presence = xmpp.Presence(to=room, show='chat', status="البوت يعمل بشكل طبيعي")
            safe_client_send(presence)
            safe_send_msg(msg_type, jid, nick, end_msg)
        else:
            safe_send_msg(msg_type, jid, nick, end_msg)
        
        # تسجيل العملية
        print(f"🧹 تم تنظيف {cleaned_count} رسالة في الغرفة {room} بواسطة {nick}")
            
    except Exception as e:
        error_msg = f"❌ خطأ في تنظيف التاريخ: {str(e)}"
        safe_send_msg(msg_type, jid, nick, error_msg)
        print(f"❌ خطأ في clear_history: {e}")

def clear_settings(msg_type, jid, nick, text):
    """إعدادات بلجن التنظيف"""
    room = get_room(jid)
    user_level = get_user_permission_level(jid, nick, room)
    
    if user_level < 8:  # مالك الغرفة فقط
        safe_send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مالك الغرفة لتعديل الإعدادات")
        return
    
    if not text:
        # عرض الإعدادات الحالية
        delay = get_config(room, 'delay', '0.5')
        answer_mode = get_config(room, 'answer_mode', 'message')
        max_count = get_config(room, 'max_count', '50')
        
        mode_display = "رسالة" if answer_mode == 'message' else "حالة"
        
        settings_msg = f"""
⚙️ **إعدادات تنظيف التاريخ:**

• التأخير بين الرسائل: {delay} ثانية
• نمط الإجابة: {mode_display}
• الحد الأقصى للرسائل: {max_count}

📝 **الأوامر المتاحة:**
`!اعدادات_تنظيف تأخير [قيمة]` - ضبط التأخير
`!اعدادات_تنظيف نمط [رسالة/حالة]` - نمط الإجابة
`!اعدادات_تنظيف حد [عدد]` - الحد الأقصى
"""
        safe_send_msg(msg_type, jid, nick, settings_msg.strip())
        return
    
    parts = text.split()
    if len(parts) < 2:
        safe_send_msg(msg_type, jid, nick, "❌ صيغة الأمر: !اعدادات_تنظيف [خيار] [قيمة]")
        return
    
    option = parts[0].lower()
    value = ' '.join(parts[1:])
    
    if option == 'تأخير':
        try:
            delay_val = float(value)
            if delay_val < 0.1 or delay_val > 2:
                safe_send_msg(msg_type, jid, nick, "❌ القيمة يجب أن تكون بين 0.1 و 2 ثانية")
                return
            
            db_execute(
                "INSERT OR REPLACE INTO plugin_data (plugin, key, value) VALUES (?, ?, ?)",
                ('clear', f'{room}:delay', str(delay_val))
            )
            safe_send_msg(msg_type, jid, nick, f"✅ تم ضبط التأخير إلى {delay_val} ثانية")
        except ValueError:
            safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال قيمة رقمية صحيحة")
    
    elif option == 'نمط':
        if value in ['رسالة', 'حالة']:
            mode_value = 'message' if value == 'رسالة' else 'presence'
            db_execute(
                "INSERT OR REPLACE INTO plugin_data (plugin, key, value) VALUES (?, ?, ?)",
                ('clear', f'{room}:answer_mode', mode_value)
            )
            safe_send_msg(msg_type, jid, nick, f"✅ تم ضبط نمط الإجابة إلى {value}")
        else:
            safe_send_msg(msg_type, jid, nick, "❌ القيم المسموحة: رسالة أو حالة")
    
    elif option == 'حد':
        try:
            max_val = int(value)
            if max_val < 10 or max_val > 100:
                safe_send_msg(msg_type, jid, nick, "❌ القيمة يجب أن تكون بين 10 و 100")
                return
            
            db_execute(
                "INSERT OR REPLACE INTO plugin_data (plugin, key, value) VALUES (?, ?, ?)",
                ('clear', f'{room}:max_count', str(max_val))
            )
            safe_send_msg(msg_type, jid, nick, f"✅ تم ضبط الحد الأقصى إلى {max_val} رسالة")
        except ValueError:
            safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال عدد صحيح")
    
    else:
        safe_send_msg(msg_type, jid, nick, "❌ الخيار غير معروف. الخيارات: تأخير، نمط، حد")

def quick_clear(msg_type, jid, nick, text):
    """تنظيف سريع لـ 10 رسائل"""
    room = get_room(jid)
    user_level = get_user_permission_level(jid, nick, room)
    
    if user_level < 7:
        safe_send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مشرف أو أعلى لتنظيف التاريخ")
        return
    
    # استخدام القيمة الافتراضية 10
    try:
        count = 10
        delay = 0.3  # تأخير أقل للتنظيف السريع
        
        safe_send_msg(msg_type, jid, nick, f"⚡ جاري التنظيف السريع لـ {count} رسالة...")
        
        cleaned_count = 0
        for i in range(count):
            try:
                msg = xmpp.Message(to=room, body="", typ="groupchat")
                msg.setTag('body')
                safe_client_send(msg)
                cleaned_count += 1
                time.sleep(delay)
            except Exception:
                continue
        
        safe_send_msg(msg_type, jid, nick, f"✅ تم التنظيف السريع لـ {cleaned_count} رسالة!")
        
    except Exception as e:
        safe_send_msg(msg_type, jid, nick, f"❌ خطأ في التنظيف السريع: {str(e)}")

def setup_clear_plugin():
    """تهيئة إعدادات البلجن"""
    print("🔧 جاري تهيئة إعدادات تنظيف التاريخ...")
    
    # انتظار حتى تصبح دوال قاعدة البيانات جاهزة
    max_retries = 3
    for i in range(max_retries):
        try:
            if db_execute and callable(db_execute):
                # يمكن إضافة جداول خاصة بالبلجن هنا إذا لزم الأمر
                print("✅ تم تهيئة بلجن التنظيف")
                return
            else:
                print(f"⏳ انتظار تهيئة قاعدة البيانات... ({i+1}/{max_retries})")
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ محاولة {i+1} فشلت: {e}")
            time.sleep(1)

def execute():
    """الدالة الرئيسية لتحميل الأوامر"""
    
    # تهيئة الإعدادات
    setup_clear_plugin()
    
    commands = [
        (7, 'تنظيف_التاريخ', clear_history, 0, 'تنظيف تاريخ الغرفة - !تنظيف_التاريخ [عدد الرسائل]'),
        (7, 'ن', clear_history, 0, 'اختصار لـ !تنظيف_التاريخ - !تنظيف [عدد]'),
        (7, 'ت', quick_clear, 0, 'تنظيف سريع لـ 10 رسائل - !تنظيف_سريع'),
        (8, 'اعدادات_تنظيف', clear_settings, 1, 'إعدادات بلجن التنظيف - !اعدادات_تنظيف [خيار] [قيمة]'),
    ]
    
    print("✅ تم تحميل بلجن تنظيف التاريخ مع دعم العربية الكامل")
    return commands

# معالجات الأحداث
presence_control = []
message_act_control = []
iq_control = []
timer_functions = []