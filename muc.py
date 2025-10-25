# [file name]: muc.py
# -*- coding: utf-8 -*-
"""
بلجن إدارة الغرف والصلاحيات الجماعية - متكامل مع النظام الجديد
"""

import time
import random
import re
import xmpp

# متغيرات البلجن
visitors_list = {}
visitors_list_lock = False

# تعريف المتغيرات العالمية التي سيتم تعيينها لاحقاً
megabase = []
client = None
send_msg = None
get_level = None
get_affiliation = None
is_owner = None
db_execute = None
db_fetchone = None
db_fetchall = None
clean_jid = None

def init_plugin(global_vars):
    """تهيئة البلجن بالمتغيرات العالمية"""
    global megabase, client, send_msg, get_level, get_affiliation, is_owner
    global db_execute, db_fetchone, db_fetchall, clean_jid
    
    # استيراد المتغيرات من النظام الرئيسي
    megabase = global_vars.get('megabase', [])
    client = global_vars.get('client')
    send_msg = global_vars.get('send_msg')
    get_level = global_vars.get('get_level')
    get_affiliation = global_vars.get('get_affiliation')
    is_owner = global_vars.get('is_owner')
    db_execute = global_vars.get('db_execute')
    db_fetchone = global_vars.get('db_fetchone')
    db_fetchall = global_vars.get('db_fetchall')
    clean_jid = global_vars.get('clean_jid')
    
    print("✅ تم تهيئة بلجن إدارة الغرف مع النظام")

def safe_send_msg(msg_type, jid, nick, text):
    """إرسال رسالة بشكل آمن"""
    global send_msg
    if send_msg and callable(send_msg):
        send_msg(msg_type, jid, nick, text)
    else:
        print(f"⚠️ send_msg غير متاح: {text}")

def safe_client_send(obj):
    """إرسال كائن XMPP بشكل آمن"""
    global client
    if client and hasattr(client, 'send'):
        client.send(obj)
    else:
        print(f"⚠️ client غير متاح للإرسال: {obj}")

def getRoom(jid):
    """استخراج اسم الغرفة من JID"""
    return jid.split('/')[0] if '/' in jid else jid

def هنا(msg_type, jid, nick, text):
    """عرض المشاركين الحاليين في الغرفة"""
    users = sorted([t[1] for t in megabase if t[0]==jid])
    msg = f"👥 عدد المشاركين: {len(users)}\n" + "، ".join(users)
    safe_send_msg(msg_type, jid, nick, msg)

def قائمة_المستخدمين(msg_type, jid, nick, text):
    """عرض قائمة المشاركين في الغرفة الحالية"""
    users = sorted([t[1] for t in megabase if t[0]==jid])
    msg = f"📃 المشاركون ({len(users)}):\n" + "، ".join(users)
    safe_send_msg(msg_type, jid, nick, msg)

def معروف(msg_type, jid, nick, text):
    """عرض جميع الأسماء السابقة لهذا المستخدم"""
    count = 10
    if '\n' in text:
        try:
            t_count = text.split('\n')[1].strip().lower()
            if t_count == 'all': 
                count = 0
            else: 
                count = int(t_count)
        except: 
            pass
        text = text.split('\n',1)[0]
    
    if not text.strip(): 
        text = nick
    
    real_jid = db_fetchone(
        'SELECT jid FROM muc_users WHERE room=? AND (nick=? OR jid=?) ORDER BY joined_at DESC', 
        (jid, text, text.lower())
    )
    
    if real_jid:
        if count:
            lst = db_fetchall(
                'SELECT nick FROM muc_users WHERE room=? AND jid=? AND nick!=? ORDER BY joined_at DESC LIMIT ?', 
                (jid, real_jid['jid'], text, count)
            )
        else:
            lst = db_fetchall(
                'SELECT nick FROM muc_users WHERE room=? AND jid=? AND nick!=? ORDER BY joined_at DESC', 
                (jid, real_jid['jid'], text)
            )
        
        nicks = "، ".join([t['nick'] for t in lst]) if lst else text
        
        if text == nick:
            msg = f"🔎 أنا أعرفك باسم: {nicks}"
        else:
            msg = f"🔎 المستخدم {text} له الأسماء التالية: {nicks}"
    else:
        msg = "❌ المستخدم غير موجود!"
    
    safe_send_msg(msg_type, jid, nick, msg)

def دعوة(msg_type, jid, nick, text):
    """دعوة مستخدم للغرفة"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم المستخدم")
        return
    
    try:
        reason = text.split('\n')[1]
        text = text.split('\n')[0]
    except:
        reason = None
    
    fnd = db_fetchall(
        'SELECT jid FROM muc_users WHERE room=? AND (nick=? OR jid=?) GROUP BY jid', 
        (jid, text, text)
    )
    
    if len(fnd) == 1:
        whojid = getRoom(str(fnd[0]['jid']))
        is_found = False
        
        for tmp in megabase:
            if tmp[0] == jid and getRoom(tmp[4]) == whojid:
                is_found = True
                break
        
        if is_found:
            safe_send_msg(msg_type, jid, nick, f"{text} موجود بالفعل!")
            return
        else:
            # إرسال الدعوة
            inv_msg = f"📨 {nick} يدعوك للغرفة {jid}"
            if reason:
                inv_msg += f" بسبب: {reason}"
            
            safe_send_msg('chat', whojid, '', inv_msg)
            
            # إرسال دعوة MUC
            inv = xmpp.Message(jid)
            inv.setTag('x', namespace=xmpp.NS_MUC_USER).addChild('invite', {'to': whojid})
            safe_client_send(inv)
            
            safe_send_msg(msg_type, jid, nick, "✅ تم إرسال الدعوة.")
    
    elif len(fnd) > 1:
        safe_send_msg(msg_type, jid, nick, "⚠️ يوجد أكثر من مستخدم بهذا الاسم، تحقق!")
    else:
        safe_send_msg(msg_type, jid, nick, f"❌ لا أعرف المستخدم {text}")

def تغيير_اللقب(msg_type, jid, nick, text):
    """تغيير لقب البوت في الغرفة"""
    if get_affiliation(jid, nick) == 'owner' or get_level(jid, nick) == 10:
        from config import BOT_NICKNAME
        new_nick = text or BOT_NICKNAME
        try:
            pres = xmpp.Presence(to=f"{jid}/{new_nick}")
            safe_client_send(pres)
            safe_send_msg(msg_type, jid, nick, f"✅ تم تغيير اللقب إلى: {new_nick}")
        except Exception as e:
            safe_send_msg(msg_type, jid, nick, f"❌ خطأ في تغيير اللقب: {e}")
    else:
        safe_send_msg(msg_type, jid, nick, "❌ لا يمكنك تغيير لقب البوت!")

def قول(msg_type, jid, nick, text):
    """قول نص في الغرفة"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال النص")
        return
    
    msg = random.choice(re.split(r'(?<!\\)\|', text)).replace('\\|', '|')
    safe_send_msg('groupchat', jid, '', msg)

def قول_خاص(msg_type, jid, nick, text):
    """إرسال رسالة خاصة لمستخدم"""
    try:
        if '\n' in text: 
            target, msg_text = text.split('\n', 1)
        else: 
            target, msg_text = text.split(' ', 1)
        
        safe_send_msg('chat', jid, target, msg_text)
    except:
        safe_send_msg(msg_type, jid, nick, "❌ خطأ في بناء الرسالة الخاصة. استخدم: !قول_خاص [المستخدم] [النص]")

def قول_عام(msg_type, jid, nick, text):
    """إرسال رسالة لجميع الغرف"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال النص")
        return
    
    rooms = db_fetchall('SELECT room FROM rooms')
    for r in rooms:
        safe_send_msg('groupchat', r['room'], '', text)

def موضوع(msg_type, jid, nick, text):
    """تغيير موضوع الغرفة"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال الموضوع الجديد")
        return
    
    msg = xmpp.Message(jid, subject=text, typ='groupchat')
    safe_client_send(msg)
    safe_send_msg(msg_type, jid, nick, "✅ تم تغيير موضوع الغرفة")

def مذكرات(msg_type, jid, nick, text):
    """إرسال مذكرة إلى نفسك"""
    user_jid = clean_jid(f"{jid}/{nick}")
    
    if text.startswith('عرض'):
        notes = db_fetchall('SELECT message FROM sayto WHERE room=? AND jid=?', (jid, user_jid))
        if notes:
            msg = '\n' + '\n'.join([f'• {note["message"]}' for note in notes])
        else:
            msg = "لا توجد مذكرات لك!"
    elif text:
        db_execute(
            'INSERT INTO sayto (who, room, jid, message) VALUES (?, ?, ?, ?)', 
            (f'\n{int(time.time())}', jid, user_jid, text)
        )
        msg = "💌 تم حفظ المذكرة!"
    else:
        msg = "❌ ماذا تريد أن أذكر لك؟"
    
    safe_send_msg(msg_type, jid, nick, msg)

def رسالة_للمالك(msg_type, jid, nick, text):
    """إرسال رسالة للمالكين"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى كتابة رسالة!")
        return
    
    msg = f"مستخدم {nick} ({jid}) أرسل رسالة للمالك:\n{text}"
    owners = db_fetchall('SELECT jid FROM bot_owner')
    
    if owners:
        for owner in owners:
            safe_send_msg('chat', owner['jid'], '', msg)
        safe_send_msg(msg_type, jid, nick, "✅ تم إرسال الرسالة للمالكين")
    else:
        safe_send_msg(msg_type, jid, nick, "❌ قائمة المالكين فارغة!")

def بحث_مستخدم(msg_type, jid, nick, text):
    """بحث في المستخدمين حسب الاسم أو JID"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم أو JID للبحث.")
        return
    
    results = []
    for user in megabase:
        if text.lower() in user[1].lower() or text.lower() in user[4].lower():
            results.append(f"- {user[1]} / {user[4]}")
    
    if results:
        msg = "نتائج البحث:\n" + "\n".join(results[:10])  # عرض أول 10 نتائج فقط
        if len(results) > 10:
            msg += f"\n... و{len(results) - 10} نتيجة أخرى"
    else:
        msg = "❌ لم يتم العثور على نتائج."
    
    safe_send_msg(msg_type, jid, nick, msg)

def قائمة_الحظر(msg_type, jid, nick, text):
    """إظهار قائمة المحظورين في الغرفة"""
    banned = db_fetchall('SELECT jid FROM muc_users WHERE room=? AND affiliation="outcast"', (jid,))
    
    if banned:
        msg = "🚫 قائمة المحظورين:\n" + "\n".join([b['jid'] for b in banned])
    else:
        msg = "✅ لا يوجد محظورين حالياً."
    
    safe_send_msg(msg_type, jid, nick, msg)


def حظر_عام(msg_type, jid, nick, text):
    """حظر عام لكل الغرف"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال JID للحظر أو 'عرض' أو 'إضافة' أو 'حذف'")
        return
    
    text = text.lower()
    room = getRoom(jid)
    user_level = get_level(room, nick)
    
    if user_level < 10:  # مالك الغرفة فقط
        safe_send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح فقط لمالك الغرفة")
        return
    
    if text == "عرض":
        rooms = db_fetchall("SELECT room FROM ignore_ban")
        if rooms:
            msg = f"الغرف المستثناة من الحظر العام:\n" + "\n".join([r['room'] for r in rooms])
        else:
            msg = "لا توجد استثناءات، الحظر العام مفعل للجميع"
    
    elif text == "حذف":
        if db_fetchone("SELECT room FROM ignore_ban WHERE room=?", (room,)):
            db_execute("DELETE FROM ignore_ban WHERE room=?", (room,))
            msg = f"تم حذف الغرفة من قائمة استثناء الحظر العام: {room}"
        else:
            msg = "الغرفة ليست في قائمة الاستثناءات"
    
    elif text == "إضافة":
        if db_fetchone("SELECT room FROM ignore_ban WHERE room=?", (room,)):
            msg = "الغرفة موجودة بالفعل في قائمة الاستثناءات"
        else:
            db_execute("INSERT INTO ignore_ban (room) VALUES (?)", (room,))
            msg = "تمت إضافة الغرفة إلى قائمة الاستثناءات"
    
    else:
        if '@' not in text or '.' not in text:
            safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال JID صحيح للحساب المطلوب حظره")
            return
        
        # حظر الحساب في جميع الغرف
        reason = f"تم الحظر العام بواسطة {nick} من {jid}"
        rooms = db_fetchall("SELECT room FROM rooms WHERE room NOT IN (SELECT room FROM ignore_ban)")
        count = 0
        
        for r in rooms:
            room_jid = r['room']
            try:
                iq = xmpp.Iq(typ='set', to=room_jid)
                query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
                item = query.setTag('item', {'affiliation': 'outcast', 'jid': text})
                item.setTagData('reason', reason)
                safe_client_send(iq)
                count += 1
                time.sleep(0.1)
            except Exception:
                continue
        
        msg = f"تم حظر الحساب {text} في {count} غرفة"
    
    safe_send_msg(msg_type, jid, nick, msg)

def حظر_مؤقت(msg_type, jid, nick, text):
    """حظر مؤقت للمستخدم"""
    if not text:
        safe_send_msg(msg_type, jid, nick, "❌ يرجى إدخال البيانات. استخدم: !حظر_مؤقت [اسم]\\n[مدة]\\n[سبب]")
        return
    
    lines = text.strip().split('\n')
    
    if lines[0].lower() == "عرض":
        # عرض المحظورين مؤقتاً
        pattern = lines[1] if len(lines) > 1 else '%'
        banned = db_fetchall("SELECT jid, time FROM tmp_ban WHERE room=? AND jid LIKE ?", (jid, pattern))
        
        if banned:
            now = int(time.time())
            msg_lines = []
            for ban in banned:
                left = ban['time'] - now
                status = "منتهي" if left < 0 else f"{left//60} دقيقة"
                msg_lines.append(f"{ban['jid']}\t{status}")
            msg = "المحظورين مؤقتاً:\n" + '\n'.join(msg_lines)
        else:
            msg = "لا يوجد محظورين مؤقتاً"
    
    elif lines[0].lower() == "حذف":
        # حذف حظر مؤقت
        if len(lines) > 1:
            pattern = lines[1]
            banned = db_fetchall("SELECT jid, time FROM tmp_ban WHERE room=? AND jid LIKE ?", (jid, pattern))
            
            if banned:
                for ban in banned:
                    try:
                        iq = xmpp.Iq(typ='set', to=jid)
                        query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
                        item = query.setTag('item', {'affiliation': 'none', 'jid': ban['jid']})
                        safe_client_send(iq)
                    except Exception:
                        continue
                
                db_execute("DELETE FROM tmp_ban WHERE room=? AND jid LIKE ?", (jid, pattern))
                msg = "تم حذف الحظر المؤقت"
            else:
                msg = "لا يوجد محظور بهذا الحساب"
        else:
            msg = "❌ يرجى تحديد الحساب"
    
    else:
        # حظر مؤقت جديد
        if len(lines) >= 2:
            who = lines[0].strip()
            time_str = lines[1].strip()
            
            # تحويل المدة إلى ثواني
            try:
                unit = time_str[-1].lower()
                val = int(time_str[:-1])
                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                ban_time = val * multipliers.get(unit, 60)
            except:
                ban_time = None
            
            if ban_time:
                reason = lines[2].strip() if len(lines) > 2 else "بدون سبب"
                full_reason = f"حظر مؤقت لمدة {time_str} بسبب: {reason}"
                
                db_execute(
                    "INSERT OR REPLACE INTO tmp_ban (room, jid, time) VALUES (?, ?, ?)", 
                    (jid, who, int(time.time()) + ban_time)
                )
                
                try:
                    iq = xmpp.Iq(typ='set', to=jid)
                    query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
                    item = query.setTag('item', {'affiliation': 'outcast', 'jid': who})
                    item.setTagData('reason', full_reason)
                    safe_client_send(iq)
                    msg = "✅ تم الحظر المؤقت"
                except Exception as e:
                    msg = f"❌ خطأ في تنفيذ الحظر: {e}"
            else:
                msg = "❌ صيغة الوقت غير صحيحة. استخدم: 10s, 5m, 1h, 2d"
        else:
            msg = "❌ يرجى إدخال اسم ومدة الحظر"
    
    safe_send_msg(msg_type, jid, nick, msg)

def visitors_list_lock_wait():
    """انتظار تحرير قفل قائمة الزوار"""
    global visitors_list_lock
    while visitors_list_lock:
        time.sleep(0.05)
    return True

def check_visitor():
    """فحص الزوار المنتهية فترة زيارتهم"""
    global visitors_list, visitors_list_lock
    
    if visitors_list_lock_wait():
        visitors_list_lock = True
        try:
            now = int(time.time())
            for key in list(visitors_list.keys()):
                room, user = key.split('/', 1)
                timeout = visitors_list[key]
                if now > timeout:
                    # إزالة الزائر المنتهي
                    visitors_list.pop(key)
        finally:
            visitors_list_lock = False

def handle_visitor_presence(conn, presence):
    """تتبع الزوار في الغرف - يمكن استدعاؤها من run.py"""
    try:
        from_jid = str(presence.getFrom())
        presence_type = presence.getType()
        
        if '/' not in from_jid:
            return
            
        room, nick = from_jid.split('/')
        
        # تجاهل الحضور بدون نيك
        if not nick or nick == room:
            return
        
        # استخراج role من بيانات الحضور
        role = 'none'
        x_tag = presence.getTag('x', namespace='http://jabber.org/protocol/muc#user')
        if x_tag:
            item_tag = x_tag.getTag('item')
            if item_tag:
                role = item_tag.getAttr('role') or 'none'
        
        # إذا كان المستخدم زائراً
        if role == 'visitor':
            if visitors_list_lock_wait():
                visitors_list_lock = True
                try:
                    visitors_list[f"{room}/{nick}"] = int(time.time()) + 300  # 5 دقائق
                finally:
                    visitors_list_lock = False
                    
    except Exception as e:
        print(f"❌ خطأ في تتبع الزوار: {e}")

def check_unban():
    """فحص المحظورين المؤقتين المنتهية فترة حظرهم"""
    now = int(time.time())
    bans = db_fetchall("SELECT room, jid FROM tmp_ban WHERE time < ?", (now,))
    
    for ban in bans:
        # رفع الحظر
        try:
            iq = xmpp.Iq(typ='set', to=ban['room'])
            query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
            item = query.setTag('item', {'affiliation': 'none', 'jid': ban['jid']})
            safe_client_send(iq)
        except Exception:
            pass
        
        db_execute("DELETE FROM tmp_ban WHERE room=? AND jid=?", (ban['room'], ban['jid']))

# قائمة الأوامر
def execute():
    """إرجاع قائمة الأوامر"""
    return [
        # أوامر عرض المعلومات
        (1, 'هنا', هنا, 0, 'عرض المشاركين الحاليين في الغرفة'),
        (1, 'معروف', معروف, 1, 'عرض الأسماء السابقة لهذا المستخدم'),
        (1, 'قائمة_المستخدمين', قائمة_المستخدمين, 0, 'عرض قائمة المستخدمين في الغرفة'),
        (7, 'قائمة_الحظر', قائمة_الحظر, 0, 'إظهار قائمة المحظورين في الغرفة'),
        (1, 'بحث_مستخدم', بحث_مستخدم, 1, 'بحث في المستخدمين حسب الاسم أو JID'),
        
        # أوامر الدعوة والحظر
        (1, 'دعوة', دعوة, 1, 'دعوة مستخدم للغرفة (دعوة اسم\\nسبب)'),
        (10, 'حظر_عام', حظر_عام, 1, 'حظر عام لكل الغرف: !حظر_عام [jid] أو !حظر_عام عرض/حذف/إضافة'),
        (8, 'حظر_مؤقت', حظر_مؤقت, 1, 'حظر مؤقت: !حظر_مؤقت [اسم]\\n[مدة مثل 10m]\\n[سبب] أو !حظر_مؤقت عرض/حذف [jid]'),
        
        # أوامر الرسائل والمذكرات
        (1, 'قول', قول, 1, 'قول نص في الغرفة (يدعم | للفصل بين رسائل متعددة)'),
        (1, 'قول_خاص', قول_خاص, 1, 'قول نص في خاص مستخدم'),
        (7, 'قول_عام', قول_عام, 1, 'قول نص في جميع الغرف'),
        (7, 'موضوع', موضوع, 1, 'تغيير موضوع الغرفة'),
        (1, 'مذكرات', مذكرات, 1, 'إرسال مذكرة إلى نفسك'),
        (1, 'رسالة_للمالك', رسالة_للمالك, 1, 'إرسال رسالة إلى مالك البوت'),
        (8, 'لقب', تغيير_اللقب, 1, 'تغيير لقب البوت في الغرفة (متاح للمالك فقط)'),
    ]

# دوال يمكن استدعاؤها من run.py الرئيسي
def get_message_handlers():
    """إرجاع معالجات الرسائل"""
    return []  # لا توجد معالجات رسائل في هذا البلجن

def get_presence_handlers():
    """إرجاع معالجات الحضور"""
    return [handle_visitor_presence]

def get_iq_handlers():
    """إرجاع معالجات IQ"""
    return []

def get_timer_functions():
    """إرجاع دوال المؤقت"""
    return [check_unban, check_visitor]

print("✅ تم تحميل بلجن إدارة الغرف المدمج (muc.py) مع دعم العربية الكامل")