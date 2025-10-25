# -*- coding: utf-8 -*-
"""
بلجن فلترة الغرف - متكامل مع النظام الجديد
فلترة ذكية للرسائل والحضور مع دعم إعدادات ejabberd
"""
# استيراد دوال قاعدة البيانات مباشرة
import time
import re
import xmpp
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_execute, db_fetchone, db_fetchall, clean_jid

# إنشاء ملفات الفلترة تلقائياً
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CENSORED_FILE = os.path.join(PLUGIN_DIR, "censored.txt")
MUCFILTER_FILE = os.path.join(PLUGIN_DIR, "mucfilter.txt")

for fname in [CENSORED_FILE, MUCFILTER_FILE]:
    if not os.path.isfile(fname):
        with open(fname, "w", encoding="utf-8") as f:
            f.write("# قائمة الكلمات والعبارات الممنوعة\n")

# متغيرات الفلترة
muc_filter_fast_join = {}
muc_filter_events = []
last_msg_base = {}
last_msg_time_base = {}
adblock_regexp = [
    r"(https?://[^\s]+)",
    r"(@[a-zA-Z0-9\-_\.]+)",
    r"(www\.[^\s]+)",
    r"([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
]

# سيتم تعيين هذه المتغيرات من النظام الرئيسي
db_execute = None
db_fetchone = None
send_msg = None
get_level = None
clean_jid = None
BOT_NICKNAME = "xbot"
is_owner = None

def init_plugin(global_vars):
    """تهيئة البلجن مع المتغيرات العالمية"""
    global db_execute, db_fetchone, send_msg, get_level, clean_jid, BOT_NICKNAME
    
    # استيراد الدوال من النظام الرئيسي
    db_execute = global_vars.get('db_execute')
    db_fetchone = global_vars.get('db_fetchone') 
    send_msg = global_vars.get('send_msg')
    get_level = global_vars.get('get_level')
    clean_jid = global_vars.get('clean_jid')
    
    # إعدادات إضافية من النظام
    if 'BOT_NICKNAME' in global_vars:
        BOT_NICKNAME = global_vars['BOT_NICKNAME']
    
    print("✅ تم تهيئة بلجن فلترة الغرف مع النظام")
    
    # تهيئة الجداول بعد التأكد من توفر الدوال
    if db_execute:
        setup_muc_filter()
    else:
        print("⚠️ لم يتم تهيئة db_execute، سيتم تأجيل إنشاء الجداول")

def safe_db_execute(query, params=()):
    """تنفيذ استعلام قاعدة البيانات بشكل آمن"""
    global db_execute
    if db_execute and callable(db_execute):
        return db_execute(query, params)
    else:
        print(f"⚠️ db_execute غير متاح: {query}")
        return 0

def safe_db_fetchone(query, params=()):
    """استعلام قاعدة البيانات بشكل آمن"""
    global db_fetchone
    if db_fetchone and callable(db_fetchone):
        return db_fetchone(query, params)
    else:
        print(f"⚠️ db_fetchone غير متاح: {query}")
        return None

def safe_send_msg(msg_type, jid, nick, text):
    """إرسال رسالة بشكل آمن"""
    global send_msg
    if send_msg and callable(send_msg):
        send_msg(msg_type, jid, nick, text)
    else:
        print(f"⚠️ send_msg غير متاح: {text}")

def safe_get_level(jid, nick):
    """الحصول على مستوى المستخدم بشكل آمن"""
    global get_level
    if get_level and callable(get_level):
        return get_level(jid, nick)
    else:
        print(f"⚠️ get_level غير متاح، استخدام مستوى افتراضي: 1")
        return 1

def safe_clean_jid(jid):
    """تنظيف JID بشكل آمن"""
    global clean_jid
    if clean_jid and callable(clean_jid):
        return clean_jid(jid)
    else:
        # تنظيف أساسي إذا لم تكن الدالة متاحة
        if jid and '/' in jid:
            return jid.split('/')[0]
        return jid

def getRoom(jid):
    """استخراج اسم الغرفة من JID"""
    return jid.split('/')[0] if '/' in jid else jid

def get_nick_by_jid_res(room, jid):
    """استخراج النيك من JID"""
    return jid.split('/')[-1] if '/' in jid else ''

def load_regex_from_file(filename):
    """تحميل الأنماط من ملف نصي"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() if not line.startswith('#')]
    except Exception:
        return []

def muc_pprint(*param):
    """تسجيل أحداث الفلترة"""
    try:
        with open(MUCFILTER_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | " + " ".join([str(p) for p in param]) + "\n")
    except Exception:
        pass

def فلترة_الرسائل(msg_type, jid, nick, text):
    """إعدادات فلترة الرسائل"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال الأمر بشكل صحيح")
        return
    
    room = getRoom(jid)
    user_level = safe_get_level(jid, nick)
    
    if user_level < 7:  # مشرف أو أعلى
        safe_send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مشرف أو أعلى")
        return
    
    parts = text.split(' ', 1)
    command = parts[0].lower()
    value = parts[1] if len(parts) > 1 else ""
    
    if command == "حالة":
        # عرض الإعدادات الحالية
        settings = {
            'muc_filter_enabled': 'مفعلة',
            'muc_filter_links': 'مفعل',
            'muc_filter_ads': 'مفعل', 
            'muc_filter_repeat': 'مفعل',
            'muc_filter_flood': 'مفعل'
        }
        
        msg = "⚙️ إعدادات فلترة الرسائل:\n"
        for key, val in settings.items():
            msg += f"• {key}: {val}\n"
        
        safe_send_msg(msg_type, jid, nick, msg)
    
    elif command == "تفعيل":
        safe_db_execute(
            "INSERT OR REPLACE INTO plugin_data (plugin, key, value) VALUES (?, ?, ?)",
            ('muc_filter', f'{room}:enabled', '1')
        )
        safe_send_msg(msg_type, jid, nick, "✅ تم تفعيل فلترة الرسائل")
    
    elif command == "تعطيل":
        safe_db_execute(
            "INSERT OR REPLACE INTO plugin_data (plugin, key, value) VALUES (?, ?, ?)",
            ('muc_filter', f'{room}:enabled', '0')
        )
        safe_send_msg(msg_type, jid, nick, "✅ تم تعطيل فلترة الرسائل")
    
    elif command == "اضافة_كلمة":
        if value:
            try:
                with open(CENSORED_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{value}\n")
                safe_send_msg(msg_type, jid, nick, f"✅ تم إضافة الكلمة: {value}")
            except Exception as e:
                safe_send_msg(msg_type, jid, nick, f"❌ خطأ في إضافة الكلمة: {e}")
        else:
            safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال الكلمة الممنوعة")
    
    elif command == "حذف_كلمة":
        if value:
            try:
                with open(CENSORED_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                with open(CENSORED_FILE, "w", encoding="utf-8") as f:
                    for line in lines:
                        if line.strip() != value:
                            f.write(line)
                
                safe_send_msg(msg_type, jid, nick, f"✅ تم حذف الكلمة: {value}")
            except Exception as e:
                safe_send_msg(msg_type, jid, nick, f"❌ خطأ في حذف الكلمة: {e}")
        else:
            safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال الكلمة المراد حذفها")
    
    elif command == "قائمة_الكلمات":
        words = load_regex_from_file(CENSORED_FILE)
        if words:
            msg = "🚫 الكلمات الممنوعة:\n" + "\n".join([f"• {word}" for word in words[:20]])
            if len(words) > 20:
                msg += f"\n... و{len(words) - 20} كلمة أخرى"
        else:
            msg = "✅ لا توجد كلمات ممنوعة حالياً"
        safe_send_msg(msg_type, jid, nick, msg)
    
    else:
        safe_send_msg(msg_type, jid, nick, "❌ أمر غير معروف. استخدم:\n!فلترة حالة - لعرض الإعدادات\n!فلترة تفعيل/تعطيل - لتفعيل/تعطيل الفلترة\n!فلترة اضافة_كلمة [كلمة] - إضافة كلمة ممنوعة\n!فلترة حذف_كلمة [كلمة] - حذف كلمة ممنوعة\n!فلترة قائمة_الكلمات - عرض الكلمات الممنوعة")

def قفل_الخاص(msg_type, jid, nick, text):
    """قفل الرسائل الخاصة للمستخدم العادي"""
    room = getRoom(jid)
    user_jid = safe_clean_jid(f"{room}/{nick}")
    
    try:
        # التحقق إذا كان القفل مفعل بالفعل
        current_lock = safe_db_fetchone(
            "SELECT * FROM muc_lock WHERE room=? AND jid=?",
            (room, user_jid)
        )
        
        if current_lock:
            # إزالة القفل
            safe_db_execute(
                "DELETE FROM muc_lock WHERE room=? AND jid=?",
                (room, user_jid)
            )
            safe_send_msg(msg_type, jid, nick, "🔓 تم فتح الرسائل الخاصة - يمكن للآخرين مراسلتك")
        else:
            # تفعيل القفل
            safe_db_execute(
                "INSERT OR REPLACE INTO muc_lock (room, jid) VALUES (?, ?)",
                (room, user_jid)
            )
            safe_send_msg(msg_type, jid, nick, "🔒 تم قفل الرسائل الخاصة - لا يمكن للآخرين مراسلتك")
            
    except Exception as e:
        safe_send_msg(msg_type, jid, nick, f"❌ خطأ في تعديل إعدادات الخاص: {e}")

def حالة_قفل_الخاص(msg_type, jid, nick, text):
    """عرض حالة قفل الرسائل الخاصة"""
    room = getRoom(jid)
    user_jid = safe_clean_jid(f"{room}/{nick}")
    
    lock_status = safe_db_fetchone(
        "SELECT * FROM muc_lock WHERE room=? AND jid=?",
        (room, user_jid)
    )
    
    if lock_status:
        msg = "🔒 حالة الرسائل الخاصة: مقفولة\nلا يمكن للآخرين إرسال رسائل خاصة لك"
    else:
        msg = "🔓 حالة الرسائل الخاصة: مفتوحة\nيمكن للآخرين إرسال رسائل خاصة لك"
    
    safe_send_msg(msg_type, jid, nick, msg)

def get_config(room, config_name, default=None):
    """الحصول على إعدادات البلجن"""
    try:
        row = safe_db_fetchone(
            "SELECT value FROM plugin_data WHERE plugin=? AND key=?",
            ('muc_filter', f"{room}:{config_name}")
        )
        return row["value"] if row else default
    except:
        return default

def get_config_int(room, config_name, default=0):
    """الحصول على إعدادات رقمية"""
    try:
        value = get_config(room, config_name)
        return int(value) if value else default
    except:
        return default

def should_filter_message(room, jid, nick, body):
    """التحقق إذا كانت الرسالة تحتاج إلى فلترة"""
    # التحقق من تفعيل الفلترة
    if get_config_int(room, 'enabled', 1) == 0:
        return False, None
    
    # تجاهل المشرفين ومالكي الغرف
    user_level = safe_get_level(room, nick)
    if user_level >= 7:  # مشرف أو أعلى
        return False, None
    
    gr = getRoom(room)
    
    # فلتر الأسطر
    nline_count = get_config_int(gr, 'newline_msg_count', 5)
    if body.count('\n') >= nline_count:
        return True, f"❌ تم حظر الرسالة بسبب كثرة الأسطر ({nline_count} فأكثر)!"
    
    # فلتر الكلمات الممنوعة
    censored_words = load_regex_from_file(CENSORED_FILE)
    for word in censored_words:
        if word and re.search(rf"\b{re.escape(word)}\b", body, re.I | re.U):
            return True, f"❌ تم حظر الرسالة بسبب كلمة ممنوعة: {word}"
    
    # فلتر الروابط والإعلانات
    filter_patterns = adblock_regexp + load_regex_from_file(MUCFILTER_FILE)
    for pat in filter_patterns:
        if re.search(pat, body, re.I | re.U):
            return True, "❌ تم حظر الرسالة بسبب وجود إعلان أو رابط!"
    
    # فلتر التكرار
    grj = getRoom(jid)
    current_time = time.time()
    if last_msg_base.get(grj) == body and (current_time - last_msg_time_base.get(grj, 0)) < 30:
        return True, "❌ تم حظر الرسالة بسبب التكرار!"
    
    last_msg_base[grj] = body
    last_msg_time_base[grj] = current_time
    
    # فلتر الحجم الكبير
    if len(body) > 400:
        return True, f"❌ تم حظر الرسالة بسبب الحجم الكبير ({len(body)} حرف)!"
    
    return False, None

def handle_message_filter(conn, message):
    """معالجة فلترة الرسائل - يمكن استدعاؤها من run.py"""
    try:
        from_jid = str(message.getFrom())
        body = message.getBody()
        msg_type = message.getType()
        
        if msg_type != 'groupchat' or '/' not in from_jid:
            return
        
        room, nick = from_jid.split('/')
        
        # تجاهل رسائل البوت
        if nick == BOT_NICKNAME:
            return
        
        # التحقق من الفلترة
        should_filter, reason = should_filter_message(room, from_jid, nick, body)
        
        if should_filter:
            # إلغاء الرسالة
            message.setBody("")  # إفراغ محتوى الرسالة
            muc_pprint(f'رسالة محظورة: {nick} في {room} - السبب: {reason}')
            
            # إرسال تنبيه للمستخدم
            try:
                warn_msg = xmpp.Message(to=from_jid, body=reason, typ='chat')
                conn.send(warn_msg)
            except:
                pass
    
    except Exception as e:
        print(f"❌ خطأ في فلترة الرسائل: {e}")

def handle_presence_filter(conn, presence):
    """معالجة فلترة الحضور - يمكن استدعاؤها من run.py"""
    try:
        from_jid = str(presence.getFrom())
        presence_type = presence.getType()
        
        if '/' not in from_jid:
            return
        
        room, nick = from_jid.split('/')
        
        # تجاهل الحضور بدون نيك أو حضور البوت
        if not nick or nick == room or nick == BOT_NICKNAME:
            return
        
        # فلترة الانضمام السريع
        if presence_type != 'unavailable':
            current_time = int(time.time())
            muc_filter_fast_join.setdefault(room, [])
            muc_filter_fast_join[room] = [current_time] + muc_filter_fast_join[room][:2]
            
            # إذا انضم 3 مرات في أقل من 3 ثواني
            if (len(muc_filter_fast_join[room]) == 3 and 
                (muc_filter_fast_join[room][0] - muc_filter_fast_join[room][-1]) <= 3):
                
                # طرد المستخدم
                try:
                    iq = xmpp.Iq(typ='set', to=room)
                    query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
                    item = query.setTag('item', {'nick': nick, 'role': 'none'})
                    item.setTagData('reason', 'الانضمام السريع ممنوع')
                    conn.send(iq)
                    muc_pprint(f'طرد بسبب الانضمام السريع: {nick} في {room}')
                except:
                    pass
    
    except Exception as e:
        print(f"❌ خطأ في فلترة الحضور: {e}")

def handle_private_message_filter(conn, message):
    """معالجة فلترة الرسائل الخاصة - يمكن استدعاؤها من run.py"""
    try:
        from_jid = str(message.getFrom())
        to_jid = str(message.getTo())
        body = message.getBody()
        msg_type = message.getType()
        
        if msg_type != 'chat':
            return
        
        # إذا كانت الرسالة موجهة للبوت، تجاهل الفلترة
        if to_jid.endswith('/' + BOT_NICKNAME):
            return
        
        # استخراج معلومات الغرفة والمستخدم
        if '/' in to_jid:
            room, target_nick = to_jid.split('/')
            sender_room, sender_nick = from_jid.split('/') if '/' in from_jid else (from_jid, '')
            
            # التحقق من قفل الرسائل الخاصة
            lock_status = safe_db_fetchone(
                "SELECT * FROM muc_lock WHERE room=? AND jid=?",
                (room, safe_clean_jid(to_jid))
            )
            
            if lock_status:
                # إلغاء الرسالة وإرسال تنبيه
                message.setBody("")
                
                # إرسال رسالة للمرسل
                try:
                    warn_msg = xmpp.Message(
                        to=from_jid, 
                        body=f"❌ لا يمكن إرسال رسالة خاصة لـ {target_nick} - قام بقفل الرسائل الخاصة",
                        typ='chat'
                    )
                    conn.send(warn_msg)
                except:
                    pass
                
                muc_pprint(f'رسالة خاصة محظورة: {sender_nick} إلى {target_nick} في {room}')
    
    except Exception as e:
        print(f"❌ خطأ في فلترة الرسائل الخاصة: {e}")

def setup_muc_filter():
    """تهيئة إعدادات الفلترة مع معالجة الأخطاء"""
    print("🔧 جاري تهيئة إعدادات فلترة الغرف...")
    
    # انتظار حتى تصبح دوال قاعدة البيانات جاهزة
    max_retries = 5
    for i in range(max_retries):
        try:
            if db_execute and callable(db_execute):
                result = db_execute("""
                CREATE TABLE IF NOT EXISTS muc_lock (
                    room TEXT,
                    jid TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (room, jid)
                )
                """)
                print("✅ تم تهيئة جداول الفلترة")
                return
            else:
                print(f"⏳ انتظار تهيئة قاعدة البيانات... ({i+1}/{max_retries})")
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ محاولة {i+1} فشلت: {e}")
            time.sleep(1)
    
    print("❌ فشل في تهيئة جداول الفلترة بعد عدة محاولات")

def execute():
    """الدالة الرئيسية لتحميل الأوامر"""
    
    commands = [
        (7, 'فلترة', فلترة_الرسائل, 1, 'إدارة فلترة الرسائل: !فلترة [حالة/تفعيل/تعطيل/اضافة_كلمة/حذف_كلمة/قائمة_الكلمات]'),
        (1, 'قفل_الخاص', قفل_الخاص, 0, 'قفل/فتح الرسائل الخاصة: !قفل_الخاص'),
        (1, 'حالة_قفل_الخاص', حالة_قفل_الخاص, 0, 'عرض حالة قفل الرسائل الخاصة: !حالة_قفل_الخاص'),
        (1, 'خاص', قفل_الخاص, 0, 'قفل/فتح الرسائل الخاصة (اختصار): !خاص'),
    ]
    
    print("✅ تم تحميل بلجن فلترة الغرف (mucfilter.py)")
    return commands

# دوال يمكن استدعاؤها من run.py الرئيسي
def get_message_handlers():
    """إرجاع معالجات الرسائل"""
    return [handle_message_filter, handle_private_message_filter]

def get_presence_handlers():
    """إرجاع معالجات الحضور"""
    return [handle_presence_filter]

def get_iq_handlers():
    """إرجاع معالجات IQ"""
    return []

def get_timer_functions():
    """إرجاع دوال المؤقت"""
    return []

print("✅ تم تحميل بلجن فلترة الغرف مع دعم ejabberd/XMPP")